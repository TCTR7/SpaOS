from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant, get_current_user, get_public_tenant, get_tenant_db, get_token_data, TokenData
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

from app.services.branch_service import provision_account, authenticate_management, branch_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, user.tenant_id, user.role.value, user.auth_version),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/register-tenant", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_tenant(body: TenantRegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Tạo Spa mới + tài khoản ADMIN đầu tiên."""
    if settings.ENVIRONMENT == "production":
        raise HTTPException(403, "Đăng ký hệ thống mới đã được tắt. Liên hệ đơn vị triển khai.")
    try:
        from app.services.spa_service import new_spa
        spa = await new_spa(db, body.tenant_name, slug=body.tenant_slug)
        tenant = Tenant(slug=body.tenant_slug, name=body.tenant_name, spa_id=spa.id)
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
        await db.flush()
        await provision_account(db, user, owner=True)
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
async def login(body: LoginRequest, x_tenant_slug: str | None = Header(None, alias="X-Tenant-Slug"),
                db: AsyncSession = Depends(get_db)) -> TokenResponse:
    if x_tenant_slug is None:
        user = await authenticate_management(db, body.phone_number, body.password)
        from app.services.spa_service import tenant_spa
        spa = await tenant_spa(db, user.tenant_id)
        result = _token_response(user)
        result.spa_slug = spa.slug
        return result
    tenant = (await db.execute(select(Tenant).where(Tenant.slug == x_tenant_slug.strip().lower(),
                                                   Tenant.status == "ACTIVE"))).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(404, "Không tìm thấy Spa")
    await set_tenant_context(db, tenant.id)
    user = (await db.execute(select(User).where(User.tenant_id == tenant.id,
                                      User.phone_number == body.phone_number))).scalar_one_or_none()
    if user is None or not user.is_active or not await branch_password(db, user, body.password):
        raise HTTPException(401, "Sai số điện thoại hoặc mật khẩu")
    return _token_response(user)


@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant), db: AsyncSession = Depends(get_tenant_db)) -> MeResponse:
    from app.services.spa_service import tenant_spa, brand_view
    spa = await tenant_spa(db, tenant.id)
    return MeResponse(user=UserOut.model_validate(user), tenant=TenantOut.model_validate(tenant), spa=brand_view(spa))


@router.post("/resolve", response_model=TokenResponse)
async def resolve_session(token: TokenData = Depends(get_token_data), db: AsyncSession = Depends(get_tenant_db)) -> TokenResponse:
    """Resolve a revoked branch session without accepting expired or reset credentials.

    The old branch grants no business access. Its retained user record only proves
    the signed identity and credential version before checking all remaining rights.
    """
    from app.services.branch_service import membership_for, account_context, branches_for, preferred_branch
    from app.services.spa_service import tenant_spa
    from app.models.models import LoginAccount
    user = (await db.execute(select(User).where(User.tenant_id == token.tenant_id, User.id == token.user_id))).scalar_one_or_none()
    if not user or user.role not in (UserRole.ADMIN, UserRole.STAFF) or user.auth_version != token.auth_version:
        raise HTTPException(401, "Phiên đăng nhập không còn hiệu lực")
    link = await membership_for(db, user)
    if not link:
        raise HTTPException(401, "Không có danh tính vận hành hợp lệ")
    await account_context(db, link.account_id)
    account = (await db.execute(select(LoginAccount).where(LoginAccount.id == link.account_id, LoginAccount.is_active.is_(True)))).scalar_one_or_none()
    spa = await tenant_spa(db, token.tenant_id)
    if not account or account.spa_id != spa.id:
        raise HTTPException(401, "Tài khoản không còn hiệu lực")
    rows = await branches_for(db, account.id)
    if not rows:
        raise HTTPException(401, "Tài khoản không còn chi nhánh được cấp")
    target = await preferred_branch(db, account, rows)
    result = _token_response(target)
    result.spa_slug = spa.slug
    return result
