import uuid
from types import SimpleNamespace
import pytest
import pytest_asyncio
from fastapi import Depends
from pydantic import SecretStr
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.main import app
from app.api.deps import get_tenant_db, get_token_data
from app.core.config import settings
from app.core.database import get_db, engine, set_tenant_context
from app.models.models import Tenant, DeploymentOperator, OwnerProvision
from app.seed import seed

B = "/api/v1"
PHONE, PASSWORD = "0998888777", "OperatorOnlyForQa@2026"

@pytest_asyncio.fixture
async def operator_env(client, monkeypatch):
    # Savepoint sessions allow real API commits while the test itself always rolls back.
    # Run via scripts.test_isolated: the operator singleton must not touch an app database.
    async with engine.connect() as connection:
        outer = await connection.begin()
        sessions = async_sessionmaker(connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
        async def clean(db):
            for key in ("app.current_operator_id", "app.operator_phone", "app.current_tenant_id",
                        "app.current_account_id", "app.login_phone"):
                await db.execute(text("SELECT set_config(:key,'',true)"), {"key": key})
        async def plain():
            async with sessions() as db:
                await clean(db)
                yield db
        async def tenant(token=Depends(get_token_data)):
            async with sessions() as db:
                await clean(db)
                await set_tenant_context(db, token.tenant_id)
                yield db
        previous = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = plain
        app.dependency_overrides[get_tenant_db] = tenant
        monkeypatch.setattr(settings, "OPERATOR_PHONE", PHONE)
        monkeypatch.setattr(settings, "OPERATOR_NAME", "Trần Cao Trung")
        monkeypatch.setattr(settings, "OPERATOR_PASSWORD", SecretStr(PASSWORD))
        try:
            async with sessions() as db:
                await clean(db)
                await seed(db)
            yield client, sessions
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous)
            await outer.rollback()

async def login(client):
    response = await client.post(B+"/operator/login", json={"phone_number": PHONE, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}

def owner_body():
    return {"request_id": str(uuid.uuid4()), "branch_name": "Chi nhánh Đà Nẵng", "owner_full_name": "Trần Cao Trung",
            "phone_number": "0981111222", "password": "Owner@12345"}

@pytest.mark.asyncio
async def test_seed_operator_only_idempotent_and_no_plain_secret(operator_env):
    client, sessions = operator_env
    async with sessions() as db:
        # Seed sets its own identity context. No tenant or business fixtures are generated.
        first = (await db.execute(select(Tenant.id))).all()
        await seed(db)
        row = (await db.execute(select(DeploymentOperator).where(DeploymentOperator.phone_number == PHONE))).scalar_one()
        assert row.password_hash != PASSWORD and row.full_name == "Trần Cao Trung"
        assert (await db.execute(select(Tenant.id))).all() == first
    assert "password" not in (await client.get(B+"/operator/me", headers=await login(client))).text

@pytest.mark.asyncio
async def test_operator_creates_unicode_owner_and_owner_uses_normal_flow(operator_env, monkeypatch):
    client, _ = operator_env
    headers, body = await login(client), owner_body()
    result = await client.post(B+"/operator/owners", headers=headers, json=body)
    assert result.status_code == 201, result.text
    record = result.json()
    assert record["owner_name"] == "Trần Cao Trung" and record["branch_name"] == "Chi nhánh Đà Nẵng"
    assert "password" not in result.text and "digest" not in result.text
    token = (await client.post(B+"/auth/login", json={"phone_number": body["phone_number"], "password": body["password"]})).json()
    owner = {"Authorization": "Bearer "+token["access_token"]}
    assert (await client.get(B+"/auth/me", headers=owner)).json()["user"]["full_name"] == body["owner_full_name"]
    assert (await client.post(B+"/branches", headers=owner, json={"name": "Chi nhánh 2"})).status_code == 201
    assert (await client.get(B+"/operator/owners", headers=owner)).status_code == 401
    assert (await client.get(B+"/customers", headers=headers)).status_code == 401
    assert (await client.get(B+"/branches", headers=headers)).status_code == 401
    assert (await client.get(B+"/operator/owners", headers=headers)).json()[0]["id"] == record["id"]

@pytest.mark.asyncio
async def test_owner_provision_retry_and_conflicts_rollback(operator_env):
    client, _ = operator_env
    headers, body = await login(client), owner_body()
    first = await client.post(B+"/operator/owners", headers=headers, json=body)
    assert first.status_code == 201
    repeat = await client.post(B+"/operator/owners", headers=headers, json=body)
    assert repeat.status_code == 201 and repeat.json()["id"] == first.json()["id"]
    assert (await client.post(B+"/operator/owners", headers=headers, json={**body, "password": "Other@12345"})).status_code == 409
    duplicate = await client.post(B+"/operator/owners", headers=headers, json={**body, "request_id": str(uuid.uuid4())})
    assert duplicate.status_code == 409
    assert len((await client.get(B+"/operator/owners", headers=headers)).json()) == 1

@pytest.mark.asyncio
async def test_private_operator_logout_revokes_token_and_account_can_lock(operator_env):
    client, sessions = operator_env
    headers = await login(client)
    assert (await client.post(B+"/operator/logout", headers=headers)).status_code == 200
    assert (await client.get(B+"/operator/me", headers=headers)).status_code == 401
    headers = await login(client)
    identity = (await client.get(B+"/operator/me", headers=headers)).json()
    async with sessions() as db:
        await db.execute(text("SELECT set_config('app.current_operator_id',:id,true)"), {"id": identity["id"]})
        await db.execute(text("UPDATE deployment_operators SET is_active=false WHERE id=:id"), {"id": uuid.UUID(identity["id"])})
        await db.commit()
    assert (await client.get(B+"/operator/owners", headers=headers)).status_code == 401

@pytest.mark.asyncio
async def test_operator_bruteforce_locks_and_no_context_rls(operator_env):
    client, sessions = operator_env
    for _ in range(5):
        assert (await client.post(B+"/operator/login", json={"phone_number": PHONE, "password": "wrong"})).status_code == 401
    assert (await client.post(B+"/operator/login", json={"phone_number": PHONE, "password": PASSWORD})).status_code == 429
    async with sessions() as db:
        for key in ("app.current_operator_id", "app.operator_phone", "app.current_tenant_id"):
            await db.execute(text("SELECT set_config(:key,'',true)"), {"key": key})
        assert (await db.execute(select(DeploymentOperator))).scalars().all() == []
        assert (await db.execute(select(OwnerProvision))).scalars().all() == []

@pytest.mark.asyncio
async def test_production_owner_guard_does_not_merge_existing_data(operator_env, monkeypatch):
    client, sessions = operator_env
    async with sessions() as db:
        db.add(Tenant(name="Existing", slug="existing-"+uuid.uuid4().hex))
        await db.commit()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    headers = await login(client)
    assert (await client.post(B+"/operator/owners", headers=headers, json=owner_body())).status_code == 409
    assert (await client.get(B+"/operator/owners", headers=headers)).json() == []

@pytest.mark.asyncio
async def test_owner_input_forbids_role_and_requires_confirmation_fields(operator_env):
    client, _ = operator_env
    headers, body = await login(client), owner_body()
    assert (await client.post(B+"/operator/owners", json=body)).status_code == 401
    assert (await client.post(B+"/operator/owners", headers=headers, json={**body, "role": "SUPERADMIN"})).status_code == 422
    assert (await client.post(B+"/operator/owners", headers=headers, json={**body, "owner_full_name": " "})).status_code == 422
    assert (await client.post(B+"/operator/owners", headers=headers, json={**body, "password": "short"})).status_code == 422
