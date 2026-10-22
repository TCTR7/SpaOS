import uuid
from datetime import date as date_type
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
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
from app.services.notification_queue import drain_events
from app.services.customer_access import booking_access
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.schemas.manual_booking import ManualBatchIn, ManualBatchOut
from app.services import manual_booking_service

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
) -> BookingOut:
    booking = await svc.create_booking(db, tenant_id, user, body)
    background_tasks.add_task(drain_events, tenant_id)
    return (await svc.present_bookings(db, tenant_id, [booking], actor=user))[0]


@router.get("", response_model=List[BookingOut])
async def list_bookings(
    response: Response,
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
) -> List[BookingOut]:
    if user.role == UserRole.CUSTOMER:
        customer_id = user.id  # khách chỉ xem lịch của chính mình
    rows = await svc.list_bookings(
        db,
        tenant_id,
        customer_id=customer_id,
        staff_id=staff_id,
        booking_status=booking_status,
        date_from=date_from,
        date_to=date_to,
        scope=scope,
        limit=limit + 1,
        offset=offset,
        actor=user,
    )
    response.headers["X-Has-More"] = str(len(rows) > limit).lower()
    response.headers["X-Next-Offset"] = str(offset + limit) if len(rows) > limit else ""
    return await svc.present_bookings(db, tenant_id, rows[:limit], actor=user)


@router.post("/manual-batches", response_model=ManualBatchOut, status_code=201)
async def create_manual_batch(body: ManualBatchIn, background_tasks: BackgroundTasks, actor: User = Depends(_admin_staff),
                              tenant_id: uuid.UUID = Depends(get_current_tenant_id),
                              db: AsyncSession = Depends(get_tenant_db)):
    result = await manual_booking_service.create_batch(db, tenant_id, actor, body)
    background_tasks.add_task(drain_events, tenant_id)
    return result


@router.get("/manual-batches/{request_id}", response_model=ManualBatchOut)
async def get_manual_batch(request_id: uuid.UUID, actor: User = Depends(_admin_staff),
                           tenant_id: uuid.UUID = Depends(get_current_tenant_id),
                           db: AsyncSession = Depends(get_tenant_db)):
    return await manual_booking_service.get_result(db, tenant_id, actor, request_id)


@router.get("/{booking_id}", response_model=BookingOut)
async def get_booking(
    booking_id: uuid.UUID,
    user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> BookingOut:
    await booking_access(db, tenant_id, booking_id, user, allow_assigned=True)
    booking = await svc.get_booking_full(db, tenant_id, booking_id)
    if booking is None or (user.role == UserRole.CUSTOMER and booking.customer_id != user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy lịch hẹn")
    return (await svc.present_bookings(db, tenant_id, [booking], actor=user))[0]


@router.get("/{booking_id}/available-slots", response_model=AvailableSlotsOut)
async def reschedule_slots(
    booking_id: uuid.UUID,
    day: date_type = Query(..., alias="date"),
    staff_id: Optional[uuid.UUID] = None,
    user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> AvailableSlotsOut:
    # Exclusion is derived only from this authorized booking, never a public query ID.
    await booking_access(db, tenant_id, booking_id, user)
    booking = await svc.get_booking_full(db, tenant_id, booking_id)
    if booking.status not in (BookingStatus.PENDING, BookingStatus.CONFIRMED):
        raise HTTPException(409, "Chỉ được sửa lịch PENDING/CONFIRMED")
    if user.role == UserRole.CUSTOMER and booking.start_time - datetime.now(timezone.utc) < timedelta(hours=settings.CANCELLATION_MIN_HOURS):
        raise HTTPException(409, "Chỉ được đổi lịch trước giờ hẹn tối thiểu 2 giờ")
    tenant = await svc.load_tenant(db, tenant_id)
    staff_ids = [staff_id] if staff_id else await svc.list_active_staff_ids(db, tenant_id)
    if staff_id:
        await svc.get_active_staff(db, tenant_id, staff_id)
    slots = await svc.compute_available_slots(db, tenant, day, booking.total_duration_minutes,
        staff_ids, exclude_booking_id=booking.id,
        include_start=booking.start_time if booking.start_time.astimezone(svc.TZ).date() == day else None)
    return AvailableSlotsOut(date=day, total_duration_minutes=booking.total_duration_minutes,
        buffer_minutes=tenant.buffer_minutes, slot_step_minutes=svc.SLOT_STEP_MINUTES,
        slots=[SlotOut(start_time=s.astimezone(svc.TZ), end_time=e.astimezone(svc.TZ), available_staff_ids=ids)
               for s, e, ids in slots])


@router.patch("/{booking_id}/status", response_model=BookingOut)
async def update_status(
    booking_id: uuid.UUID,
    body: BookingStatusUpdate,
    background_tasks: BackgroundTasks,
    user: User = Depends(_admin_staff),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> BookingOut:
    booking, changed = await svc.update_booking_status(db, tenant_id, booking_id, body.status, actor=user)
    if changed: background_tasks.add_task(drain_events, tenant_id)
    return (await svc.present_bookings(db, tenant_id, [booking], actor=user))[0]


@router.post("/{booking_id}/cancel", response_model=BookingOut)
async def cancel_booking(
    booking_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> BookingOut:
    booking, changed = await svc.cancel_booking(db, tenant_id, user, booking_id)
    if changed: background_tasks.add_task(drain_events, tenant_id)
    return (await svc.present_bookings(db, tenant_id, [booking], actor=user))[0]


@router.patch("/{booking_id}", response_model=BookingOut)
async def edit_booking(booking_id: uuid.UUID, body: BookingUpdate,
                       background_tasks: BackgroundTasks,
                       user: User = Depends(get_current_user),
                       tenant_id: uuid.UUID = Depends(get_current_tenant_id),
                       db: AsyncSession = Depends(get_tenant_db)):
    booking = await svc.reschedule_booking(db, tenant_id, user, booking_id, body)
    background_tasks.add_task(drain_events, tenant_id)
    return (await svc.present_bookings(db, tenant_id, [booking], actor=user))[0]
