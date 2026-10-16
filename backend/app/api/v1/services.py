import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, get_tenant_db, require_roles
from app.api.utils import apply_patch, commit_and_refresh
from app.models.models import BookingItem, CustomerPackage, Service, User, UserRole
from app.schemas.admin import ServiceCreate, ServiceDeleteOut, ServiceOut, ServiceUpdate

router = APIRouter(prefix="/services", tags=["services"])

_admin = require_roles(UserRole.ADMIN)
_admin_staff = require_roles(UserRole.ADMIN, UserRole.STAFF)


async def _get_service(db: AsyncSession, tenant_id: uuid.UUID, service_id: uuid.UUID) -> Service:
    result = await db.execute(select(Service).where(Service.id == service_id, Service.tenant_id == tenant_id))
    service = result.scalar_one_or_none()
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy dịch vụ")
    return service


@router.get("", response_model=List[ServiceOut])
async def list_services(
    is_active: Optional[bool] = None,
    is_package: Optional[bool] = None,
    _user: User = Depends(_admin_staff),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> List[Service]:
    stmt = select(Service).where(Service.tenant_id == tenant_id)
    if is_active is not None:
        stmt = stmt.where(Service.is_active.is_(is_active))
    if is_package is not None:
        stmt = stmt.where(Service.is_package.is_(is_package))
    return list((await db.execute(stmt.order_by(Service.is_package, Service.name))).scalars().all())


@router.post("", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
async def create_service(
    body: ServiceCreate,
    _user: User = Depends(_admin),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> Service:
    service = Service(tenant_id=tenant_id, **body.model_dump())
    db.add(service)
    await commit_and_refresh(db, tenant_id, service)
    return service


@router.patch("/{service_id}", response_model=ServiceOut)
async def update_service(
    service_id: uuid.UUID,
    body: ServiceUpdate,
    _user: User = Depends(_admin),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> Service:
    service = await _get_service(db, tenant_id, service_id)
    apply_patch(service, body, nullable=("description",))
    if not service.is_package:
        service.total_sessions = 1
    await commit_and_refresh(db, tenant_id, service)
    return service


@router.delete("/{service_id}", response_model=ServiceDeleteOut)
async def delete_service(
    service_id: uuid.UUID,
    _user: User = Depends(_admin),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> ServiceDeleteOut:
    """Xóa cứng nếu chưa phát sinh dữ liệu (booking_items / customer_packages), ngược lại soft-delete."""
    service = await _get_service(db, tenant_id, service_id)
    used_in_booking = (
        await db.execute(
            select(BookingItem.id).where(BookingItem.tenant_id == tenant_id, BookingItem.service_id == service_id).limit(1)
        )
    ).first()
    used_in_package = (
        await db.execute(
            select(CustomerPackage.id)
            .where(CustomerPackage.tenant_id == tenant_id, CustomerPackage.service_id == service_id)
            .limit(1)
        )
    ).first()
    if used_in_booking or used_in_package:
        service.is_active = False
        mode = "soft"
    else:
        await db.delete(service)
        mode = "hard"
    await db.commit()
    return ServiceDeleteOut(id=service_id, deleted=True, mode=mode)
