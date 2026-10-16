import uuid
from typing import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import engine
from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    # Mỗi test chạy event loop riêng -> bỏ pool connection cũ
    await engine.dispose()


def unique_slug(prefix: str = "spa") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def unique_phone() -> str:
    return "09" + str(uuid.uuid4().int)[:8]
