from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant, get_tenant_db, require_roles
from app.api.utils import apply_patch, commit_and_refresh
from app.core.database import get_db, set_tenant_context
from app.models.models import Service, Tenant, User, UserRole
from app.schemas.admin import PublicStaffOut, PublicTenantOut, ServiceOut, TenantDetailOut, TenantUpdate

public_router = APIRouter(prefix="/public", tags=["public"])
tenants_router = APIRouter(prefix="/tenants", tags=["tenants"])


@public_router.get("/tenants/{slug}", response_model=PublicTenantOut)
async def get_public_tenant_info(slug: str, day: str | None = None, db: AsyncSession = Depends(get_db)) -> PublicTenantOut:
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
    from app.services.spa_service import tenant_spa
    spa = await tenant_spa(db, tenant.id)
    staff = (await db.execute(select(User.id, User.full_name).where(
        User.tenant_id == tenant.id, User.role == UserRole.STAFF, User.is_active.is_(True)
    ).order_by(User.full_name, User.id))).all()
    if day:
        from datetime import date
        from app.services.assignment_service import effective_windows
        try:
            selected_day = date.fromisoformat(day)
        except ValueError:
            raise HTTPException(422, "Ngày không hợp lệ")
        windows = await effective_windows(db, tenant, [row.id for row in staff], selected_day)
        staff = [row for row in staff if windows[row.id]]
    return PublicTenantOut(
        spa_slug=spa.slug,
        id=tenant.id,
        slug=tenant.slug,
        name=tenant.name,
        address=tenant.address, contact_phone=tenant.contact_phone,
        logo_url=tenant.logo_url or spa.logo_url,
        theme_color=spa.theme_color,
        open_time=tenant.open_time,
        close_time=tenant.close_time,
        buffer_minutes=tenant.buffer_minutes,
        services=[ServiceOut.model_validate(s) for s in services],
        staff=[PublicStaffOut(id=row.id, full_name=row.full_name) for row in staff],
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
    data = body.model_dump(exclude_unset=True)
    logo_data = data.pop("logo_data", None)
    if logo_data is not None:
        import base64, binascii, uuid
        from app.api.v1.experience import validate_image_payload
        from app.models.models import TenantLogo
        from sqlalchemy import text
        try:
            image = base64.b64decode(logo_data, validate=True)
        except (ValueError, binascii.Error):
            raise HTTPException(422, "Dữ liệu ảnh không hợp lệ")
        validate_image_payload(image)
        await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": f"logo:{tenant.id}"})
        logo = (await db.execute(select(TenantLogo).where(TenantLogo.tenant_id == tenant.id))).scalar_one_or_none()
        if logo: logo.data = image
        else: db.add(TenantLogo(tenant_id=tenant.id, data=image))
        data["logo_url"] = f"/api/v1/public/tenants/{tenant.slug}/logo?v={uuid.uuid4().hex}"
    apply_patch(tenant, TenantUpdate(**data), nullable=("logo_url", "theme_color", "address", "contact_phone"))
    if tenant.close_time <= tenant.open_time:
        raise HTTPException(
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            detail="Giờ đóng cửa phải sau giờ mở cửa",
        )
    await commit_and_refresh(db, tenant.id, tenant)
    return tenant
