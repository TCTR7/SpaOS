import uuid
from typing import List

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, status
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.api.deps import get_current_tenant_id, get_current_user, get_tenant_db
from app.api.utils import commit_and_refresh
from app.core.config import settings
from app.core.database import set_tenant_context
from app.models.models import Notification, PushSubscription, User, UserRole, Booking
from app.services.customer_access import booking_read_scope
from app.schemas.sprint4 import (
    NotificationListOut,
    NotificationOut,
    ReadAllOut,
    SubscribeRequest,
    SubscriptionOut,
    UnsubscribeOut,
    UnsubscribeRequest,
    VapidKeyOut,
)
from app.services.booking_service import HTTP_422
from app.services.notification_service import webpush_enabled

router = APIRouter(prefix="/notifications", tags=["notifications"])


def visible_notifications(tenant_id, user):
    base = (Notification.tenant_id == tenant_id) & (Notification.user_id == user.id)
    if user.role == UserRole.STAFF:
        base = base & Notification.booking_id.in_(select(Booking.id).where(
            Booking.tenant_id == tenant_id,
            booking_read_scope(tenant_id, user)))
    return base


@router.get("/vapid-public-key", response_model=VapidKeyOut)
async def vapid_public_key() -> VapidKeyOut:
    """Public key (không bí mật) để Frontend gọi `pushManager.subscribe({ applicationServerKey })`."""
    return VapidKeyOut(public_key=settings.VAPID_PUBLIC_KEY, enabled=webpush_enabled())


@router.post("/subscribe", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
async def subscribe(
    body: SubscribeRequest,
    user_agent: Optional[str] = Header(default=None),
    user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> PushSubscription:
    if not body.endpoint.startswith("https://"):
        raise HTTPException(status_code=HTTP_422, detail="endpoint phải là URL https")
    # Serialize endpoint ownership changes, including the first INSERT (no row yet).
    # Transaction-scoped and tenant-specific; released on commit/rollback.
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"push:{tenant_id}:{body.endpoint}"},
    )
    # 1 trình duyệt chỉ thuộc về 1 user: bỏ đăng ký của user khác trên cùng endpoint (đăng xuất/đăng nhập tài khoản khác)
    await db.execute(
        delete(PushSubscription).where(
            PushSubscription.tenant_id == tenant_id,
            PushSubscription.endpoint == body.endpoint,
            PushSubscription.user_id != user.id,
        )
    )
    sub = (
        await db.execute(
            select(PushSubscription).where(
                PushSubscription.tenant_id == tenant_id,
                PushSubscription.user_id == user.id,
                PushSubscription.endpoint == body.endpoint,
            )
        )
    ).scalar_one_or_none()
    if sub is None:
        sub = PushSubscription(tenant_id=tenant_id, user_id=user.id, endpoint=body.endpoint, p256dh="", auth="")
        db.add(sub)
    sub.p256dh = body.keys.p256dh
    sub.auth = body.keys.auth
    sub.user_agent = (user_agent or "")[:500] or None
    await commit_and_refresh(db, tenant_id, sub)
    return sub


@router.delete("/unsubscribe", response_model=UnsubscribeOut)
async def unsubscribe(
    body: UnsubscribeRequest = Body(...),
    user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> UnsubscribeOut:
    result = await db.execute(
        delete(PushSubscription).where(
            PushSubscription.tenant_id == tenant_id,
            PushSubscription.user_id == user.id,
            PushSubscription.endpoint == body.endpoint,
        )
    )
    await db.commit()
    return UnsubscribeOut(deleted=result.rowcount or 0)


@router.get("", response_model=NotificationListOut)
async def list_notifications(
    unread_only: bool = False,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> NotificationListOut:
    base = visible_notifications(tenant_id, user)
    unread = (
        await db.execute(select(func.count(Notification.id)).where(base, Notification.is_read.is_(False)))
    ).scalar_one()
    stmt = select(Notification).where(base)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    rows = (
        await db.execute(stmt.order_by(Notification.created_at.desc(), Notification.id).limit(limit).offset(offset))
    ).scalars().all()
    return NotificationListOut(unread_count=unread, items=[NotificationOut.model_validate(n) for n in rows])


# Khai báo trước `/{id}/read` cho rõ ràng (đường dẫn khác số segment nên không xung đột)
@router.patch("/read-all", response_model=ReadAllOut)
async def read_all(
    user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> ReadAllOut:
    result = await db.execute(
        update(Notification)
        .where(visible_notifications(tenant_id, user), Notification.is_read.is_(False))
        .values(is_read=True)
    )
    await db.commit()
    return ReadAllOut(updated=result.rowcount or 0)


@router.patch("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> Notification:
    notification = (
        await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                visible_notifications(tenant_id, user),
            )
        )
    ).scalar_one_or_none()
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy thông báo")
    notification.is_read = True
    await commit_and_refresh(db, tenant_id, notification)
    return notification
