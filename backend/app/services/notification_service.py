import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.models import Booking, Notification, PushSubscription, User, UserRole
from app.services.booking_service import TZ

logger = logging.getLogger("spaos.notifications")

_STATUS_TITLES = {
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
                tenant_id=tenant_id, user_id=d.user_id, title=d.title, body=d.body, type=ntype, booking_id=booking_id
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
            for s in subs:
                n = by_user[s.user_id]
                payload = json.dumps(
                    {
                        "title": n.title,
                        "body": n.body,
                        "type": n.type,
                        "booking_id": str(booking_id),
                        "notification_id": str(n.id),
                    },
                    ensure_ascii=False,
                )
                jobs.append(
                    {"sub_id": s.id, "sub": {"endpoint": s.endpoint, "p256dh": s.p256dh, "auth": s.auth}, "payload": payload}
                )
        await session.commit()

    if not jobs:
        return
    results = await asyncio.gather(*[_send_one(j["sub"], j["payload"]) for j in jobs], return_exceptions=True)
    expired: List[uuid.UUID] = []
    for job, res in zip(jobs, results):
        if isinstance(res, BaseException):
            logger.warning("Web Push lỗi (%s): %s", job["sub_id"], res)
        elif res in (404, 410):
            expired.append(job["sub_id"])  # subscription đã hết hạn/bị thu hồi -> dọn
        elif res is not None:
            logger.warning("Web Push thất bại status=%s sub=%s", res, job["sub_id"])
    if expired:
        async with AsyncSessionLocal() as session:
            await set_tenant_context(session, tenant_id)
            await session.execute(
                delete(PushSubscription).where(PushSubscription.tenant_id == tenant_id, PushSubscription.id.in_(expired))
            )
            await session.commit()


async def notify_booking_event(
    tenant_id: uuid.UUID, booking_id: uuid.UUID, event: str, actor_id: uuid.UUID, to_staff: bool
) -> None:
    """Chạy trong BackgroundTasks: KHÔNG bao giờ raise (không ảnh hưởng transaction đặt lịch chính).

    event: CREATED | CONFIRMED | IN_PROGRESS | COMPLETED | CANCELLED | NO_SHOW
    to_staff=True  -> gửi ADMIN/STAFF của Spa (trừ người thực hiện)
    to_staff=False -> gửi CUSTOMER sở hữu lịch hẹn
    """
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
                            User.role.in_((UserRole.ADMIN, UserRole.STAFF)),
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
                    else:
                        title = "Khách đã hủy lịch hẹn"
                        body = f"{customer.full_name} đã hủy lịch lúc {when}"
                    drafts.append(Draft(uid, title, body))
            elif booking.customer_id != actor_id:
                drafts.append(Draft(booking.customer_id, _STATUS_TITLES.get(event, "Cập nhật lịch hẹn"), f"Lịch hẹn lúc {when}"))
        await _deliver(tenant_id, drafts, f"BOOKING_{event}", booking_id)
    except Exception:  # noqa: BLE001 - thông báo lỗi không được phép ảnh hưởng nghiệp vụ chính
        logger.exception("Gửi thông báo thất bại (booking=%s, event=%s)", booking_id, event)
