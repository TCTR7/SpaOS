from datetime import datetime, timezone
from sqlalchemy import select, func
from app.models.models import Booking, BookingItem, BookingStatus, CustomerPackage, PackageStatus
from app.schemas.admin import CustomerPackageOut, MyCustomerPackageOut

async def package_views(db, tenant_id, customer_id):
    reserved = (select(BookingItem.customer_package_id.label("package_id"), func.count(BookingItem.id).label("sessions"))
      .join(Booking, (Booking.id == BookingItem.booking_id) & (Booking.tenant_id == tenant_id))
      .where(BookingItem.tenant_id == tenant_id, Booking.customer_id == customer_id,
          Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS]),
          BookingItem.customer_package_id.is_not(None)).group_by(BookingItem.customer_package_id).subquery())
    rows = (await db.execute(select(CustomerPackage, func.coalesce(reserved.c.sessions, 0))
      .outerjoin(reserved, reserved.c.package_id == CustomerPackage.id)
      .where(CustomerPackage.tenant_id == tenant_id, CustomerPackage.customer_id == customer_id)
      .order_by(CustomerPackage.created_at.desc(), CustomerPackage.id))).all()
    now = datetime.now(timezone.utc)
    return [MyCustomerPackageOut(**CustomerPackageOut.model_validate(package).model_dump(exclude={"remaining_sessions"}),
       reserved_sessions=held, available_sessions=max(0, package.total_sessions-package.used_sessions-held)
       if package.status == PackageStatus.ACTIVE and (package.expiry_date is None or package.expiry_date > now) else 0)
       for package, held in rows]
