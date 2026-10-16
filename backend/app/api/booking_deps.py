import uuid
from typing import AsyncIterator, Optional

import jwt
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import _UNAUTHORIZED, bearer_scheme
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.core.security import decode_access_token
from app.models.models import Tenant, User
from fastapi import HTTPException, status


class TenantCtx:
    """Session đã gán tenant context + tenant_id (+ user nếu có JWT)."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user: Optional[User]) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.user = user


async def get_optional_tenant_ctx(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    x_tenant_slug: Optional[str] = Header(default=None, alias="X-Tenant-Slug"),
) -> AsyncIterator[TenantCtx]:
    """tenant_id lấy từ JWT nếu có, ngược lại từ header X-Tenant-Slug (khách chưa đăng nhập)."""
    async with AsyncSessionLocal() as session:
        user: Optional[User] = None
        if credentials is not None:
            try:
                payload = decode_access_token(credentials.credentials)
                tenant_id = uuid.UUID(payload["tenant_id"])
                user_id = uuid.UUID(payload["sub"])
            except (jwt.PyJWTError, KeyError, ValueError):
                raise _UNAUTHORIZED
            await set_tenant_context(session, tenant_id)
            user = (
                await session.execute(select(User).where(User.id == user_id, User.tenant_id == tenant_id))
            ).scalar_one_or_none()
            if user is None or not user.is_active:
                raise _UNAUTHORIZED
        elif x_tenant_slug:
            tenant = (
                await session.execute(select(Tenant).where(Tenant.slug == x_tenant_slug.strip().lower()))
            ).scalar_one_or_none()
            if tenant is None or tenant.status != "ACTIVE":
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy Spa")
            tenant_id = tenant.id
            await set_tenant_context(session, tenant_id)
        else:
            raise _UNAUTHORIZED
        yield TenantCtx(session, tenant_id, user)
