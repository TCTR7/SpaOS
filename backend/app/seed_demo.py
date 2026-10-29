"""Seed dữ liệu mẫu (idempotent): `python -m app.seed`."""
import asyncio
import uuid
from datetime import time
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine, set_tenant_context
from app.core.security import hash_password
from app.services.branch_service import provision_account
from app.models.models import (
    CustomerPackage,
    PackageStatus,
    Service,
    StaffSchedule,
    Tenant,
    User,
    UserRole,
)

SLUG = "spa-demo"

ADMIN = ("0900000001", "Chủ Spa Demo", "Admin@123")
STAFF = [
    ("0900000011", "Lan Anh", "Staff@123"),
    ("0900000012", "Minh Thư", "Staff@123"),
    ("0900000013", "Hoàng Yến", "Staff@123"),
]
CUSTOMER = ("0900000101", "Nguyễn Thị Mai", "Customer@123")

# (name, description, duration, price, is_package, total_sessions)
SERVICES = [
    ("Massage body thư giãn", "Massage toàn thân bằng tinh dầu", 60, "350000", False, 1),
    ("Chăm sóc da mặt cơ bản", "Làm sạch, đắp mặt nạ dưỡng ẩm", 60, "300000", False, 1),
    ("Gội đầu dưỡng sinh", "Gội đầu kết hợp massage đầu cổ vai gáy", 45, "150000", False, 1),
    ("Massage chân thảo dược", "Ngâm chân và massage bấm huyệt", 45, "200000", False, 1),
    ("Tẩy tế bào chết toàn thân", "Tẩy da chết và dưỡng ẩm body", 60, "400000", False, 1),
    ("Liệu trình trị mụn 10 buổi", "Gói 10 buổi điều trị mụn chuyên sâu", 60, "3000000", True, 10),
    ("Liệu trình massage body 10 buổi", "Gói 10 buổi massage body", 60, "2800000", True, 10),
]


async def _get_or_create_user(
    db: AsyncSession, tenant_id: uuid.UUID, role: UserRole, phone: str, name: str, password: str
) -> User:
    user = (
        await db.execute(select(User).where(User.tenant_id == tenant_id, User.phone_number == phone))
    ).scalar_one_or_none()
    if user is None:
        user = User(
            tenant_id=tenant_id,
            role=role,
            full_name=name,
            phone_number=phone,
            password_hash=hash_password(password),
        )
        db.add(user)
        await db.flush()
    if role in (UserRole.ADMIN, UserRole.STAFF):
        await provision_account(db, user, owner=role == UserRole.ADMIN)
    return user


async def seed(db: AsyncSession) -> None:
    tenant: Optional[Tenant] = (await db.execute(select(Tenant).where(Tenant.slug == SLUG))).scalar_one_or_none()
    if tenant is None:
        from app.services.spa_service import new_spa
        spa = await new_spa(db, "Spa Demo", slug=SLUG)
        tenant = Tenant(
            spa_id=spa.id,
            slug=SLUG,
            name="Spa Demo",
            theme_color="#e91e63",
            open_time=time(9, 0),
            close_time=time(20, 0),
            buffer_minutes=10,
        )
        db.add(tenant)
        await db.flush()
    tenant_id = tenant.id
    # Mọi bảng còn lại có RLS -> gán tenant context cho transaction này
    await set_tenant_context(db, tenant_id)

    await _get_or_create_user(db, tenant_id, UserRole.ADMIN, *ADMIN)

    staff_users = [await _get_or_create_user(db, tenant_id, UserRole.STAFF, *s) for s in STAFF]
    for staff in staff_users:
        from app.models.models import StaffAssignment
        from app.services.assignment_service import staff_account
        from datetime import date
        aid = await staff_account(db, tenant_id, staff.id)
        if not (await db.execute(select(StaffAssignment.id).where(StaffAssignment.account_id == aid).limit(1))).first():
            db.add_all([StaffAssignment(spa_id=tenant.spa_id, account_id=aid, tenant_id=tenant_id,
                weekday=dow, effective_from=date.today(), start_time=time(9), end_time=time(20)) for dow in range(7)])
        has_schedule = (
            await db.execute(
                select(StaffSchedule.id).where(StaffSchedule.tenant_id == tenant_id, StaffSchedule.staff_id == staff.id).limit(1)
            )
        ).first()
        if not has_schedule:
            # Thứ 2 -> Chủ nhật (0=CN .. 6=Thứ 7)
            for dow in range(7):
                db.add(
                    StaffSchedule(
                        tenant_id=tenant_id,
                        staff_id=staff.id,
                        day_of_week=dow,
                        start_time=time(9, 0),
                        end_time=time(20, 0),
                        is_day_off=False,
                    )
                )

    services = {}
    for name, desc, duration, price, is_package, sessions in SERVICES:
        svc = (
            await db.execute(select(Service).where(Service.tenant_id == tenant_id, Service.name == name))
        ).scalar_one_or_none()
        if svc is None:
            svc = Service(
                tenant_id=tenant_id,
                name=name,
                description=desc,
                duration_minutes=duration,
                price=Decimal(price),
                is_package=is_package,
                total_sessions=sessions,
            )
            db.add(svc)
            await db.flush()
        services[name] = svc

    customer = await _get_or_create_user(db, tenant_id, UserRole.CUSTOMER, *CUSTOMER)
    pkg_service = services["Liệu trình trị mụn 10 buổi"]
    existing_pkg = (
        await db.execute(
            select(CustomerPackage.id).where(
                CustomerPackage.tenant_id == tenant_id,
                CustomerPackage.customer_id == customer.id,
                CustomerPackage.service_id == pkg_service.id,
            )
        )
    ).first()
    if not existing_pkg:
        db.add(
            CustomerPackage(
                tenant_id=tenant_id,
                customer_id=customer.id,
                service_id=pkg_service.id,
                package_name=pkg_service.name,
                total_sessions=pkg_service.total_sessions,
                used_sessions=0,
                status=PackageStatus.ACTIVE,
            )
        )

    await db.commit()


async def main() -> None:
    if settings.ENVIRONMENT == "production":
        raise RuntimeError("Không cho phép seed dữ liệu demo trên production.")
    async with AsyncSessionLocal() as db:
        await seed(db)
    await engine.dispose()
    print(f"Seed OK. Tenant slug: {SLUG}")
    print(f"  ADMIN    {ADMIN[0]} / {ADMIN[2]}")
    for phone, name, pw in STAFF:
        print(f"  STAFF    {phone} / {pw}  ({name})")
    print(f"  CUSTOMER {CUSTOMER[0]} / {CUSTOMER[2]}")


if __name__ == "__main__":
    asyncio.run(main())
