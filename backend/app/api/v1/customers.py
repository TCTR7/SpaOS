import secrets
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, get_tenant_db, require_roles
from app.api.utils import apply_patch, commit_and_refresh
from app.core.security import hash_password
from app.services.audit_service import audit
from app.services.customer_access import customer_access, customer_scope
from app.services.booking_service import get_active_staff
from app.models.models import Booking, BookingItem, BookingStatus, CustomerPackage, PackageStatus, Service, User, UserRole
from app.schemas.admin import (
    CustomerCreate,
    CustomerAssignment,
    CustomerPackageCreate,
    CustomerPackageOut,
    MyCustomerPackageOut,
    CustomerUpdate,
    UserDetailOut,
)

customers_router = APIRouter(prefix="/customers", tags=["customers"])
packages_router = APIRouter(prefix="/customer-packages", tags=["customer-packages"])

_admin_staff = require_roles(UserRole.ADMIN, UserRole.STAFF)


async def _get_customer(db: AsyncSession, tenant_id: uuid.UUID, customer_id: uuid.UUID) -> User:
    result = await db.execute(
        select(User).where(User.id == customer_id, User.tenant_id == tenant_id, User.role == UserRole.CUSTOMER)
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy khách hàng")
    return customer


@customers_router.get("", response_model=List[UserDetailOut])
async def list_customers(
    response: Response,
    q: Optional[str] = Query(default=None, description="Tìm theo SĐT hoặc họ tên"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user: User = Depends(_admin_staff),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> List[User]:
    stmt = select(User).where(User.tenant_id == tenant_id, User.role == UserRole.CUSTOMER)
    if _user.role == UserRole.STAFF:
        stmt = stmt.where(User.id.in_(customer_scope(tenant_id, _user)))
    if q and q.strip():
        term = q.strip().lower()
        stmt = stmt.where(
            or_(
                func.lower(User.full_name).contains(term, autoescape=True),
                User.phone_number.contains(term, autoescape=True),
            )
        )
    stmt = stmt.order_by(User.full_name, User.id).limit(limit + 1).offset(offset)
    rows = list((await db.execute(stmt)).scalars().all())
    response.headers["X-Has-More"] = str(len(rows) > limit).lower()
    response.headers["X-Next-Offset"] = str(offset + limit) if len(rows) > limit else ""
    return rows[:limit]


@customers_router.post("", response_model=UserDetailOut, status_code=status.HTTP_201_CREATED)
async def create_customer(
    body: CustomerCreate,
    _user: User = Depends(_admin_staff),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> User:
    """Tạo nhanh khách tại quầy. Không truyền password -> sinh mật khẩu ngẫu nhiên (khách đặt lại sau)."""
    customer = User(
        tenant_id=tenant_id,
        role=UserRole.CUSTOMER,
        full_name=body.full_name,
        phone_number=body.phone_number,
        password_hash=hash_password(body.password or secrets.token_urlsafe(16)),
        notes=body.notes,
        assigned_staff_id=_user.id if _user.role == UserRole.STAFF else None,
    )
    db.add(customer)
    try:
        await db.flush()
        audit(db, tenant_id, _user, "CUSTOMER_CREATED", "customer", customer.id)
        await commit_and_refresh(db, tenant_id, customer)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Số điện thoại đã tồn tại trong Spa")
    return customer


@customers_router.patch("/{customer_id}", response_model=UserDetailOut)
async def update_customer(
    customer_id: uuid.UUID,
    body: CustomerUpdate,
    _user: User = Depends(_admin_staff),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> User:
    customer = await customer_access(db, tenant_id, customer_id, _user, write=True)
    apply_patch(customer, body, nullable=("notes",))
    audit(db, tenant_id, _user, "CUSTOMER_UPDATED", "customer", customer.id,
          {"fields": sorted(body.model_fields_set)})
    await commit_and_refresh(db, tenant_id, customer)
    return customer


@customers_router.get("/{customer_id}/packages", response_model=List[CustomerPackageOut])
async def list_packages_of_customer(
    customer_id: uuid.UUID,
    _user: User = Depends(_admin_staff),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> List[CustomerPackage]:
    await customer_access(db, tenant_id, customer_id, _user)
    stmt = (
        select(CustomerPackage)
        .where(CustomerPackage.tenant_id == tenant_id, CustomerPackage.customer_id == customer_id)
        .order_by(CustomerPackage.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


@packages_router.get("/me", response_model=List[MyCustomerPackageOut])
async def list_my_packages(
    user: User = Depends(require_roles(UserRole.CUSTOMER)),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> List[MyCustomerPackageOut]:
    """Customer and tenant are derived exclusively from the JWT."""
    reserved = (
        select(BookingItem.customer_package_id.label("package_id"), func.count(BookingItem.id).label("sessions"))
        .join(Booking, Booking.id == BookingItem.booking_id)
        .where(
            BookingItem.tenant_id == tenant_id,
            Booking.tenant_id == tenant_id,
            Booking.customer_id == user.id,
            Booking.status.in_((BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS)),
            BookingItem.customer_package_id.is_not(None),
        )
        .group_by(BookingItem.customer_package_id)
        .subquery()
    )
    rows = (await db.execute(
        select(CustomerPackage, func.coalesce(reserved.c.sessions, 0))
        .outerjoin(reserved, reserved.c.package_id == CustomerPackage.id)
        .where(CustomerPackage.tenant_id == tenant_id, CustomerPackage.customer_id == user.id)
        .order_by(CustomerPackage.created_at.desc(), CustomerPackage.id)
    )).all()
    now = datetime.now(timezone.utc)
    result = []
    for package, held in rows:
        active = package.status == PackageStatus.ACTIVE and (
            package.expiry_date is None or package.expiry_date > now
        )
        result.append(MyCustomerPackageOut(
            **CustomerPackageOut.model_validate(package).model_dump(exclude={"remaining_sessions"}),
            reserved_sessions=held,
            available_sessions=max(0, package.total_sessions - package.used_sessions - held) if active else 0,
        ))
    return result


@packages_router.get("", response_model=List[CustomerPackageOut])
async def list_customer_packages(
    customer_id: Optional[uuid.UUID] = None,
    package_status: Optional[PackageStatus] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user: User = Depends(_admin_staff),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> List[CustomerPackage]:
    stmt = select(CustomerPackage).where(CustomerPackage.tenant_id == tenant_id)
    if _user.role == UserRole.STAFF:
        stmt = stmt.where(CustomerPackage.customer_id.in_(customer_scope(tenant_id, _user)))
    if customer_id is not None:
        stmt = stmt.where(CustomerPackage.customer_id == customer_id)
    if package_status is not None:
        stmt = stmt.where(CustomerPackage.status == package_status)
    stmt = stmt.order_by(CustomerPackage.created_at.desc()).limit(limit).offset(offset)
    return list((await db.execute(stmt)).scalars().all())


@packages_router.post("", response_model=CustomerPackageOut, status_code=status.HTTP_201_CREATED)
async def create_customer_package(
    body: CustomerPackageCreate,
    _user: User = Depends(_admin_staff),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> CustomerPackage:
    """Cấp thẻ liệu trình. `package_name`/`total_sessions` mặc định lấy từ service nếu không truyền."""
    await customer_access(db, tenant_id, body.customer_id, _user, write=True)
    service = (
        await db.execute(select(Service).where(Service.id == body.service_id, Service.tenant_id == tenant_id))
    ).scalar_one_or_none()
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy dịch vụ")
    if not service.is_package or not service.is_active:
        raise HTTPException(
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            detail="Dịch vụ phải là gói liệu trình đang hoạt động",
        )
    if body.expiry_date is not None and body.expiry_date <= datetime.now(body.expiry_date.tzinfo):
        raise HTTPException(
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            detail="expiry_date phải ở tương lai",
        )

    package = CustomerPackage(
        tenant_id=tenant_id,
        customer_id=body.customer_id,
        service_id=service.id,
        package_name=body.package_name or service.name,
        purchase_price=service.price,
        total_sessions=body.total_sessions or service.total_sessions,
        used_sessions=0,
        expiry_date=body.expiry_date,
        status=PackageStatus.ACTIVE,
    )
    db.add(package)
    await db.flush()
    audit(db, tenant_id, _user, "PACKAGE_ISSUED", "package", package.id,
          {"customer_id": str(package.customer_id), "purchase_price": str(package.purchase_price),
           "total_sessions": package.total_sessions})
    await commit_and_refresh(db, tenant_id, package)
    return package


@customers_router.patch("/{customer_id}/assignment", response_model=UserDetailOut)
async def assign_customer(customer_id: uuid.UUID, body: CustomerAssignment,
                          actor: User = Depends(require_roles(UserRole.ADMIN)),
                          tenant_id: uuid.UUID = Depends(get_current_tenant_id),
                          db: AsyncSession = Depends(get_tenant_db)):
    customer = await customer_access(db, tenant_id, customer_id, actor, write=True)
    if body.assigned_staff_id is not None:
        await get_active_staff(db, tenant_id, body.assigned_staff_id)
    previous_owner = customer.assigned_staff_id
    customer.assigned_staff_id = body.assigned_staff_id
    if previous_owner != body.assigned_staff_id:
        audit(db, tenant_id, actor, "CUSTOMER_ASSIGNED", "customer", customer.id,
              {"from_staff_id": str(previous_owner) if previous_owner else None,
               "to_staff_id": str(body.assigned_staff_id) if body.assigned_staff_id else None})
    await commit_and_refresh(db, tenant_id, customer)
    return customer
