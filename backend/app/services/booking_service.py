import uuid
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import set_tenant_context
from app.models.models import (
    Booking,
    BookingItem,
    BookingStatus,
    CustomerPackage,
    PackageStatus,
    Service,
    StaffSchedule,
    Tenant,
    User,
    UserRole,
)
from app.schemas.booking import BookingCreate, BookingUpdate, BookingOut
from app.services.audit_service import audit
from app.services.customer_access import customer_access, booking_access, customer_scope, booking_read_scope

TZ = ZoneInfo(settings.DEFAULT_TIMEZONE)
SLOT_STEP_MINUTES = 15
HTTP_422 = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)

# Booking còn "giữ chỗ" (chiếm lịch KTV và chiếm buổi trong thẻ liệu trình)
ACTIVE_STATUSES = (BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS)

ALLOWED_TRANSITIONS: Dict[BookingStatus, Tuple[BookingStatus, ...]] = {
    BookingStatus.PENDING: (BookingStatus.CONFIRMED, BookingStatus.CANCELLED),
    BookingStatus.CONFIRMED: (
        BookingStatus.IN_PROGRESS,
        BookingStatus.COMPLETED,
        BookingStatus.CANCELLED,
        BookingStatus.NO_SHOW,
    ),
    BookingStatus.IN_PROGRESS: (BookingStatus.COMPLETED, BookingStatus.CANCELLED),
    BookingStatus.COMPLETED: (),
    BookingStatus.CANCELLED: (),
    BookingStatus.NO_SHOW: (),
}


# ---------------------------------------------------------------- time helpers
def day_of_week_index(d: date) -> int:
    """Quy ước PRD: 0=Chủ nhật, 1=Thứ 2 ... 6=Thứ 7 (Python weekday(): 0=Thứ 2 ... 6=Chủ nhật)."""
    return (d.weekday() + 1) % 7


def ensure_aware(dt: datetime) -> datetime:
    """Datetime không offset được hiểu là giờ Asia/Ho_Chi_Minh."""
    return dt.replace(tzinfo=TZ) if dt.tzinfo is None else dt


def local_day_bounds(d: date) -> Tuple[datetime, datetime]:
    start = datetime.combine(d, time.min, tzinfo=TZ)
    return start, start + timedelta(days=1)


def _fits(windows: List[Tuple[datetime, datetime]], start: datetime, end: datetime) -> bool:
    return any(w0 <= start and end <= w1 for w0, w1 in windows)


def _conflicts(busy: List[Booking], start: datetime, end: datetime, buffer_minutes: int) -> bool:
    """Booking cũ chiếm [start, end + buffer); khoảng mới là [start, end + buffer)."""
    buf = timedelta(minutes=buffer_minutes)
    new_end_buf = end + buf
    return any(start < b.end_time + buf and new_end_buf > b.start_time for b in busy)


# ---------------------------------------------------------------- loaders
async def load_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant is None or tenant.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy Spa")
    return tenant


async def load_services(db: AsyncSession, tenant_id: uuid.UUID, service_ids: List[uuid.UUID]) -> Dict[uuid.UUID, Service]:
    unique = set(service_ids)
    rows = (
        await db.execute(
            select(Service).where(
                Service.tenant_id == tenant_id, Service.id.in_(unique), Service.is_active.is_(True)
            )
        )
    ).scalars().all()
    found = {s.id: s for s in rows}
    if len(found) != len(unique):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dịch vụ không tồn tại hoặc đã ngừng hoạt động")
    return found


def total_duration(service_ids: List[uuid.UUID], services: Dict[uuid.UUID, Service]) -> int:
    return sum(services[sid].duration_minutes for sid in service_ids)


async def get_active_staff(db: AsyncSession, tenant_id: uuid.UUID, staff_id: uuid.UUID) -> User:
    staff = (
        await db.execute(
            select(User).where(
                User.id == staff_id,
                User.tenant_id == tenant_id,
                User.role == UserRole.STAFF,
                User.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if staff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy kỹ thuật viên")
    return staff


async def list_active_staff_ids(db: AsyncSession, tenant_id: uuid.UUID) -> List[uuid.UUID]:
    rows = await db.execute(
        select(User.id)
        .where(User.tenant_id == tenant_id, User.role == UserRole.STAFF, User.is_active.is_(True))
        .order_by(User.id)
    )
    return list(rows.scalars().all())


async def get_schedule_windows(
    db: AsyncSession, tenant: Tenant, staff_ids: List[uuid.UUID], d: date
) -> Dict[uuid.UUID, List[Tuple[datetime, datetime]]]:
    """Khung giờ làm việc (aware, Asia/Ho_Chi_Minh) của từng KTV trong ngày `d`, đã giao với giờ mở/đóng cửa."""
    result: Dict[uuid.UUID, List[Tuple[datetime, datetime]]] = {sid: [] for sid in staff_ids}
    if not staff_ids:
        return result
    rows = (
        await db.execute(
            select(StaffSchedule).where(
                StaffSchedule.tenant_id == tenant.id,
                StaffSchedule.staff_id.in_(staff_ids),
                StaffSchedule.day_of_week == day_of_week_index(d),
            )
        )
    ).scalars().all()
    day_off = {r.staff_id for r in rows if r.is_day_off}
    for r in rows:
        if r.staff_id in day_off:
            continue
        w_start = max(tenant.open_time, r.start_time)
        w_end = min(tenant.close_time, r.end_time)
        if w_start < w_end:
            result[r.staff_id].append(
                (datetime.combine(d, w_start, tzinfo=TZ), datetime.combine(d, w_end, tzinfo=TZ))
            )
    return result


async def fetch_busy(
    db: AsyncSession,
    tenant: Tenant,
    staff_ids: List[uuid.UUID],
    day_start: datetime,
    day_end: datetime,
    lock: bool = False,
) -> Dict[uuid.UUID, List[Booking]]:
    """Booking (khác CANCELLED) của các KTV có thể ảnh hưởng tới khoảng [day_start, day_end)."""
    busy: Dict[uuid.UUID, List[Booking]] = {sid: [] for sid in staff_ids}
    if not staff_ids:
        return busy
    stmt = (
        select(Booking)
        .where(
            Booking.tenant_id == tenant.id,
            Booking.staff_id.in_(staff_ids),
            Booking.status != BookingStatus.CANCELLED,
            Booking.start_time < day_end + timedelta(minutes=tenant.buffer_minutes),
            Booking.end_time > day_start - timedelta(minutes=tenant.buffer_minutes),
        )
        .order_by(Booking.id)
    )
    if lock:
        stmt = stmt.with_for_update()
    for b in (await db.execute(stmt)).scalars().all():
        busy[b.staff_id].append(b)
    return busy


# ---------------------------------------------------------------- available slots
async def compute_available_slots(
    db: AsyncSession,
    tenant: Tenant,
    d: date,
    duration_minutes: int,
    staff_ids: List[uuid.UUID],
    *, exclude_booking_id: Optional[uuid.UUID] = None, include_start: Optional[datetime] = None,
) -> List[Tuple[datetime, datetime, List[uuid.UUID]]]:
    windows = await get_schedule_windows(db, tenant, staff_ids, d)
    day_start, day_end = local_day_bounds(d)
    busy = await fetch_busy(db, tenant, staff_ids, day_start, day_end)
    if exclude_booking_id is not None:
        busy = {sid: [b for b in rows if b.id != exclude_booking_id] for sid, rows in busy.items()}
    now = datetime.now(timezone.utc)
    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=SLOT_STEP_MINUTES)

    slots: Dict[datetime, List[uuid.UUID]] = {}
    for sid in staff_ids:
        for w_start, w_end in windows[sid]:
            slot_start = w_start
            while slot_start + duration <= w_end:
                if slot_start > now and not _conflicts(busy[sid], slot_start, slot_start + duration, tenant.buffer_minutes):
                    ids = slots.setdefault(slot_start, [])
                    if sid not in ids:
                        ids.append(sid)
                slot_start += step
            if include_start is not None and w_start <= include_start and include_start + duration <= w_end:
                if include_start > now and not _conflicts(busy[sid], include_start, include_start + duration, tenant.buffer_minutes):
                    ids = slots.setdefault(include_start, [])
                    if sid not in ids:
                        ids.append(sid)
    return [(s, s + duration, ids) for s, ids in sorted(slots.items())]


# ---------------------------------------------------------------- booking helpers
async def get_booking_full(
    db: AsyncSession, tenant_id: uuid.UUID, booking_id: uuid.UUID, lock: bool = False
) -> Optional[Booking]:
    stmt = (
        select(Booking)
        .options(selectinload(Booking.items.and_(BookingItem.tenant_id == tenant_id)))
        .where(Booking.id == booking_id, Booking.tenant_id == tenant_id)
        .execution_options(populate_existing=True)
    )
    if lock:
        stmt = stmt.with_for_update()
    return (await db.execute(stmt)).scalar_one_or_none()


async def _lock_packages(
    db: AsyncSession, tenant_id: uuid.UUID, package_ids: List[uuid.UUID]
) -> Dict[uuid.UUID, CustomerPackage]:
    """Lock theo thứ tự id tăng dần để tránh deadlock giữa các transaction."""
    if not package_ids:
        return {}
    rows = (
        await db.execute(
            select(CustomerPackage)
            .where(CustomerPackage.tenant_id == tenant_id, CustomerPackage.id.in_(package_ids))
            .order_by(CustomerPackage.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalars().all()
    return {p.id: p for p in rows}


async def _pending_package_uses(db: AsyncSession, tenant_id: uuid.UUID, package_id: uuid.UUID) -> int:
    """Số buổi của thẻ đang bị giữ bởi booking PENDING/CONFIRMED/IN_PROGRESS (chưa COMPLETED)."""
    result = await db.execute(
        select(func.count(BookingItem.id))
        .join(Booking, Booking.id == BookingItem.booking_id)
        .where(
            BookingItem.tenant_id == tenant_id,
            Booking.tenant_id == tenant_id,
            BookingItem.customer_package_id == package_id,
            Booking.status.in_(ACTIVE_STATUSES),
        )
    )
    return int(result.scalar_one())


async def _check_staff_free(
    db: AsyncSession, tenant: Tenant, staff_id: uuid.UUID, start: datetime, end: datetime
) -> Optional[str]:
    """Trả về None nếu KTV rảnh, ngược lại trả lý do. Lock các booking của KTV trong ngày (FOR UPDATE)."""
    local_day = start.astimezone(TZ).date()
    windows = (await get_schedule_windows(db, tenant, [staff_id], local_day))[staff_id]
    if not _fits(windows, start, end):
        return "Kỹ thuật viên không làm việc trong khung giờ này"
    day_start, day_end = local_day_bounds(local_day)
    busy = (await fetch_busy(db, tenant, [staff_id], day_start, day_end, lock=True))[staff_id]
    if _conflicts(busy, start, end, tenant.buffer_minutes):
        return "Kỹ thuật viên đã có lịch trong khung giờ này"
    return None


async def _lock_staff_row(db: AsyncSession, tenant_id: uuid.UUID, staff_id: uuid.UUID) -> Optional[User]:
    return (
        await db.execute(
            select(User)
            .where(
                User.id == staff_id,
                User.tenant_id == tenant_id,
                User.role == UserRole.STAFF,
                User.is_active.is_(True),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()


# ---------------------------------------------------------------- create booking
async def create_booking(db: AsyncSession, tenant_id: uuid.UUID, actor: User, body: BookingCreate,
                         *, commit: bool = True, staff_candidates: Optional[List[uuid.UUID]] = None) -> Booking:
    start = ensure_aware(body.start_time).astimezone(timezone.utc)
    now = datetime.now(timezone.utc)

    # 1. Khách hàng
    if actor.role == UserRole.CUSTOMER:
        if body.customer_id is not None and body.customer_id != actor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không được đặt lịch thay khách khác")
        customer = actor
        if start <= now:
            raise HTTPException(status_code=HTTP_422, detail="start_time phải ở tương lai")
    else:
        if body.customer_id is None:
            raise HTTPException(status_code=HTTP_422, detail="customer_id là bắt buộc khi tạo lịch tại quầy")
        customer = (
            await db.execute(
                select(User).where(
                    User.id == body.customer_id,
                    User.tenant_id == tenant_id,
                    User.role == UserRole.CUSTOMER,
                    User.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if customer is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy khách hàng")

    customer = await customer_access(db, tenant_id, customer.id, actor, write=True)

    # 2. Dịch vụ, thời lượng
    tenant = await load_tenant(db, tenant_id)
    service_ids = [i.service_id for i in body.items]
    services = await load_services(db, tenant_id, service_ids)
    duration = total_duration(service_ids, services)
    end = start + timedelta(minutes=duration)

    # 3. Thẻ liệu trình: lock FOR UPDATE (thứ tự id tăng dần) TRƯỚC khi lock KTV -> thứ tự lock nhất quán
    uses = Counter(i.customer_package_id for i in body.items if i.customer_package_id is not None)
    packages = await _lock_packages(db, tenant_id, sorted(uses))
    for pid, n in uses.items():
        pkg = packages.get(pid)
        if pkg is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy thẻ liệu trình")
        if pkg.customer_id != customer.id:
            raise HTTPException(status_code=HTTP_422, detail="Thẻ liệu trình không thuộc khách hàng này")
        if pkg.status != PackageStatus.ACTIVE:
            raise HTTPException(status_code=HTTP_422, detail="Thẻ liệu trình không còn hiệu lực")
        if pkg.expiry_date is not None and pkg.expiry_date <= start:
            raise HTTPException(status_code=HTTP_422, detail="Thẻ liệu trình đã hết hạn")
        remaining = pkg.total_sessions - pkg.used_sessions - await _pending_package_uses(db, tenant_id, pid)
        if remaining < n:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Thẻ liệu trình chỉ còn {max(remaining, 0)} buổi khả dụng",
            )
    for item in body.items:
        if item.customer_package_id is not None and packages[item.customer_package_id].service_id != item.service_id:
            raise HTTPException(status_code=HTTP_422, detail="Thẻ liệu trình không áp dụng cho dịch vụ này")

    # 4. Chọn + lock KTV, kiểm tra xung đột
    staff_id: Optional[uuid.UUID] = None
    if body.staff_id is not None:
        if await _lock_staff_row(db, tenant_id, body.staff_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy kỹ thuật viên")
        reason = await _check_staff_free(db, tenant, body.staff_id, start, end)
        if reason is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=reason)
        staff_id = body.staff_id
    else:
        local_day = start.astimezone(TZ).date()
        all_ids = staff_candidates if staff_candidates is not None else await list_active_staff_ids(db, tenant_id)
        windows = await get_schedule_windows(db, tenant, all_ids, local_day)
        # Chỉ lock các KTV có ca làm phù hợp; lock tuần tự theo id tăng dần (tránh deadlock)
        for sid in (s for s in all_ids if _fits(windows[s], start, end)):
            if await _lock_staff_row(db, tenant_id, sid) is None:
                continue
            if await _check_staff_free(db, tenant, sid, start, end) is None:
                staff_id = sid
                break
        if staff_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Không còn kỹ thuật viên trống trong khung giờ này"
            )

    # First successful booking establishes an owner; future bookings never transfer it.
    if customer.assigned_staff_id is None:
        customer.assigned_staff_id = staff_id
        audit(db, tenant_id, actor, "CUSTOMER_ASSIGNED", "customer", customer.id,
              {"from_staff_id": None, "to_staff_id": str(staff_id), "source": "first_booking"})

    # 5. Tạo booking + items
    items: List[BookingItem] = []
    total_price = Decimal("0")
    for item in body.items:
        svc = services[item.service_id]
        price = Decimal("0") if item.customer_package_id is not None else svc.price
        total_price += price
        items.append(
            BookingItem(
                tenant_id=tenant_id,
                service_id=svc.id,
                customer_package_id=item.customer_package_id,
                duration_minutes=svc.duration_minutes,
                price=price,
            )
        )
    booking = Booking(
        tenant_id=tenant_id,
        customer_id=customer.id,
        staff_id=staff_id,
        start_time=start,
        end_time=end,
        total_duration_minutes=duration,
        total_price=total_price,
        status=BookingStatus.PENDING,
        note=body.note,
        items=items,
    )
    db.add(booking)
    await db.flush()
    booking_id = booking.id
    audit(db, tenant_id, actor, "BOOKING_CREATED", "booking", booking.id,
          {"customer_id": str(customer.id), "staff_id": str(staff_id), "start_time": start.isoformat()})
    if not commit:
        return booking
    await db.commit()  # nhả toàn bộ lock

    await set_tenant_context(db, tenant_id)
    full = await get_booking_full(db, tenant_id, booking_id)
    assert full is not None
    return full


# ---------------------------------------------------------------- status / cancel
async def _consume_package_sessions(db: AsyncSession, tenant_id: uuid.UUID, booking: Booking) -> None:
    uses = Counter(i.customer_package_id for i in booking.items if i.customer_package_id is not None)
    packages = await _lock_packages(db, tenant_id, sorted(uses))
    for pid, n in uses.items():
        pkg = packages.get(pid)
        if pkg is None:
            continue
        if pkg.used_sessions + n > pkg.total_sessions:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Thẻ liệu trình đã dùng hết số buổi, không thể hoàn thành"
            )
        pkg.used_sessions += n
        if pkg.used_sessions == pkg.total_sessions:
            pkg.status = PackageStatus.COMPLETED


async def update_booking_status(
    db: AsyncSession, tenant_id: uuid.UUID, booking_id: uuid.UUID, new_status: BookingStatus, actor: Optional[User] = None
) -> Tuple[Booking, bool]:
    """Trả về (booking, changed). changed=False khi gửi lại đúng trạng thái hiện tại (no-op)."""
    if actor is not None:
        await booking_access(db, tenant_id, booking_id, actor, write=True)
    # Booking items are immutable after creation. Read their package IDs without
    # locking the booking, then follow create_booking's package -> booking order.
    # Re-read the status under the booking lock to keep COMPLETED idempotent.
    if new_status == BookingStatus.COMPLETED:
        package_ids = list((await db.execute(
            select(BookingItem.customer_package_id).where(
                BookingItem.tenant_id == tenant_id,
                BookingItem.booking_id == booking_id,
                BookingItem.customer_package_id.is_not(None),
            )
        )).scalars().all())
        await _lock_packages(db, tenant_id, package_ids)
    booking = await get_booking_full(db, tenant_id, booking_id, lock=True)
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy lịch hẹn")
    if booking.status == new_status:
        return booking, False  # idempotent
    if new_status not in ALLOWED_TRANSITIONS[booking.status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Không thể chuyển trạng thái {booking.status.value} -> {new_status.value}",
        )
    if new_status == BookingStatus.COMPLETED:
        await _consume_package_sessions(db, tenant_id, booking)
    previous_status = booking.status
    booking.status = new_status
    audit(db, tenant_id, actor, "BOOKING_STATUS_CHANGED", "booking", booking.id,
          {"from_status": previous_status.value, "to_status": new_status.value})
    await db.commit()

    await set_tenant_context(db, tenant_id)
    full = await get_booking_full(db, tenant_id, booking_id)
    assert full is not None
    return full, True


async def cancel_booking(
    db: AsyncSession, tenant_id: uuid.UUID, actor: User, booking_id: uuid.UUID
) -> Tuple[Booking, bool]:
    """Trả về (booking, changed)."""
    await booking_access(db, tenant_id, booking_id, actor, write=True)
    booking = await get_booking_full(db, tenant_id, booking_id, lock=True)
    if booking is None or (actor.role == UserRole.CUSTOMER and booking.customer_id != actor.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy lịch hẹn")
    if booking.status == BookingStatus.CANCELLED:
        return booking, False  # idempotent

    if actor.role == UserRole.CUSTOMER:
        if booking.status not in (BookingStatus.PENDING, BookingStatus.CONFIRMED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Chỉ được hủy lịch đang ở trạng thái PENDING/CONFIRMED"
            )
        if booking.start_time - datetime.now(timezone.utc) < timedelta(hours=settings.CANCELLATION_MIN_HOURS):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Chỉ được hủy lịch trước giờ hẹn tối thiểu {settings.CANCELLATION_MIN_HOURS} giờ",
            )
    elif BookingStatus.CANCELLED not in ALLOWED_TRANSITIONS[booking.status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Không thể hủy lịch ở trạng thái {booking.status.value}"
        )

    previous_status = booking.status
    booking.status = BookingStatus.CANCELLED
    audit(db, tenant_id, actor, "BOOKING_CANCELLED", "booking", booking.id,
          {"from_status": previous_status.value})
    await db.commit()
    await set_tenant_context(db, tenant_id)
    full = await get_booking_full(db, tenant_id, booking_id)
    assert full is not None
    return full, True


# ---------------------------------------------------------------- list
async def present_bookings(db: AsyncSession, tenant_id: uuid.UUID, bookings: List[Booking], actor: Optional[User] = None) -> List[BookingOut]:
    """Project names for already-authorized rows in two bounded queries; no lazy relationships."""
    if not bookings:
        return []
    user_ids = {b.customer_id for b in bookings} | {b.staff_id for b in bookings if b.staff_id}
    service_ids = {item.service_id for b in bookings for item in b.items}
    users = dict((await db.execute(select(User.id, User.full_name).where(
        User.tenant_id == tenant_id, User.id.in_(user_ids),
        User.role.in_([UserRole.CUSTOMER, UserRole.STAFF])
    ))).all())
    services = dict((await db.execute(select(Service.id, Service.name).where(
        Service.tenant_id == tenant_id, Service.id.in_(service_ids)
    ))).all())
    managed = set()
    if actor is not None and actor.role == UserRole.STAFF:
        managed = set((await db.execute(customer_scope(tenant_id, actor).where(User.id.in_({b.customer_id for b in bookings})))).scalars().all())
    return [BookingOut.model_validate(b).model_copy(update={
        "can_manage": actor is None or actor.role != UserRole.STAFF or b.customer_id in managed,
        "customer_name": users.get(b.customer_id), "staff_name": users.get(b.staff_id),
        "items": [item.model_copy(update={"service_name": services.get(item.service_id)})
                  for item in BookingOut.model_validate(b).items],
    }) for b in bookings]


async def list_bookings(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    customer_id: Optional[uuid.UUID],
    staff_id: Optional[uuid.UUID],
    booking_status: Optional[BookingStatus],
    date_from: Optional[date],
    date_to: Optional[date],
    scope: Optional[str],
    limit: int,
    offset: int,
    actor: Optional[User] = None,
) -> List[Booking]:
    stmt = select(Booking).options(selectinload(Booking.items.and_(BookingItem.tenant_id == tenant_id))).where(Booking.tenant_id == tenant_id)
    if actor is not None and actor.role == UserRole.STAFF:
        stmt = stmt.where(booking_read_scope(tenant_id, actor))
    if customer_id is not None:
        stmt = stmt.where(Booking.customer_id == customer_id)
    if staff_id is not None:
        stmt = stmt.where(Booking.staff_id == staff_id)
    if booking_status is not None:
        stmt = stmt.where(Booking.status == booking_status)
    if date_from is not None:
        stmt = stmt.where(Booking.start_time >= local_day_bounds(date_from)[0])
    if date_to is not None:
        stmt = stmt.where(Booking.start_time < local_day_bounds(date_to)[1])

    now = datetime.now(timezone.utc)
    upcoming = (Booking.status.in_(ACTIVE_STATUSES)) & (Booking.end_time >= now)
    if scope == "upcoming":
        stmt = stmt.where(upcoming).order_by(Booking.start_time, Booking.id)
    elif scope == "history":
        stmt = stmt.where(~upcoming).order_by(Booking.start_time.desc(), Booking.id)
    else:
        stmt = stmt.order_by(Booking.start_time.desc(), Booking.id)
    return list((await db.execute(stmt.limit(limit).offset(offset))).scalars().all())


async def reschedule_booking(db: AsyncSession, tenant_id: uuid.UUID, actor: User,
                             booking_id: uuid.UUID, body: BookingUpdate) -> Booking:
    customer = await booking_access(db, tenant_id, booking_id, actor, write=True)
    if body.transfer_customer and actor.role != UserRole.ADMIN:
        raise HTTPException(403, "Chỉ Admin được chuyển người phụ trách")
    booking = await get_booking_full(db, tenant_id, booking_id)
    if booking.status not in (BookingStatus.PENDING, BookingStatus.CONFIRMED):
        raise HTTPException(409, "Chỉ được sửa lịch PENDING/CONFIRMED")
    now = datetime.now(timezone.utc)
    start = ensure_aware(body.start_time).astimezone(timezone.utc)
    if start <= now:
        raise HTTPException(422, "start_time phải ở tương lai")
    if actor.role == UserRole.CUSTOMER and booking.start_time - now < timedelta(hours=settings.CANCELLATION_MIN_HOURS):
        raise HTTPException(409, "Chỉ được đổi lịch trước giờ hẹn tối thiểu 2 giờ")
    tenant = await load_tenant(db, tenant_id)
    packages = await _lock_packages(db, tenant_id, sorted({
        item.customer_package_id for item in booking.items if item.customer_package_id}))
    for package in packages.values():
        if package.status != PackageStatus.ACTIVE or (package.expiry_date and package.expiry_date <= start):
            raise HTTPException(422, "Thẻ liệu trình không còn hiệu lực tại giờ hẹn mới")
    # Lock old + potential new technicians in one deterministic order before bookings.
    target_staff = body.staff_id if "staff_id" in body.model_fields_set else booking.staff_id
    candidates = [target_staff] if target_staff else await list_active_staff_ids(db, tenant_id)
    valid = set()
    for sid in sorted(set(candidates + ([booking.staff_id] if booking.staff_id else []))):
        if await _lock_staff_row(db, tenant_id, sid):
            valid.add(sid)
    if target_staff and target_staff not in valid:
        raise HTTPException(404, "Không tìm thấy kỹ thuật viên")
    end = start + timedelta(minutes=booking.total_duration_minutes)
    windows = await get_schedule_windows(db, tenant, candidates, start.astimezone(TZ).date())
    day_start, day_end = local_day_bounds(start.astimezone(TZ).date())
    busy = await fetch_busy(db, tenant, candidates, day_start, day_end, lock=True)
    chosen = next((sid for sid in candidates if sid in valid and _fits(windows[sid], start, end)
                   and not _conflicts([b for b in busy[sid] if b.id != booking_id],
                                      start, end, tenant.buffer_minutes)), None)
    if chosen is None:
        raise HTTPException(409, "Không còn kỹ thuật viên trống trong khung giờ này")
    booking = await get_booking_full(db, tenant_id, booking_id, lock=True)
    before = {"start_time": booking.start_time.isoformat(), "staff_id": str(booking.staff_id)}
    booking.start_time, booking.end_time, booking.staff_id = start, end, chosen
    if body.transfer_customer and customer.assigned_staff_id != chosen:
        previous_owner = customer.assigned_staff_id
        customer.assigned_staff_id = chosen
        audit(db, tenant_id, actor, "CUSTOMER_ASSIGNED", "customer", customer.id,
              {"from_staff_id": str(previous_owner) if previous_owner else None,
               "to_staff_id": str(chosen), "source": "reschedule"})
    audit(db, tenant_id, actor, "BOOKING_RESCHEDULED", "booking", booking.id,
          {"before": before, "after": {"start_time": start.isoformat(), "staff_id": str(chosen)},
           "note_changed": "note" in body.model_fields_set})
    if "note" in body.model_fields_set:
        booking.note = body.note
    await db.commit()
    await set_tenant_context(db, tenant_id)
    return await get_booking_full(db, tenant_id, booking_id)
