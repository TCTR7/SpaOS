from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant, get_current_user, get_public_tenant
from app.core.config import settings
from app.core.database import get_db, set_tenant_context
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import Tenant, User, UserRole
from app.schemas.auth import (
    CustomerRegisterRequest,
    LoginRequest,
    MeResponse,
    TenantOut,
    TenantRegisterRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, user.tenant_id, user.role.value),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/register-tenant", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_tenant(body: TenantRegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Tạo Spa mới + tài khoản ADMIN đầu tiên."""
    try:
        tenant = Tenant(slug=body.tenant_slug, name=body.tenant_name)
        db.add(tenant)
        await db.flush()
        await set_tenant_context(db, tenant.id)
        user = User(
            tenant_id=tenant.id,
            role=UserRole.ADMIN,
            full_name=body.admin_full_name,
            phone_number=body.phone_number,
            password_hash=hash_password(body.password),
        )
        db.add(user)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug Spa đã tồn tại")
    return _token_response(user)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_customer(
    body: CustomerRegisterRequest,
    tenant: Tenant = Depends(get_public_tenant),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Khách hàng đăng ký trong Spa xác định bởi header `X-Tenant-Slug`. Role luôn là CUSTOMER."""
    await set_tenant_context(db, tenant.id)
    user = User(
        tenant_id=tenant.id,
        role=UserRole.CUSTOMER,
        full_name=body.full_name,
        phone_number=body.phone_number,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Số điện thoại đã đăng ký tại Spa này")
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    tenant: Tenant = Depends(get_public_tenant),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Đăng nhập (Admin/Staff/Customer) trong Spa xác định bởi header `X-Tenant-Slug`."""
    await set_tenant_context(db, tenant.id)
    result = await db.execute(
        select(User).where(User.tenant_id == tenant.id, User.phone_number == body.phone_number)
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sai số điện thoại hoặc mật khẩu")
    return _token_response(user)


@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant)) -> MeResponse:
    return MeResponse(user=UserOut.model_validate(user), tenant=TenantOut.model_validate(tenant))
