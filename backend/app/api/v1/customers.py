import secrets
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, get_tenant_db, require_roles
from app.api.utils import apply_patch, commit_and_refresh
from app.core.security import hash_password
from app.models.models import CustomerPackage, PackageStatus, Service, User, UserRole
from app.schemas.admin import (
    CustomerCreate,
    CustomerPackageCreate,
    CustomerPackageOut,
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
    q: Optional[str] = Query(default=None, description="Tìm theo SĐT hoặc họ tên"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user: User = Depends(_admin_staff),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> List[User]:
    stmt = select(User).where(User.tenant_id == tenant_id, User.role == UserRole.CUSTOMER)
    if q and q.strip():
        term = q.strip().lower()
        stmt = stmt.where(
            or_(
                func.lower(User.full_name).contains(term, autoescape=True),
                User.phone_number.contains(term, autoescape=True),
            )
        )
    stmt = stmt.order_by(User.full_name).limit(limit).offset(offset)
    return list((await db.execute(stmt)).scalars().all())


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
    )
    db.add(customer)
    try:
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
    customer = await _get_customer(db, tenant_id, customer_id)
    apply_patch(customer, body, nullable=("notes",))
    await commit_and_refresh(db, tenant_id, customer)
    return customer


@customers_router.get("/{customer_id}/packages", response_model=List[CustomerPackageOut])
async def list_packages_of_customer(
    customer_id: uuid.UUID,
    _user: User = Depends(_admin_staff),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> List[CustomerPackage]:
    await _get_customer(db, tenant_id, customer_id)
    stmt = (
        select(CustomerPackage)
        .where(CustomerPackage.tenant_id == tenant_id, CustomerPackage.customer_id == customer_id)
        .order_by(CustomerPackage.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


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
    await _get_customer(db, tenant_id, body.customer_id)
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
        total_sessions=body.total_sessions or service.total_sessions,
        used_sessions=0,
        expiry_date=body.expiry_date,
        status=PackageStatus.ACTIVE,
    )
    db.add(package)
    await commit_and_refresh(db, tenant_id, package)
    return package
