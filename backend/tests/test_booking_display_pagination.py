import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event

from app.core.database import AsyncSessionLocal, engine, set_tenant_context
from app.models.models import Booking, BookingItem, BookingStatus, User, UserRole
from tests.test_sprint4_reports_notifications import B, _setup, _book, _day


@pytest.mark.asyncio
async def test_display_projection_respects_ownership_and_tenant(client):
    c, other = await _setup(client), await _setup(client)
    booking = await _book(client, c["ch"], f"{_day()}T10:00:00+07:00", [c["s30"]], c["staff"][0]["id"])
    assert booking["customer_name"] == "Khach"
    assert booking["staff_name"] == "KTV 0"
    assert booking["items"][0]["service_name"] == "Goi dau"
    for headers in (c["ah"], c["ch"], c["staff"][0]["h"]):
        response = await client.get(f"{B}/bookings?limit=1", headers=headers)
        assert response.status_code == 200
        assert response.headers["x-has-more"] == "false"
        assert response.json()[0]["customer_name"] == "Khach"
    for headers in (c["staff"][1]["h"], other["ah"]):
        response = await client.get(f"{B}/bookings?customer_id={c['customer_id']}", headers=headers)
        assert response.json() == [] and response.headers["x-has-more"] == "false"
        assert (await client.get(f"{B}/bookings/{booking['id']}", headers=headers)).status_code == 404
    await client.patch(f"{B}/services/{c['s30']['id']}", headers=c["ah"], json={"is_active": False})
    response = await client.get(f"{B}/bookings/{booking['id']}", headers=c["ch"])
    assert response.json()["items"][0]["service_name"] == "Goi dau"
    assert "phone_number" not in response.json()


@pytest.mark.asyncio
async def test_public_staff_is_minimal_scoped_and_independent_of_slots(client):
    c, other = await _setup(client), await _setup(client)
    # No shift on the selected day must not remove a person from the directory.
    await client.put(f"{B}/staff/{c['staff'][0]['id']}/schedules", headers=c["ah"], json={"schedules": []})
    response = await client.get(f"{B}/public/tenants/{c['slug']}")
    staff = response.json()["staff"]
    assert {row["id"] for row in staff} == {row["id"] for row in c["staff"]}
    assert all(set(row) == {"id", "full_name"} for row in staff)
    assert not ({row["id"] for row in staff} & {row["id"] for row in other["staff"]})
    await client.patch(f"{B}/staff/{c['staff'][1]['id']}", headers=c["ah"], json={"is_active": False})
    assert len((await client.get(f"{B}/public/tenants/{c['slug']}")).json()["staff"]) == 1
    assert (await client.get(f"{B}/public/tenants/not-a-real-spa")).status_code == 404


@pytest.mark.asyncio
async def test_more_than_200_rows_paginate_without_n_plus_one(client):
    c = await _setup(client)
    me = (await client.get(f"{B}/auth/me", headers=c["ah"])).json()
    tenant_id = uuid.UUID(me["tenant"]["id"])
    start = datetime.now(timezone.utc) + timedelta(days=5)
    async with AsyncSessionLocal() as db:
        await set_tenant_context(db, tenant_id)
        for i in range(205):
            customer = User(tenant_id=tenant_id, role=UserRole.CUSTOMER, full_name=f"Bulk {i:03d}",
                            phone_number=f"088000{i:04d}", password_hash="unused-qa-fixture",
                            assigned_staff_id=uuid.UUID(c["staff"][0]["id"]))
            db.add(customer)
            db.add(Booking(tenant_id=tenant_id, customer_id=uuid.UUID(c["customer_id"]),
                staff_id=uuid.UUID(c["staff"][0]["id"]), start_time=start + timedelta(hours=i),
                end_time=start + timedelta(hours=i, minutes=30), total_duration_minutes=30,
                total_price=100000, status=BookingStatus.PENDING, items=[BookingItem(
                    tenant_id=tenant_id, service_id=uuid.UUID(c["s30"]["id"]), duration_minutes=30, price=100000)]))
        await db.commit()
    counts = []
    def count_queries(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            counts.append(statement)
    event.listen(engine.sync_engine, "before_cursor_execute", count_queries)
    try:
        first = await client.get(f"{B}/bookings?limit=200", headers=c["ah"])
        large_count = len(counts)
        counts.clear()
        await client.get(f"{B}/bookings?limit=1", headers=c["ah"])
        assert large_count <= len(counts) + 1, "Query count must not grow per booking/item"
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", count_queries)
    second = await client.get(f"{B}/bookings?limit=200&offset=200", headers=c["ah"])
    assert len(first.json()) == 200 and first.headers["x-next-offset"] == "200"
    assert len(second.json()) == 5 and second.headers["x-has-more"] == "false"
    assert len({row["id"] for row in first.json() + second.json()}) == 205
    customers = await client.get(f"{B}/customers?limit=200", headers=c["staff"][0]["h"])
    assert len(customers.json()) == 200 and customers.headers["x-has-more"] == "true"
    found = await client.get(f"{B}/customers?q=Bulk%20204&limit=50", headers=c["staff"][0]["h"])
    assert len(found.json()) == 1 and found.json()[0]["full_name"] == "Bulk 204"
    denied = await client.get(f"{B}/customers?q=Bulk&limit=1", headers=c["staff"][1]["h"])
    assert denied.json() == [] and denied.headers["x-has-more"] == "false"
