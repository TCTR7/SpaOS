from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant, get_tenant_db, require_roles
from app.api.utils import apply_patch, commit_and_refresh
from app.core.database import get_db, set_tenant_context
from app.models.models import Service, Tenant, User, UserRole
from app.schemas.admin import PublicTenantOut, ServiceOut, TenantDetailOut, TenantUpdate

public_router = APIRouter(prefix="/public", tags=["public"])
tenants_router = APIRouter(prefix="/tenants", tags=["tenants"])


@public_router.get("/tenants/{slug}", response_model=PublicTenantOut)
async def get_public_tenant_info(slug: str, db: AsyncSession = Depends(get_db)) -> PublicTenantOut:
    result = await db.execute(select(Tenant).where(Tenant.slug == slug.strip().lower()))
    tenant = result.scalar_one_or_none()
    if tenant is None or tenant.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy Spa")

    # services có RLS -> phải gán tenant context (suy ra từ slug) trước khi query
    await set_tenant_context(db, tenant.id)
    services = (
        await db.execute(
            select(Service)
            .where(Service.tenant_id == tenant.id, Service.is_active.is_(True))
            .order_by(Service.is_package, Service.name)
        )
    ).scalars().all()
    from app.services.branding_service import get_branding
    branding = await get_branding(db)
    return PublicTenantOut(
        id=tenant.id,
        slug=tenant.slug,
        name=tenant.name,
        logo_url=tenant.logo_url,
        theme_color=branding.theme_color if branding.configured else tenant.theme_color,
        open_time=tenant.open_time,
        close_time=tenant.close_time,
        buffer_minutes=tenant.buffer_minutes,
        services=[ServiceOut.model_validate(s) for s in services],
    )


@tenants_router.get("/me", response_model=TenantDetailOut)
async def get_my_tenant(
    _admin: User = Depends(require_roles(UserRole.ADMIN)), tenant: Tenant = Depends(get_current_tenant)
) -> Tenant:
    return tenant


@tenants_router.patch("/me", response_model=TenantDetailOut)
async def update_my_tenant(
    body: TenantUpdate,
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_tenant_db),
) -> Tenant:
    apply_patch(tenant, body, nullable=("logo_url", "theme_color"))
    if tenant.close_time <= tenant.open_time:
        raise HTTPException(
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            detail="close_time phải lớn hơn open_time",
        )
    await commit_and_refresh(db, tenant.id, tenant)
    return tenant
