import uuid
from datetime import datetime
from decimal import Decimal
import pytest
from sqlalchemy import select, text
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.core.config import settings
from app.models.models import BranchMembership, LoginAccount, Tenant
from tests.test_sprint4_reports_notifications import B, _setup
from tests.test_manual_payments import invoice, receipt

async def new_branch(client, c, name="Chi nhánh 2"):
    response = await client.post(f"{B}/branches", headers=c["ah"], json={"name": name})
    assert response.status_code == 201, response.text
    row = response.json()
    token = (await client.post(f"{B}/branches/{row['tenant']['id']}/switch", headers=c["ah"])).json()["access_token"]
    return row, {"Authorization": "Bearer " + token}

@pytest.mark.asyncio
async def test_login_without_slug_and_branch_switch_isolation(client):
    c = await _setup(client, staff_count=1)
    me = (await client.get(f"{B}/auth/me", headers=c["ah"])).json()
    row, second = await new_branch(client, c)
    login = await client.post(f"{B}/auth/login", json={"phone_number": me["user"]["phone_number"], "password": "secret123"})
    assert login.status_code == 200, login.text
    assert (await client.post(f"{B}/auth/login", json={"phone_number": me["user"]["phone_number"], "password": "bad"})).status_code == 401
    branches = (await client.get(f"{B}/branches", headers=c["ah"])).json()
    assert len(branches) == 2 and all(b["is_owner"] for b in branches)
    assert (await client.get(f"{B}/customers", headers=second)).json() == []
    assert (await client.get(f"{B}/customers/{c['customer_id']}/packages", headers=second)).status_code == 404
    other = await _setup(client, staff_count=1)
    other_tid = (await client.get(f"{B}/auth/me", headers=other["ah"])).json()["tenant"]["id"]
    assert (await client.post(f"{B}/branches/{other_tid}/switch", headers=c["ah"])).status_code == 404
    assert (await client.get(f"{B}/dashboard", headers=c["ah"], params={"branch_id": other_tid})).status_code == 404

@pytest.mark.asyncio
async def test_staff_branch_grant_revocation_and_no_owner_escalation(client):
    c = await _setup(client, staff_count=1)
    row, second = await new_branch(client, c)
    tid = row["tenant"]["id"]
    h = c["staff"][0]["h"]
    assert (await client.post(f"{B}/branches/{tid}/switch", headers=h)).status_code == 404
    assert (await client.post(f"{B}/branches", headers=h, json={"name": "Forbidden"})).status_code == 403
    granted = await client.post(f"{B}/branches/{tid}/staff-access", headers=c["ah"], json={"source_staff_id": c["staff"][0]["id"]})
    assert granted.status_code == 201, granted.text
    uid = granted.json()["id"]
    response = await client.post(f"{B}/branches/{tid}/switch", headers=h)
    assert response.status_code == 200
    local = {"Authorization": "Bearer "+response.json()["access_token"]}
    assert (await client.get(f"{B}/customers", headers=local)).json() == []
    assert (await client.get(f"{B}/dashboard", headers=local, params={"all_branches": True})).status_code == 403
    assert (await client.post(f"{B}/branches", headers=local, json={"name": "Forbidden"})).status_code == 403
    assert (await client.patch(f"{B}/staff/{uid}", headers=second, json={"password": "Changed@123"})).status_code == 409
    assert (await client.patch(f"{B}/staff/{uid}", headers=second, json={"is_active": False})).status_code == 200
    assert (await client.get(f"{B}/auth/me", headers=local)).status_code == 401
    assert (await client.post(f"{B}/branches/{tid}/switch", headers=h)).status_code == 404
    assert len((await client.get(f"{B}/branches", headers=h)).json()) == 1

@pytest.mark.asyncio
async def test_dashboard_sums_receipts_and_outstanding_without_double_charge(client):
    c = await _setup(client, staff_count=1)
    inv, _ = await invoice(client, c, package=True)
    await client.post(f"{B}/payments/invoices/{inv['id']}/receipts", headers=c["ah"], json=receipt("12345.67"))
    row, second = await new_branch(client, c)
    result = await client.get(f"{B}/dashboard", headers=c["ah"], params={"all_branches": True})
    assert result.status_code == 200, result.text
    data = result.json()
    assert len(data["branches"]) == 2
    assert Decimal(data["totals"]["net_received"]) == Decimal("12345.67")
    assert Decimal(data["totals"]["outstanding"]) == Decimal("1987654.33")
    assert data["totals"]["active_packages"] == 1
    empty = (await client.get(f"{B}/dashboard", headers=second)).json()
    assert Decimal(empty["totals"]["net_received"]) == 0
    assert (await client.get(f"{B}/dashboard", headers=c["ah"], params={"all_branches": True, "branch_id": row["tenant"]["id"]})).status_code == 422
    assert (await client.get(f"{B}/dashboard", headers=c["ch"])).status_code == 403

@pytest.mark.asyncio
async def test_account_membership_rls_and_branch_deactivation(client):
    c = await _setup(client, staff_count=1)
    row, second = await new_branch(client, c)
    tid = uuid.UUID(row["tenant"]["id"])
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(LoginAccount))).scalars().all() == []
        assert (await db.execute(select(BranchMembership))).scalars().all() == []
        await set_tenant_context(db, tid)
        links = (await db.execute(select(BranchMembership).where(BranchMembership.tenant_id == tid))).scalars().all()
        assert len(links) == 1
        await db.execute(text("UPDATE tenants SET status='INACTIVE' WHERE id=:tid"), {"tid": tid})
        await db.commit()
    assert (await client.get(f"{B}/services", headers=second)).status_code == 403
    assert (await client.get(f"{B}/bookings", headers=second)).status_code == 403
    assert (await client.post(f"{B}/branches/{tid}/switch", headers=c["ah"])).status_code == 404

@pytest.mark.asyncio
async def test_identity_phone_conflict_never_merges_and_password_update(client):
    c = await _setup(client, staff_count=1)
    staff = c["staff"][0]
    user = (await client.get(f"{B}/auth/me", headers=staff["h"])).json()["user"]
    row, second = await new_branch(client, c)
    clash = await client.post(f"{B}/staff", headers=second, json={
        "full_name": "Other person", "phone_number": user["phone_number"], "password": "Other@123"})
    assert clash.status_code == 409
    assert (await client.get(f"{B}/staff", headers=second)).json() == []
    assert (await client.patch(f"{B}/staff/{staff['id']}", headers=c["ah"], json={"password": "NewStaff@123"})).status_code == 200
    assert (await client.post(f"{B}/auth/login", json={"phone_number": user["phone_number"], "password": "NewStaff@123"})).status_code == 200
    assert (await client.post(f"{B}/auth/login", json={"phone_number": user["phone_number"], "password": "secret123"})).status_code == 401

@pytest.mark.asyncio
async def test_production_registration_disabled_and_public_names_only(client, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "ALLOW_TENANT_REGISTRATION", False)
    result = await client.post(f"{B}/auth/register-tenant", json={"tenant_name": "Closed", "tenant_slug": "closed",
        "admin_full_name": "Owner", "phone_number": "0909999888", "password": "Admin@123"})
    assert result.status_code == 403
    result = await client.get(f"{B}/branches/public")
    assert result.status_code == 200
    assert all(set(row) == {"id", "name", "slug"} for row in result.json()["branches"])


@pytest.mark.asyncio
async def test_conflicting_staff_phone_rolls_back_identity_and_user(client):
    c = await _setup(client, staff_count=2)
    a, b = c["staff"]
    phone_a = (await client.get(f"{B}/auth/me", headers=a["h"])).json()["user"]["phone_number"]
    phone_b = (await client.get(f"{B}/auth/me", headers=b["h"])).json()["user"]["phone_number"]
    result = await client.patch(f"{B}/staff/{a['id']}", headers=c["ah"], json={"phone_number": phone_b})
    assert result.status_code == 409
    assert (await client.get(f"{B}/auth/me", headers=a["h"])).json()["user"]["phone_number"] == phone_a
    assert (await client.post(f"{B}/auth/login", json={"phone_number": phone_a, "password": "secret123"})).status_code == 200

@pytest.mark.asyncio
async def test_operator_resolves_one_legacy_identity_without_merging(client, capsys):
    from types import SimpleNamespace
    from scripts.branch_account_audit import run
    from tests.conftest import unique_phone
    from app.models.models import User, UserRole
    from app.core.security import hash_password
    c = await _setup(client, staff_count=1)
    branch, _ = await new_branch(client, c)
    tid = uuid.UUID(branch["tenant"]["id"])
    uid, phone, new_phone = uuid.uuid4(), unique_phone(), unique_phone()
    async with AsyncSessionLocal() as db:
        await set_tenant_context(db, tid)
        db.add(User(id=uid, tenant_id=tid, role=UserRole.STAFF, full_name="Legacy",
            phone_number=phone, password_hash=hash_password("Legacy@123")))
        await db.commit()
    assert (await client.post(f"{B}/auth/login", json={"phone_number": phone, "password": "Legacy@123"})).status_code == 401
    await run(SimpleNamespace(apply=False))
    assert str(uid) in capsys.readouterr().out
    await run(SimpleNamespace(apply=True, tenant_id=str(tid), user_id=str(uid), phone=new_phone))
    login = await client.post(f"{B}/auth/login", json={"phone_number": new_phone, "password": "Legacy@123"})
    assert login.status_code == 200 and login.json()["user"]["id"] == str(uid)
