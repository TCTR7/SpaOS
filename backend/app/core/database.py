import uuid
from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def set_tenant_context(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Gán biến session `app.current_tenant_id` (is_local=true -> chỉ trong transaction hiện tại).

    PostgreSQL RLS đọc biến này. Phải gọi lại sau mỗi commit/rollback.
    """
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
        {"tid": str(tenant_id)},
    )


async def get_db() -> AsyncIterator[AsyncSession]:
    """Session KHÔNG gắn tenant (chỉ dùng cho tra cứu tenant theo slug / đăng ký tenant)."""
    async with AsyncSessionLocal() as session:
        yield session
