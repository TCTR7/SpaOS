import uuid
from datetime import date as date_type
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.booking_deps import TenantCtx, get_optional_tenant_ctx
from app.api.deps import get_current_tenant_id, get_current_user, get_tenant_db, require_roles
from app.models.models import Booking, BookingStatus, User, UserRole
from app.schemas.booking import (
    AvailableSlotsOut,
    BookingCreate,
    BookingUpdate,
    BookingOut,
    BookingStatusUpdate,
    SlotOut,
)
from app.services import booking_service as svc
from app.services.notification_service import notify_booking_event
from app.services.customer_access import booking_access

router = APIRouter(prefix="/bookings", tags=["bookings"])

_admin_staff = require_roles(UserRole.ADMIN, UserRole.STAFF)


@router.get("/available-slots", response_model=AvailableSlotsOut)
async def available_slots(
    day: date_type = Query(..., alias="date", description="YYYY-MM-DD (theo giờ Asia/Ho_Chi_Minh)"),
    service_ids: List[uuid.UUID] = Query(..., min_length=1, max_length=10),
    staff_id: Optional[uuid.UUID] = None,
    ctx: TenantCtx = Depends(get_optional_tenant_ctx),
) -> AvailableSlotsOut:
    """Khách (header `X-Tenant-Slug` hoặc JWT) và Admin/Staff (JWT) đều gọi được."""
    db, tenant_id = ctx.db, ctx.tenant_id
    tenant = await svc.load_tenant(db, tenant_id)
    services = await svc.load_services(db, tenant_id, service_ids)
    duration = svc.total_duration(service_ids, services)

    if staff_id is not None:
        await svc.get_active_staff(db, tenant_id, staff_id)
        staff_ids = [staff_id]
    else:
        staff_ids = await svc.list_active_staff_ids(db, tenant_id)

    slots = await svc.compute_available_slots(db, tenant, day, duration, staff_ids)
    return AvailableSlotsOut(
        date=day,
        total_duration_minutes=duration,
        buffer_minutes=tenant.buffer_minutes,
        slot_step_minutes=svc.SLOT_STEP_MINUTES,
        slots=[
            SlotOut(start_time=s.astimezone(svc.TZ), end_time=e.astimezone(svc.TZ), available_staff_ids=ids)
            for s, e, ids in slots
        ],
    )


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
async def create_booking(
    body: BookingCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> Booking:
    booking = await svc.create_booking(db, tenant_id, user, body)
    if user.role == UserRole.CUSTOMER:  # khách tự đặt -> báo ADMIN/STAFF (non-blocking, lỗi push không ảnh hưởng đặt lịch)
        background_tasks.add_task(notify_booking_event, tenant_id, booking.id, "CREATED", user.id, True)
    return booking


@router.get("", response_model=List[BookingOut])
async def list_bookings(
    date_from: Optional[date_type] = None,
    date_to: Optional[date_type] = None,
    staff_id: Optional[uuid.UUID] = None,
    booking_status: Optional[BookingStatus] = Query(default=None, alias="status"),
    customer_id: Optional[uuid.UUID] = None,
    scope: Optional[str] = Query(default=None, pattern="^(upcoming|history)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> List[Booking]:
    if user.role == UserRole.CUSTOMER:
        customer_id = user.id  # khách chỉ xem lịch của chính mình
    return await svc.list_bookings(
        db,
        tenant_id,
        customer_id=customer_id,
        staff_id=staff_id,
        booking_status=booking_status,
        date_from=date_from,
        date_to=date_to,
        scope=scope,
        limit=limit,
        offset=offset,
        actor=user,
    )


@router.get("/{booking_id}", response_model=BookingOut)
async def get_booking(
    booking_id: uuid.UUID,
    user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> Booking:
    await booking_access(db, tenant_id, booking_id, user)
    booking = await svc.get_booking_full(db, tenant_id, booking_id)
    if booking is None or (user.role == UserRole.CUSTOMER and booking.customer_id != user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy lịch hẹn")
    return booking


@router.patch("/{booking_id}/status", response_model=BookingOut)
async def update_status(
    booking_id: uuid.UUID,
    body: BookingStatusUpdate,
    background_tasks: BackgroundTasks,
    user: User = Depends(_admin_staff),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> Booking:
    booking, changed = await svc.update_booking_status(db, tenant_id, booking_id, body.status, actor=user)
    if changed:  # báo CUSTOMER sở hữu lịch hẹn
        background_tasks.add_task(notify_booking_event, tenant_id, booking.id, booking.status.value, user.id, False)
    return booking


@router.post("/{booking_id}/cancel", response_model=BookingOut)
async def cancel_booking(
    booking_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> Booking:
    booking, changed = await svc.cancel_booking(db, tenant_id, user, booking_id)
    if changed:  # khách hủy -> báo ADMIN/STAFF; Admin/Staff hủy -> báo khách
        background_tasks.add_task(
            notify_booking_event, tenant_id, booking.id, "CANCELLED", user.id, user.role == UserRole.CUSTOMER
        )
    return booking


@router.patch("/{booking_id}", response_model=BookingOut)
async def edit_booking(booking_id: uuid.UUID, body: BookingUpdate,
                       background_tasks: BackgroundTasks,
                       user: User = Depends(get_current_user),
                       tenant_id: uuid.UUID = Depends(get_current_tenant_id),
                       db: AsyncSession = Depends(get_tenant_db)):
    booking = await svc.reschedule_booking(db, tenant_id, user, booking_id, body)
    background_tasks.add_task(notify_booking_event, tenant_id, booking.id, "RESCHEDULED",
                              user.id, user.role == UserRole.CUSTOMER)
    return booking
