import uuid
from typing import AsyncIterator, Callable

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db, set_tenant_context
from app.core.security import decode_access_token
from app.models.models import Tenant, User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Token không hợp lệ hoặc đã hết hạn",
    headers={"WWW-Authenticate": "Bearer"},
)


class TokenData:
    def __init__(self, user_id: uuid.UUID, tenant_id: uuid.UUID, role: str) -> None:
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role


def get_token_data(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> TokenData:
    if credentials is None:
        raise _UNAUTHORIZED
    try:
        payload = decode_access_token(credentials.credentials)
        return TokenData(
            user_id=uuid.UUID(payload["sub"]),
            tenant_id=uuid.UUID(payload["tenant_id"]),
            role=payload["role"],
        )
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _UNAUTHORIZED


async def get_tenant_db(token: TokenData = Depends(get_token_data)) -> AsyncIterator[AsyncSession]:
    """Session đã gán `app.current_tenant_id` từ JWT (kích hoạt RLS).

    tenant_id CHỈ lấy từ JWT, không bao giờ từ Client Body.
    """
    async with AsyncSessionLocal() as session:
        await set_tenant_context(session, token.tenant_id)
        yield session


async def get_current_tenant_id(token: TokenData = Depends(get_token_data)) -> uuid.UUID:
    return token.tenant_id


async def get_current_user(
    token: TokenData = Depends(get_token_data),
    db: AsyncSession = Depends(get_tenant_db),
) -> User:
    result = await db.execute(
        select(User).where(User.id == token.user_id, User.tenant_id == token.tenant_id)
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise _UNAUTHORIZED
    return user


async def get_current_tenant(
    token: TokenData = Depends(get_token_data),
    db: AsyncSession = Depends(get_tenant_db),
    _user: User = Depends(get_current_user),
) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.id == token.tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None or tenant.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Spa không tồn tại hoặc đã bị khóa")
    return tenant


def require_roles(*roles: UserRole) -> Callable[..., User]:
    async def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không đủ quyền truy cập")
        return user

    return _checker


async def get_public_tenant(
    x_tenant_slug: str = Header(..., alias="X-Tenant-Slug"),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Tenant cho khách chưa đăng nhập (đăng ký/đăng nhập khách) qua header X-Tenant-Slug."""
    result = await db.execute(select(Tenant).where(Tenant.slug == x_tenant_slug.strip().lower()))
    tenant = result.scalar_one_or_none()
    if tenant is None or tenant.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy Spa")
    return tenant
