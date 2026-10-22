import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from contextvars import ContextVar
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, or_, text

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.models import Booking, Notification, NotificationDispatch, PushSubscription, Tenant, User, UserRole
from app.services.booking_service import TZ

logger = logging.getLogger("spaos.notifications")
_current_event = ContextVar("notification_event", default=None)

_STATUS_TITLES = {
    "CREATED": "Bạn có lịch hẹn mới",
    "RESCHEDULED": "Lịch hẹn đã được thay đổi",
    "CONFIRMED": "Lịch hẹn đã được xác nhận",
    "IN_PROGRESS": "Buổi chăm sóc đã bắt đầu",
    "COMPLETED": "Buổi chăm sóc đã hoàn thành",
    "CANCELLED": "Lịch hẹn đã bị hủy",
    "NO_SHOW": "Bạn đã vắng mặt tại lịch hẹn",
}


@dataclass
class Draft:
    user_id: uuid.UUID
    title: str
    body: str
    url: str = "/admin/bookings"


def webpush_enabled() -> bool:
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)


def _send_one_sync(sub: Dict[str, str], payload: str) -> Optional[int]:
    """Gửi 1 Web Push (blocking). Trả về None nếu OK, ngược lại trả HTTP status lỗi (0 = lỗi mạng/khác)."""
    from pywebpush import WebPushException, webpush

    try:
        webpush(
            subscription_info={"endpoint": sub["endpoint"], "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]}},
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.VAPID_SUBJECT},
            ttl=3600,
            timeout=10,
        )
        return None
    except WebPushException as exc:
        return exc.response.status_code if exc.response is not None else 0


async def _send_one(sub: Dict[str, str], payload: str) -> Optional[int]:
    return await asyncio.to_thread(_send_one_sync, sub, payload)


async def _deliver(tenant_id: uuid.UUID, drafts: List[Draft], ntype: str, booking_id: uuid.UUID) -> None:
    """Lưu thông báo in-app (1 transaction riêng) rồi bắn Web Push tới các thiết bị đã đăng ký."""
    if not drafts:
        return
    jobs: List[Dict[str, Any]] = []
    async with AsyncSessionLocal() as session:
        await set_tenant_context(session, tenant_id)
        customer_id = (await session.execute(select(Booking.customer_id).where(
            Booking.id == booking_id, Booking.tenant_id == tenant_id))).scalar_one_or_none()
        if customer_id is None:
            return
        await session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                              {"key": f"customer:{tenant_id}:{customer_id}"})
        owner_id = (await session.execute(select(User.assigned_staff_id).where(
            User.id == customer_id, User.tenant_id == tenant_id))).scalar_one()
        staff_id = (await session.execute(select(Booking.staff_id).where(
            Booking.tenant_id == tenant_id, Booking.id == booking_id))).scalar_one()
        roles = dict((await session.execute(select(User.id, User.role).where(
            User.tenant_id == tenant_id, User.id.in_({d.user_id for d in drafts}),
            User.is_active.is_(True)))).all())
        drafts = [d for d in drafts if d.user_id in roles and (
            roles[d.user_id] == UserRole.ADMIN or d.user_id == customer_id or
            (roles[d.user_id] == UserRole.STAFF and d.user_id in {owner_id, staff_id}))]
        event_id = _current_event.get()
        if event_id is not None:
            existing = set((await session.execute(select(Notification.user_id).where(
                Notification.tenant_id == tenant_id, Notification.event_id == event_id))).scalars().all())
            drafts = [d for d in drafts if d.user_id not in existing]
        if ntype == "BOOKING_CREATED":
            # Retries of a committed counter batch must not duplicate notifications/push.
            existing = set((await session.execute(select(Notification.user_id).where(
                Notification.tenant_id == tenant_id, Notification.booking_id == booking_id,
                Notification.type == ntype, Notification.user_id.in_({d.user_id for d in drafts})
            ))).scalars().all())
            drafts = [d for d in drafts if d.user_id not in existing]
        if not drafts:
            return
        # Notification INSERTs acquire FK KEY SHARE locks on users and bookings.
        # Acquire recipient locks first, in the same order as auto-assignment,
        # so an INSERT cannot hold a booking FK lock while waiting for its staff.
        await session.execute(
            select(User.id)
            .where(User.tenant_id == tenant_id, User.id.in_({d.user_id for d in drafts}))
            .order_by(User.id)
            .with_for_update(read=True, key_share=True)
        )
        rows = [
            Notification(
                tenant_id=tenant_id, user_id=d.user_id, title=d.title, body=d.body, type=ntype, booking_id=booking_id, event_id=event_id
            )
            for d in sorted(drafts, key=lambda x: x.user_id)
        ]
        session.add_all(rows)
        await session.flush()
        if webpush_enabled():
            subs = (
                await session.execute(
                    select(PushSubscription).where(
                        PushSubscription.tenant_id == tenant_id,
                        PushSubscription.user_id.in_({d.user_id for d in drafts}),
                    )
                )
            ).scalars().all()
            by_user: Dict[uuid.UUID, Notification] = {n.user_id: n for n in rows}
            urls = {d.user_id: d.url for d in drafts}
            for s in subs:
                n = by_user[s.user_id]
                session.add(NotificationDispatch(tenant_id=tenant_id, notification_id=n.id, subscription_id=s.id,
                    url=urls[s.user_id] + "?booking_id=" + str(booking_id)))
        await session.commit()
    from app.services.notification_queue import drain_push
    await drain_push(tenant_id)



async def notify_booking_event(
    tenant_id: uuid.UUID, booking_id: uuid.UUID, event: str, actor_id: uuid.UUID, to_staff: bool, *, event_id: uuid.UUID | None = None, strict: bool = False
) -> None:
    """Chạy trong BackgroundTasks: KHÔNG bao giờ raise (không ảnh hưởng transaction đặt lịch chính).

    event: CREATED | RESCHEDULED | CONFIRMED | IN_PROGRESS | COMPLETED | CANCELLED | NO_SHOW
    to_staff=True  -> gửi ADMIN, KTV thực hiện và người phụ trách hồ sơ (trừ người thực hiện thao tác)
    to_staff=False -> gửi CUSTOMER sở hữu lịch hẹn
    """
    event_token = _current_event.set(event_id)
    try:
        async with AsyncSessionLocal() as session:
            await set_tenant_context(session, tenant_id)
            booking = (
                await session.execute(select(Booking).where(Booking.id == booking_id, Booking.tenant_id == tenant_id))
            ).scalar_one_or_none()
            if booking is None:
                return
            customer = (
                await session.execute(select(User).where(User.id == booking.customer_id, User.tenant_id == tenant_id))
            ).scalar_one()
            staff_name: Optional[str] = None
            if booking.staff_id is not None:
                staff_name = (
                    await session.execute(
                        select(User.full_name).where(User.id == booking.staff_id, User.tenant_id == tenant_id)
                    )
                ).scalar_one_or_none()
            when = booking.start_time.astimezone(TZ).strftime("%H:%M %d/%m/%Y")
            drafts: List[Draft] = []
            if to_staff:
                recipients = (
                    await session.execute(
                        select(User.id).where(
                            User.tenant_id == tenant_id,
                            or_(User.role == UserRole.ADMIN,
                                (User.role == UserRole.STAFF) & User.id.in_([uid for uid in
                                    {customer.assigned_staff_id, booking.staff_id} if uid is not None])),
                            User.is_active.is_(True),
                            User.id != actor_id,
                        )
                    )
                ).scalars().all()
                for uid in recipients:
                    if event == "CREATED":
                        assigned = uid == booking.staff_id
                        title = "Lịch hẹn mới được giao cho bạn" if assigned else "Có lịch hẹn mới"
                        body = f"{customer.full_name} đặt lịch lúc {when}" + (f" - KTV {staff_name}" if staff_name else "")
                    elif event == "RESCHEDULED":
                        title = "Khách đã đổi lịch hẹn"
                        body = f"{customer.full_name} đổi lịch sang {when}"
                    else:
                        title = "Khách đã hủy lịch hẹn"
                        body = f"{customer.full_name} đã hủy lịch lúc {when}"
                    drafts.append(Draft(uid, title, body))
            elif booking.customer_id != actor_id:
                slug = (await session.execute(select(Tenant.slug).where(Tenant.id == tenant_id))).scalar_one()
                drafts.append(Draft(
                    booking.customer_id, _STATUS_TITLES.get(event, "Cập nhật lịch hẹn"),
                    f"Lịch hẹn lúc {when}" + (f" - KTV {staff_name}" if staff_name else ""), f"/{slug}/appointments",
                ))
        await _deliver(tenant_id, drafts, f"BOOKING_{event}", booking_id)
    except Exception:  # noqa: BLE001 - thông báo lỗi không được phép ảnh hưởng nghiệp vụ chính
        if strict:
            raise
        logger.warning("Gửi thông báo thất bại; sẽ kiểm tra tác vụ chưa hoàn tất")
    finally:
        _current_event.reset(event_token)
