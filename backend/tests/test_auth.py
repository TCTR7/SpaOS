import pytest
from sqlalchemy import text

from app.core.database import AsyncSessionLocal, set_tenant_context
from tests.conftest import unique_phone, unique_slug


async def _register_tenant(client, slug: str, phone: str, password: str = "secret123") -> dict:
    r = await client.post(
        "/api/v1/auth/register-tenant",
        json={
            "tenant_name": "Spa " + slug,
            "tenant_slug": slug,
            "admin_full_name": "Admin",
            "phone_number": phone,
            "password": password,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_register_tenant_login_me(client):
    slug, phone = unique_slug(), unique_phone()
    data = await _register_tenant(client, slug, phone)
    assert data["user"]["role"] == "ADMIN"

    r = await client.post(
        "/api/v1/auth/login",
        headers={"X-Tenant-Slug": slug},
        json={"phone_number": phone, "password": "secret123"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["tenant"]["slug"] == slug


@pytest.mark.asyncio
async def test_wrong_password_and_duplicate_slug(client):
    slug, phone = unique_slug(), unique_phone()
    await _register_tenant(client, slug, phone)
    r = await client.post(
        "/api/v1/auth/login",
        headers={"X-Tenant-Slug": slug},
        json={"phone_number": phone, "password": "wrong"},
    )
    assert r.status_code == 401
    r = await client.post(
        "/api/v1/auth/register-tenant",
        json={
            "tenant_name": "x", "tenant_slug": slug, "admin_full_name": "x",
            "phone_number": unique_phone(), "password": "secret123",
        },
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_same_phone_in_two_tenants_and_isolation(client):
    s1, s2, phone = unique_slug(), unique_slug(), unique_phone()
    await _register_tenant(client, s1, unique_phone())
    await _register_tenant(client, s2, unique_phone())

    for s in (s1, s2):
        r = await client.post(
            "/api/v1/auth/register",
            headers={"X-Tenant-Slug": s},
            json={"full_name": "Khach", "phone_number": phone, "password": "secret123"},
        )
        assert r.status_code == 201, r.text
        assert r.json()["user"]["role"] == "CUSTOMER"

    # trùng SĐT trong cùng tenant -> 409
    r = await client.post(
        "/api/v1/auth/register",
        headers={"X-Tenant-Slug": s1},
        json={"full_name": "Khach", "phone_number": phone, "password": "secret123"},
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_rls_blocks_cross_tenant_and_no_context(client):
    s1, s2 = unique_slug(), unique_slug()
    t1 = (await _register_tenant(client, s1, unique_phone()))["user"]["tenant_id"]
    await _register_tenant(client, s2, unique_phone())

    async with AsyncSessionLocal() as session:
        # Không có tenant context -> thấy 0 dòng
        n = (await session.execute(text("SELECT count(*) FROM users"))).scalar_one()
        assert n == 0
        await session.rollback()

        import uuid
        await set_tenant_context(session, uuid.UUID(t1))
        tenants = (await session.execute(text("SELECT DISTINCT tenant_id FROM users"))).scalars().all()
        assert [str(t) for t in tenants] == [t1]


@pytest.mark.asyncio
async def test_protected_requires_token(client):
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    r = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401
