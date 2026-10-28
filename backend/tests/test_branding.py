import hashlib
import hmac
import json
import uuid
import pytest
from sqlalchemy import select, text
from app.core.config import settings
from app.models.models import DeploymentBranding, Spa
from app.schemas.operator import OwnerCreate
from app.api.v1.operator import request_digest
from tests.test_operator import operator_env, login, owner_body, B

@pytest.mark.asyncio
async def test_operator_branding_validation_and_public_shape(operator_env):
    client, _ = operator_env
    assert (await client.get(B+"/branding")).json() == {"theme_color":"#be185d","configured":False}
    headers = await login(client)
    for color in ("red", "#abc", "#zzzzzz", "#112233; color:red", "", None):
        assert (await client.post(B+"/operator/branding", headers=headers, json={"theme_color":color})).status_code == 422
    assert (await client.post(B+"/operator/branding", headers=headers, json={"theme_color":"#2563eb","tenant_id":str(uuid.uuid4())})).status_code == 422
    result = await client.post(B+"/operator/branding", headers=headers, json={"theme_color":"#00FF00"})
    assert result.status_code == 200 and result.json() == {"theme_color":"#00ff00","configured":True}
    assert (await client.get(B+"/branding")).json() == result.json()

@pytest.mark.asyncio
async def test_owner_cannot_change_deployment_branding_and_customer_reads_it(operator_env):
    client, _ = operator_env
    operator = await login(client)
    body = {**owner_body(),"theme_color":"#2563eb"}
    record = await client.post(B+"/operator/owners", headers=operator, json=body)
    assert record.status_code == 201, record.text
    token = (await client.post(B+"/auth/login", json={"phone_number":body["phone_number"],"password":body["password"]})).json()["access_token"]
    owner = {"Authorization":"Bearer "+token}
    assert (await client.post(B+"/operator/branding", headers=owner, json={"theme_color":"#ff0000"})).status_code == 401
    assert (await client.post(B+"/operator/branding", json={"theme_color":"#ff0000"})).status_code == 401
    me = (await client.get(B+"/auth/me", headers=owner)).json()
    assert (await client.get(B+"/public/tenants/"+me["tenant"]["slug"])).json()["theme_color"] == "#2563eb"
    assert (await client.get(B+"/branding")).json()["theme_color"] == "#be185d"
    assert me["spa"]["theme_color"] == "#2563eb"
    repeat = await client.post(B+"/operator/owners", headers=operator, json=body)
    assert repeat.json()["id"] == record.json()["id"]
    assert (await client.post(B+"/operator/owners", headers=operator,json={**body,"theme_color":"#ffff00"})).status_code == 409

@pytest.mark.asyncio
async def test_branding_rolls_back_on_owner_conflict_and_raw_rls_prevents_write(operator_env):
    client, sessions = operator_env
    headers = await login(client)
    body = {**owner_body(),"theme_color":"#2563eb"}
    assert (await client.post(B+"/operator/owners",headers=headers,json=body)).status_code == 201
    assert (await client.post(B+"/operator/owners",headers=headers,json={**body,"request_id":str(uuid.uuid4()),"theme_color":"#ffff00"})).status_code == 409
    assert (await client.get(B+"/branding")).json()["theme_color"] == "#be185d"
    async with sessions() as db:
        for key in ("app.current_operator_id","app.operator_phone","app.current_tenant_id","app.current_spa_id","app.public_spa_slug"):
            await db.execute(text("SELECT set_config(:key,'',true)"),{"key":key})
        assert (await db.execute(select(Spa))).scalars().all() == []
        assert (await db.execute(select(DeploymentBranding))).scalars().all() == []
        result = await db.execute(text("UPDATE deployment_branding SET theme_color='#ff0000' WHERE slot=1"))
        assert result.rowcount == 0
        await db.rollback()
    assert (await client.get(B+"/branding")).json()["theme_color"] == "#be185d"

def test_owner_digest_remains_compatible_when_color_was_omitted():
    body = owner_body()
    expected = hmac.new(settings.JWT_SECRET_KEY.encode(),
        json.dumps(body,ensure_ascii=False,sort_keys=True).encode(),hashlib.sha256).hexdigest()
    assert request_digest(OwnerCreate(**body)) == expected
