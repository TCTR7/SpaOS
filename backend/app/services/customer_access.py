"""Persistent ownership, independent of booking technician/history."""
from fastapi import HTTPException
from sqlalchemy import select, text
from app.models.models import User, UserRole, Booking


def customer_scope(tenant_id, actor):
    return select(User.id).where(User.tenant_id == tenant_id, User.role == UserRole.CUSTOMER,
                                 User.assigned_staff_id == actor.id)


async def customer_access(db, tenant_id, customer_id, actor, *, write=False):
    # Serialize writes and ownership transfers before package/staff/booking row locks.
    if write:
        await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                         {"key": f"customer:{tenant_id}:{customer_id}"})
    customer = (await db.execute(select(User).where(
        User.tenant_id == tenant_id, User.id == customer_id, User.role == UserRole.CUSTOMER
    ).execution_options(populate_existing=True))).scalar_one_or_none()
    if customer is None or (actor.role == UserRole.STAFF and customer.assigned_staff_id != actor.id) or (
            actor.role == UserRole.CUSTOMER and customer.id != actor.id):
        raise HTTPException(404, "Không tìm thấy khách hàng")
    return customer


async def booking_access(db, tenant_id, booking_id, actor, *, write=False):
    customer_id = (await db.execute(select(Booking.customer_id).where(
        Booking.tenant_id == tenant_id, Booking.id == booking_id))).scalar_one_or_none()
    if customer_id is None:
        raise HTTPException(404, "Không tìm thấy lịch hẹn")
    return await customer_access(db, tenant_id, customer_id, actor, write=write)
