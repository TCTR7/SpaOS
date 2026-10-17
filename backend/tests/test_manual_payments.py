import asyncio
import uuid
from decimal import Decimal
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.database import AsyncSessionLocal, set_tenant_context
from app.schemas.payments import InvoiceCreate, ReceiptCreate
from pydantic import ValidationError
from tests.test_sprint4_reports_notifications import B, _setup, _book, _day


async def invoice(client, c, *, package=False):
    if package:
        source = (await client.post(f"{B}/customer-packages", headers=c["ah"],
            json={"customer_id": c["customer_id"], "service_id": c["pkg_svc"]["id"]})).json()
        payload = {"customer_package_id": source["id"]}
    else:
        source = await _book(client, c["ch"], f"{_day()}T09:00:00+07:00", [c["s60"]])
        payload = {"booking_id": source["id"]}
    result = await client.post(f"{B}/payments/invoices", headers=c["ah"], json=payload)
    assert result.status_code == 201, result.text
    return result.json(), source


def receipt(amount="100000", key=None, method="CASH"):
    return {"amount": amount, "method": method, "idempotency_key": key or str(uuid.uuid4())}


def test_payment_input_validation():
    with pytest.raises(ValidationError):
        InvoiceCreate()
    with pytest.raises(ValidationError):
        InvoiceCreate(booking_id=uuid.uuid4(), customer_package_id=uuid.uuid4())
    for amount in ("0", "-1", "0.001", "NaN", "Infinity"):
        with pytest.raises(ValidationError):
            ReceiptCreate(**receipt(amount))
    with pytest.raises(ValidationError):
        ReceiptCreate(**receipt(), tenant_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_partial_full_overpayment_and_reversal_are_audited(client):
    c = await _setup(client, staff_count=1)
    inv, _ = await invoice(client, c)
    path = f"{B}/payments/invoices/{inv['id']}"
    assert inv["status"] == "UNPAID"
    first = await client.post(path+"/receipts", headers=c["ah"], json=receipt())
    assert first.status_code == 201, first.text
    state = (await client.get(path, headers=c["ah"])).json()
    assert (state["status"], Decimal(state["balance_due"])) == ("PARTIAL", Decimal("200000"))
    assert (await client.post(path+"/receipts", headers=c["ah"], json=receipt("200001"))).status_code == 409
    assert (await client.post(path+"/receipts", headers=c["ah"], json=receipt("200000", method="BANK_TRANSFER"))).status_code == 201
    assert (await client.get(path, headers=c["ah"])).json()["status"] == "PAID"
    undo = {"idempotency_key": str(uuid.uuid4()), "reason": "Ghi nhầm khoản thu"}
    response = await client.post(f"{B}/payments/entries/{first.json()['id']}/void", headers=c["ah"], json=undo)
    assert response.status_code == 201, response.text
    assert Decimal(response.json()["amount"]) == -100000
    assert (await client.get(path, headers=c["ah"])).json()["status"] == "PARTIAL"
    repeat = await client.post(f"{B}/payments/entries/{first.json()['id']}/void", headers=c["ah"], json=undo)
    assert repeat.json()["id"] == response.json()["id"]
    assert (await client.post(f"{B}/payments/entries/{first.json()['id']}/void", headers=c["ah"],
            json={"idempotency_key": str(uuid.uuid4()), "reason": "Hủy lần hai"})).status_code == 409
    logs = (await client.get(f"{B}/audit-logs", headers=c["ah"], params={"entity_id": inv["id"]})).json()
    assert sorted(r["action"] for r in logs) == sorted(["INVOICE_CREATED", "PAYMENT_RECEIVED", "PAYMENT_RECEIVED", "PAYMENT_VOIDED"])
    assert all(r["actor_id"] == c["admin_id"] for r in logs)


@pytest.mark.asyncio
async def test_concurrent_receipts_same_key_and_overpayment(client):
    c = await _setup(client, staff_count=1)
    inv, _ = await invoice(client, c)
    path = f"{B}/payments/invoices/{inv['id']}/receipts"
    body = receipt("200000")
    results = await asyncio.wait_for(asyncio.gather(*[client.post(path, headers=c["ah"], json=body) for _ in range(5)]), 15)
    assert [r.status_code for r in results] == [201]*5
    assert len({r.json()["id"] for r in results}) == 1
    assert (await client.post(path, headers=c["ah"], json={**body, "amount": "1"})).status_code == 409
    results = await asyncio.wait_for(asyncio.gather(*[
        client.post(path, headers=c["ah"], json=receipt("100000")) for _ in range(2)]), 15)
    assert sorted(r.status_code for r in results) == [201, 409]


@pytest.mark.asyncio
async def test_finance_admin_only_and_cross_tenant_isolation(client):
    a, b = await _setup(client), await _setup(client)
    inv, source = await invoice(client, a)
    base = f"{B}/payments/invoices"
    entry = (await client.post(f"{base}/{inv['id']}/receipts", headers=a["ah"], json=receipt())).json()
    for headers in (a["ch"], a["staff"][0]["h"]):
        assert (await client.get(base, headers=headers)).status_code == 403
        assert (await client.get(f"{B}/audit-logs", headers=headers)).status_code == 403
        assert (await client.post(f"{base}/{inv['id']}/receipts", headers=headers, json=receipt())).status_code == 403
    assert (await client.get(base)).status_code == 401
    assert (await client.get(base, headers=b["ah"])).json() == []
    assert (await client.get(f"{base}/{inv['id']}", headers=b["ah"])).status_code == 404
    assert (await client.post(base, headers=b["ah"], json={"booking_id": source["id"]})).status_code == 404
    assert (await client.post(f"{base}/{inv['id']}/receipts", headers=b["ah"], json=receipt())).status_code == 404
    assert (await client.post(f"{B}/payments/entries/{entry['id']}/void", headers=b["ah"],
            json={"idempotency_key": str(uuid.uuid4()), "reason": "No"})).status_code == 404
    assert (await client.get(f"{B}/audit-logs", headers=b["ah"], params={"entity_id": inv["id"]})).json() == []


@pytest.mark.asyncio
async def test_package_sale_snapshot_and_no_double_charge_on_package_session(client):
    c = await _setup(client, staff_count=1)
    inv, pkg = await invoice(client, c, package=True)
    assert Decimal(inv["amount_due"]) == 2000000
    await client.patch(f"{B}/services/{c['pkg_svc']['id']}", headers=c["ah"], json={"price": 999999})
    repeat = await client.post(f"{B}/payments/invoices", headers=c["ah"], json={"customer_package_id": pkg["id"]})
    assert repeat.json()["id"] == inv["id"] and Decimal(repeat.json()["amount_due"]) == 2000000
    booking = await _book(client, c["ch"], f"{_day()}T10:00:00+07:00", [c["pkg_svc"]], package_id=pkg["id"])
    zero = await client.post(f"{B}/payments/invoices", headers=c["ah"], json={"booking_id": booking["id"]})
    assert zero.status_code == 201 and Decimal(zero.json()["amount_due"]) == 0
    assert zero.json()["status"] == "PAID"
    assert (await client.post(f"{B}/payments/invoices/{zero.json()['id']}/receipts",
            headers=c["ah"], json=receipt("1"))).status_code == 409


@pytest.mark.asyncio
async def test_legacy_package_requires_explicit_price(client):
    c = await _setup(client, staff_count=1)
    pkg = (await client.post(f"{B}/customer-packages", headers=c["ah"],
        json={"customer_id": c["customer_id"], "service_id": c["pkg_svc"]["id"]})).json()
    async with AsyncSessionLocal() as session:
        me = (await client.get(f"{B}/auth/me", headers=c["ah"])).json()
        await set_tenant_context(session, uuid.UUID(me["user"]["tenant_id"]))
        await session.execute(text("UPDATE customer_packages SET purchase_price=NULL WHERE id=:id AND tenant_id=:tid"),
                              {"id": uuid.UUID(pkg["id"]), "tid": uuid.UUID(me["user"]["tenant_id"])})
        await session.commit()
    payload = {"customer_package_id": pkg["id"]}
    assert (await client.post(f"{B}/payments/invoices", headers=c["ah"], json=payload)).status_code == 422
    result = await client.post(f"{B}/payments/invoices", headers=c["ah"], json={**payload, "legacy_amount_due": "500000"})
    assert result.status_code == 201 and Decimal(result.json()["amount_due"]) == 500000


@pytest.mark.asyncio
async def test_ledger_and_audit_append_only_and_rls(client):
    c = await _setup(client, staff_count=1)
    inv, _ = await invoice(client, c)
    await client.post(f"{B}/payments/invoices/{inv['id']}/receipts", headers=c["ah"], json=receipt())
    me = (await client.get(f"{B}/auth/me", headers=c["ah"])).json()
    tid = uuid.UUID(me["user"]["tenant_id"])
    for table in ("payment_invoices", "payment_entries", "audit_logs"):
        async with AsyncSessionLocal() as session:
            assert (await session.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one() == 0
            enabled, forced = (await session.execute(text("SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname=:name"), {"name": table})).one()
            assert enabled and forced
    for table in ("payment_entries", "audit_logs"):
        async with AsyncSessionLocal() as session:
            await set_tenant_context(session, tid)
            with pytest.raises(DBAPIError):
                await session.execute(text(f"UPDATE {table} SET updated_at=now() WHERE tenant_id=:tid"), {"tid": tid})
            await session.rollback()


@pytest.mark.asyncio
async def test_summary_uses_receipts_not_completed_services(client):
    c = await _setup(client, staff_count=1)
    inv, _ = await invoice(client, c)
    body = receipt("12345.67", method="BANK_TRANSFER")
    r = await client.post(f"{B}/payments/invoices/{inv['id']}/receipts", headers=c["ah"], json=body)
    assert r.status_code == 201
    today = datetime.now(timezone.utc).astimezone(__import__("zoneinfo").ZoneInfo("Asia/Ho_Chi_Minh")).date().isoformat()
    response = await client.get(f"{B}/payments/summary", headers=c["ah"], params={"date_from": today, "date_to": today})
    assert response.status_code == 200
    assert Decimal(str(response.json()["net_received"])) == Decimal("12345.67")
    assert Decimal(str(response.json()["cash"])) == 0


@pytest.mark.asyncio
async def test_handover_is_explicit_admin_only_and_rollback_on_conflict(client):
    c = await _setup(client)
    a, b = c["staff"]
    booking = await _book(client, c["ch"], f"{_day()}T09:00:00+07:00", [c["s30"]], a["id"])
    path = f"{B}/bookings/{booking['id']}"
    payload = {"start_time": f"{_day()}T13:00:00+07:00", "staff_id": b["id"], "transfer_customer": True}
    assert (await client.patch(path, headers=c["ch"], json=payload)).status_code == 403
    assert (await client.patch(path, headers=a["h"], json=payload)).status_code == 403
    rival = await _book(client, c["ch"], f"{_day()}T13:00:00+07:00", [c["s30"]], b["id"])
    assert (await client.patch(path, headers=c["ah"], json=payload)).status_code == 409
    assert (await client.get(f"{B}/customers", headers=a["h"])).json()[0]["assigned_staff_id"] == a["id"]
    await client.post(f"{B}/bookings/{rival['id']}/cancel", headers=c["ah"])
    assert (await client.patch(path, headers=c["ah"], json=payload)).status_code == 200
    assert (await client.get(f"{B}/customers", headers=a["h"])).json() == []
    assert (await client.get(f"{B}/customers", headers=b["h"])).json()[0]["assigned_staff_id"] == b["id"]
    logs = (await client.get(f"{B}/audit-logs", headers=c["ah"], params={"entity_id": booking["id"]})).json()
    assert sum(row["action"] == "BOOKING_RESCHEDULED" for row in logs) == 1


@pytest.mark.asyncio
async def test_collection_list_is_automatic_read_only_and_scoped(client):
    c = await _setup(client, staff_count=1)
    pkg = (await client.post(f"{B}/customer-packages", headers=c["ah"],
        json={"customer_id": c["customer_id"], "service_id": c["pkg_svc"]["id"]})).json()
    booking = await _book(client, c["ch"], f"{_day()}T09:00:00+07:00", [c["s60"]])
    covered = await _book(client, c["ch"], f"{_day()}T11:00:00+07:00", [c["pkg_svc"]], package_id=pkg["id"])
    path = f"{B}/payments/collections"
    result = await client.get(path, headers=c["ah"])
    assert result.status_code == 200, result.text
    rows = {r["source_id"]: r for r in result.json()}
    assert set(rows) == {pkg["id"], booking["id"]}
    assert rows[pkg["id"]]["description"] == pkg["package_name"]
    assert Decimal(rows[pkg["id"]]["amount_due"]) == 2000000
    assert rows[booking["id"]]["customer_id"] == c["customer_id"]
    assert rows[booking["id"]]["invoice_id"] is None
    assert (await client.get(f"{B}/payments/invoices", headers=c["ah"])).json() == []
    all_rows = (await client.get(path, headers=c["ah"], params={"scope": "all"})).json()
    assert next(r for r in all_rows if r["source_id"] == covered["id"])["status"] == "COVERED"
    phone = rows[booking["id"]]["phone_number"]
    assert len((await client.get(path, headers=c["ah"], params={"q": phone})).json()) == 2
    assert (await client.get(path, headers=c["ah"], params={"q": "absent-customer"})).json() == []
    assert len((await client.get(path, headers=c["ah"], params={"limit": 1})).json()) == 1
    for header in (c["ch"], c["staff"][0]["h"]):
        assert (await client.get(path, headers=header)).status_code == 403
    other = await _setup(client, staff_count=1)
    assert (await client.get(path, headers=other["ah"], params={"scope": "all"})).json() == []


@pytest.mark.asyncio
async def test_collection_balances_paid_filter_void_and_cancelled(client):
    c = await _setup(client, staff_count=1)
    inv, booking = await invoice(client, c)
    path = f"{B}/payments/collections"
    entry = (await client.post(f"{B}/payments/invoices/{inv['id']}/receipts",
        headers=c["ah"], json=receipt("300000"))).json()
    assert (await client.get(path, headers=c["ah"])).json() == []
    rows = (await client.get(path, headers=c["ah"], params={"scope": "all"})).json()
    assert rows[0]["status"] == "PAID" and rows[0]["invoice_id"] == inv["id"]
    await client.post(f"{B}/payments/entries/{entry['id']}/void", headers=c["ah"],
        json={"idempotency_key": str(uuid.uuid4()), "reason": "Nhập nhầm"})
    rows = (await client.get(path, headers=c["ah"])).json()
    assert rows[0]["status"] == "UNPAID" and Decimal(rows[0]["balance_due"]) == 300000
    cancelled = await _book(client, c["ch"], f"{_day()}T12:00:00+07:00", [c["s30"]])
    await client.post(f"{B}/bookings/{cancelled['id']}/cancel", headers=c["ah"])
    assert all(r["source_id"] != cancelled["id"] for r in
        (await client.get(path, headers=c["ah"], params={"scope": "all"})).json())


@pytest.mark.asyncio
async def test_collection_legacy_price_uses_confirmed_invoice_not_current_menu(client):
    c = await _setup(client, staff_count=1)
    inv, pkg = await invoice(client, c, package=True)
    tid = uuid.UUID((await client.get(f"{B}/auth/me", headers=c["ah"])).json()["user"]["tenant_id"])
    async with AsyncSessionLocal() as session:
        await set_tenant_context(session, tid)
        await session.execute(text("UPDATE customer_packages SET purchase_price=NULL WHERE id=:id AND tenant_id=:tid"),
            {"id": uuid.UUID(pkg["id"]), "tid": tid})
        await session.commit()
    rows = (await client.get(f"{B}/payments/collections", headers=c["ah"])).json()
    assert rows[0]["status"] == "UNPAID"
    assert Decimal(rows[0]["amount_due"]) == Decimal(inv["amount_due"])
    new_pkg = (await client.post(f"{B}/customer-packages", headers=c["ah"],
        json={"customer_id": c["customer_id"], "service_id": c["pkg_svc"]["id"]})).json()
    async with AsyncSessionLocal() as session:
        await set_tenant_context(session, tid)
        await session.execute(text("UPDATE customer_packages SET purchase_price=NULL WHERE id=:id AND tenant_id=:tid"),
            {"id": uuid.UUID(new_pkg["id"]), "tid": tid})
        await session.commit()
    row = next(r for r in (await client.get(f"{B}/payments/collections", headers=c["ah"])).json()
        if r["source_id"] == new_pkg["id"])
    assert row["status"] == "NEEDS_PRICE" and row["amount_due"] is None
