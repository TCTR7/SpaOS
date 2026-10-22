import uuid
import pytest
from sqlalchemy import select, text
from tests.test_operator import operator_env, login, owner_body, PASSWORD, B
from app.models.models import OwnerRecoveryGrant
from app.core.database import set_tenant_context


async def provision(client):
    headers, body = await login(client), owner_body()
    response = await client.post(B+"/operator/owners", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return headers, body, response.json()


@pytest.mark.asyncio
async def test_owner_update_recovery_and_history(operator_env):
    client, _ = operator_env
    headers, body, record = await provision(client)
    path = B+"/operator/owners/"+record["id"]
    auth = (await client.post(B+"/auth/login", json={"phone_number":body["phone_number"],"password":body["password"]})).json()
    old = {"Authorization":"Bearer "+auth["access_token"]}
    branch = await client.post(B+"/branches", headers=old, json={"name":"Chi nhánh thứ hai"})
    assert branch.status_code == 201, branch.text
    switched = (await client.post(B+"/branches/"+branch.json()["tenant"]["id"]+"/switch", headers=old)).json()
    old_second = {"Authorization":"Bearer "+switched["access_token"]}
    update = {"full_name":"Chủ spa mới", "phone_number":"0983333444", "current_password":PASSWORD, "identity_verified":True}
    assert (await client.patch(path, headers=headers, json={**update,"current_password":"WrongPass"})).status_code == 403
    assert (await client.patch(path, headers=headers, json={**update,"identity_verified":False})).status_code == 422
    result = await client.patch(path, headers=headers, json=update)
    assert result.status_code == 200, result.text
    assert result.json()["full_name"] == update["full_name"]
    assert len(result.json()["branches"]) == 2
    for session in (old, old_second):
        assert (await client.get(B+"/auth/me", headers=session)).status_code == 401
    issue = {"current_password":PASSWORD,"identity_verified":True}
    first = (await client.post(path+"/recovery-link", headers=headers,json=issue)).json()
    second = await client.post(path+"/recovery-link", headers=headers,json=issue)
    assert second.status_code == 200, second.text
    claim = {"token":first["token"],"password":"NewOwner@2026"}
    assert (await client.post(B+"/operator/recovery",json=claim)).status_code == 400
    claim["token"] = second.json()["token"]
    assert (await client.post(B+"/operator/recovery",json=claim)).status_code == 200
    assert (await client.post(B+"/operator/recovery",json=claim)).status_code == 400
    auth = await client.post(B+"/auth/login",json={"phone_number":update["phone_number"],"password":claim["password"]})
    assert auth.status_code == 200, auth.text
    assert auth.json()["user"]["full_name"] == update["full_name"]
    events = (await client.get(path+"/events",headers=headers)).json()
    assert {e["action"] for e in events} >= {"OWNER_ACCOUNT_UPDATED","OWNER_RECOVERY_COMPLETED"}
    assert second.json()["token"] not in str(events)
    # Historical provision is unchanged while detail reads current account data.
    history = (await client.get(B+"/operator/owners",headers=headers)).json()
    assert next(r for r in history if r["id"] == record["id"])["phone_number"] == body["phone_number"]


@pytest.mark.asyncio
async def test_owner_grant_expiry_scope_and_revocation(operator_env):
    client, sessions = operator_env
    headers, body, record = await provision(client)
    path = B+"/operator/owners/"+record["id"]
    assert (await client.get(path)).status_code == 401
    owner = (await client.post(B+"/auth/login",json={"phone_number":body["phone_number"],"password":body["password"]})).json()
    ah = {"Authorization":"Bearer "+owner["access_token"]}
    assert (await client.get(path,headers=ah)).status_code == 401
    assert (await client.get(B+"/operator/owners/"+str(uuid.uuid4()),headers=headers)).status_code == 404
    issue = {"current_password":PASSWORD,"identity_verified":True}
    issued = (await client.post(path+"/recovery-link",headers=headers,json=issue)).json()
    # A normal password change invalidates previously issued recovery links.
    own = await client.patch(B+"/account/credentials",headers=ah,json={"current_password":body["password"],"password":"ChangedOwn@2026"})
    assert own.status_code == 200, own.text
    assert (await client.post(B+"/operator/recovery",json={"token":issued["token"],"password":"BadReplay@2026"})).status_code == 400
    issued = (await client.post(path+"/recovery-link",headers=headers,json=issue)).json()
    async with sessions() as db:
        await db.execute(text("SELECT set_config('app.current_operator_id',:id,true)"),{"id":(await client.get(B+"/operator/me",headers=headers)).json()["id"]})
        await set_tenant_context(db, uuid.UUID(record["tenant_id"]))
        await db.execute(text("UPDATE owner_recovery_grants SET expires_at=now()-interval '1 minute' WHERE tenant_id=:tid"),{"tid":uuid.UUID(record["tenant_id"])})
        await db.commit()
    assert (await client.post(B+"/operator/recovery",json={"token":issued["token"],"password":"ExpiredLink@2026"})).status_code == 400
    async with sessions() as db:
        await db.execute(text("SELECT set_config('app.current_operator_id','',true)"))
        await db.execute(text("SELECT set_config('app.current_tenant_id','',true)"))
        await db.execute(text("SELECT set_config('app.owner_recovery_hash','',true)"))
        assert not list((await db.execute(select(OwnerRecoveryGrant))).scalars())


@pytest.mark.asyncio
async def test_version_operator_only_and_swagger(operator_env):
    client, _ = operator_env
    assert (await client.get(B+"/operator/system")).status_code == 401
    response = await client.get(B+"/operator/system",headers=await login(client))
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["version"] == (await client.get("/openapi.json")).json()["info"]["version"]
