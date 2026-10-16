import uuid
from datetime import date
from decimal import Decimal
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, get_tenant_db, require_roles
from app.models.models import Booking, BookingItem, BookingStatus, User, UserRole
from app.schemas.sprint4 import StaffPerformanceItem, StaffPerformanceOut, StaffPerformanceTotals
from app.services.booking_service import HTTP_422, TZ, local_day_bounds

router = APIRouter(prefix="/reports", tags=["reports"])

MAX_RANGE_DAYS = 366


@router.get("/staff-performance", response_model=StaffPerformanceOut)
async def staff_performance(
    start_date: date,
    end_date: date,
    staff_id: Optional[uuid.UUID] = None,
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> StaffPerformanceOut:
    """Hiệu suất/hoa hồng KTV: booking COMPLETED có `start_time` trong [start_date, end_date] (giờ Asia/Ho_Chi_Minh)."""
    if end_date < start_date:
        raise HTTPException(status_code=HTTP_422, detail="end_date phải >= start_date")
    if (end_date - start_date).days >= MAX_RANGE_DAYS:
        raise HTTPException(status_code=HTTP_422, detail=f"Khoảng thời gian tối đa {MAX_RANGE_DAYS} ngày")

    # Biên theo giờ địa phương -> so sánh với TIMESTAMPTZ (UTC) trong DB
    range_start = local_day_bounds(start_date)[0]
    range_end = local_day_bounds(end_date)[1]  # loại trừ (đầu ngày hôm sau)

    staff_stmt = select(User.id, User.full_name, User.is_active).where(
        User.tenant_id == tenant_id, User.role == UserRole.STAFF
    )
    if staff_id is not None:
        staff_stmt = staff_stmt.where(User.id == staff_id)
    staff_rows = (await db.execute(staff_stmt.order_by(User.full_name, User.id))).all()
    if staff_id is not None and not staff_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")

    # 1 câu aggregate duy nhất (GROUP BY staff) -> không N+1
    item_count = func.count(BookingItem.id)
    stmt = (
        select(
            Booking.staff_id,
            func.count(func.distinct(Booking.id)),
            item_count,
            item_count.filter(BookingItem.customer_package_id.is_not(None)),
            func.coalesce(func.sum(BookingItem.price), 0),
        )
        .select_from(Booking)
        .join(BookingItem, BookingItem.booking_id == Booking.id)
        .where(
            Booking.tenant_id == tenant_id,
            BookingItem.tenant_id == tenant_id,
            Booking.status == BookingStatus.COMPLETED,
            Booking.staff_id.is_not(None),
            Booking.start_time >= range_start,
            Booking.start_time < range_end,
        )
        .group_by(Booking.staff_id)
    )
    if staff_id is not None:
        stmt = stmt.where(Booking.staff_id == staff_id)
    stats: Dict[uuid.UUID, tuple] = {row[0]: row[1:] for row in (await db.execute(stmt)).all()}

    items = []
    tot_b = tot_s = tot_pkg = 0
    tot_rev = Decimal("0")
    for sid, name, active in staff_rows:
        bookings_n, services_n, pkg_n, revenue = stats.get(sid, (0, 0, 0, Decimal("0")))
        items.append(
            StaffPerformanceItem(
                staff_id=sid,
                full_name=name,
                is_active=active,
                completed_bookings_count=bookings_n,
                completed_services_count=services_n,
                single_services_count=services_n - pkg_n,
                package_sessions_count=pkg_n,
                total_revenue=revenue,
            )
        )
        tot_b += bookings_n
        tot_s += services_n
        tot_pkg += pkg_n
        tot_rev += revenue

    return StaffPerformanceOut(
        start_date=start_date,
        end_date=end_date,
        timezone=str(TZ),
        staff=items,
        totals=StaffPerformanceTotals(
            completed_bookings_count=tot_b,
            completed_services_count=tot_s,
            single_services_count=tot_s - tot_pkg,
            package_sessions_count=tot_pkg,
            total_revenue=tot_rev,
        ),
    )
