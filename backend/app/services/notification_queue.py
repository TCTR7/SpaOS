"""Transactional events and per-subscription retries; all operations remain tenant scoped."""
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, select, text
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.models import (Booking, Notification, NotificationDispatch, NotificationEvent, PushSubscription, Tenant, User, UserRole)

logger = logging.getLogger("spaos.notification_queue")

def enqueue_event(db, tenant_id, booking_id, actor, event):
    db.add(NotificationEvent(tenant_id=tenant_id, booking_id=booking_id, actor_id=actor.id,
        event=event, to_staff=actor.role == UserRole.CUSTOMER))


async def drain_push(tenant_id, limit=30):
    from app.services.notification_service import _send_one, webpush_enabled
    if not webpush_enabled(): return
    # Each job is persisted before any network operation. Concurrent workers use SKIP LOCKED.
    for _ in range(limit):
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tenant_id)
            row = (await db.execute(select(NotificationDispatch).where(NotificationDispatch.tenant_id == tenant_id,
                NotificationDispatch.delivered_at.is_(None), NotificationDispatch.next_attempt_at <= datetime.now(timezone.utc))
                .order_by(NotificationDispatch.created_at).limit(1).with_for_update(skip_locked=True))).scalar_one_or_none()
            if row is None: break
            notification = (await db.execute(select(Notification).where(Notification.tenant_id == tenant_id, Notification.id == row.notification_id))).scalar_one_or_none()
            sub = (await db.execute(select(PushSubscription).where(PushSubscription.tenant_id == tenant_id, PushSubscription.id == row.subscription_id))).scalar_one_or_none()
            eligible = False
            if notification and sub and notification.user_id == sub.user_id:
                booking = (await db.execute(select(Booking).where(Booking.tenant_id == tenant_id, Booking.id == notification.booking_id))).scalar_one_or_none()
                if booking:
                    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                        {"key": f"customer:{tenant_id}:{booking.customer_id}"})
                    booking = (await db.execute(select(Booking).where(Booking.tenant_id == tenant_id, Booking.id == notification.booking_id)
                        .execution_options(populate_existing=True))).scalar_one_or_none()
                user = (await db.execute(select(User).where(User.tenant_id == tenant_id, User.id == sub.user_id, User.is_active.is_(True)))).scalar_one_or_none()
                if booking and user:
                    customer = (await db.execute(select(User).where(User.tenant_id == tenant_id, User.id == booking.customer_id))).scalar_one_or_none()
                    eligible = user.role == UserRole.ADMIN or user.id == booking.customer_id or (user.role == UserRole.STAFF and
                        user.id in {booking.staff_id, customer.assigned_staff_id if customer else None})
            if not eligible:
                row.delivered_at = datetime.now(timezone.utc)
            else:
                payload = json.dumps({"title": notification.title, "body": notification.body, "type": notification.type,
                    "booking_id": str(notification.booking_id), "notification_id": str(notification.id), "url": row.url}, ensure_ascii=False)
                try:
                    outcome = await _send_one({"endpoint": sub.endpoint, "p256dh": sub.p256dh, "auth": sub.auth}, payload)
                except Exception:
                    outcome = 0
                row.attempts += 1
                if outcome is None:
                    row.delivered_at = datetime.now(timezone.utc)
                elif outcome in (404, 410):
                    await db.delete(sub)  # cascades only jobs for this expired subscription
                else:
                    row.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=min(3600, 5 * 2 ** min(row.attempts, 10)))
            await db.commit()


async def drain_events(tenant_id, limit=30):
    from app.services.notification_service import notify_booking_event
    for _ in range(limit):
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tenant_id)
            event = (await db.execute(select(NotificationEvent).where(NotificationEvent.tenant_id == tenant_id,
                NotificationEvent.processed_at.is_(None), NotificationEvent.next_attempt_at <= datetime.now(timezone.utc))
                .order_by(NotificationEvent.created_at, NotificationEvent.id).limit(1)
                .with_for_update(skip_locked=True, key_share=True))).scalar_one_or_none()
            if event is None: break
            try:
                await notify_booking_event(tenant_id, event.booking_id, event.event, event.actor_id, event.to_staff,
                    event_id=event.id, strict=True)
                event.processed_at = datetime.now(timezone.utc)
            except Exception:
                logger.warning("Notification event will be retried")
                event.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=min(3600, 5 * 2 ** min(event.attempts, 10)))
            event.attempts += 1
            await db.commit()
    await drain_push(tenant_id)


async def worker():
    while True:
        try:
            async with AsyncSessionLocal() as db:
                tenants = list((await db.execute(select(Tenant.id).where(Tenant.status == "ACTIVE"))).scalars().all())
            for tenant_id in tenants:
                await drain_events(tenant_id)
        except asyncio.CancelledError: raise
        except Exception: logger.warning("Notification worker will retry")
        await asyncio.sleep(5)
