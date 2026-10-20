import uuid
import re
from typing import AsyncIterator

import pytest_asyncio
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url

from app.core.database import engine
from app.core.config import settings
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def require_disposable_test_database():
    """Fail before any fixture can write to a deployment database."""
    database = make_url(settings.DATABASE_URL).database or ""
    if settings.ENVIRONMENT != "test" or not re.fullmatch(r"spaos_qa_[a-f0-9]{32}", database):
        pytest.exit("Refusing application database: use python -m scripts.test_isolated", returncode=2)


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
