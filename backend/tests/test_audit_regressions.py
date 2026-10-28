import asyncio
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.core.database import AsyncSessionLocal, set_tenant_context
from app.services import booking_service as svc
from tests.test_booking_concurrency import B, _setup_spa, _day, _body


@pytest.mark.asyncio
async def test_create_and_complete_package_do_not_deadlock(client, monkeypatch):
    ctx = await _setup_spa(client)
    pkg = (await client.post(f"{B}/customer-packages", headers=ctx["ah"], json={
        "customer_id": ctx["customer_id"], "service_id": ctx["pkg_svc"]["id"],
    })).json()
    def body(hour):
        return {"start_time": f"{_day()}T{hour:02d}:00:00+07:00", "staff_id": ctx["staff"][0],
                "items": [{"service_id": ctx["pkg_svc"]["id"], "customer_package_id": pkg["id"]}]}
    booking = (await client.post(f"{B}/bookings", headers=ctx["ch"], json=body(9))).json()
    url = f"{B}/bookings/{booking['id']}/status"
    assert (await client.patch(url, headers=ctx["ah"], json={"status": "CONFIRMED"})).status_code == 200
    package_locked, completion_started = asyncio.Event(), asyncio.Event()
    original_packages, original_booking = svc._lock_packages, svc.get_booking_full
    original_access = svc.booking_access
    from app.services import assignment_service
    original_workforce = assignment_service.lock_workforce
    async def lock_workforce(*args, **kwargs):
        if asyncio.current_task().get_name() == "audit-complete":
            completion_started.set()
        return await original_workforce(*args, **kwargs)
    monkeypatch.setattr(assignment_service, "lock_workforce", lock_workforce)

    async def access(*args, **kwargs):
        if asyncio.current_task().get_name() == "audit-complete":
            completion_started.set()
        return await original_access(*args, **kwargs)

    monkeypatch.setattr(svc, "booking_access", access)

    async def lock_packages(*args, **kwargs):
        name = asyncio.current_task().get_name()
        if name == "audit-complete":
            completion_started.set()
        result = await original_packages(*args, **kwargs)
        if name == "audit-create":
            package_locked.set()
            await asyncio.wait_for(completion_started.wait(), 10)
        return result

    async def get_booking(*args, **kwargs):
        result = await original_booking(*args, **kwargs)
        if asyncio.current_task().get_name() == "audit-complete" and kwargs.get("lock"):
            completion_started.set()
        return result

    monkeypatch.setattr(svc, "_lock_packages", lock_packages)
    monkeypatch.setattr(svc, "get_booking_full", get_booking)
    creating = asyncio.create_task(client.post(f"{B}/bookings", headers=ctx["ch"], json=body(11)), name="audit-create")
    await asyncio.wait_for(package_locked.wait(), 10)
    completing = asyncio.create_task(client.patch(url, headers=ctx["ah"], json={"status": "COMPLETED"}), name="audit-complete")
    try:
        results = await asyncio.wait_for(asyncio.gather(creating, completing, return_exceptions=True), 20)
        assert [getattr(r, "status_code", repr(r)) for r in results] == [201, 200]
    finally:
        for task in (creating, completing):
            if not task.done():
                task.cancel()
        await asyncio.gather(creating, completing, return_exceptions=True)
    packages = (await client.get(f"{B}/customer-packages", headers=ctx["ah"])).json()
    assert packages[0]["used_sessions"] == 1


@pytest.mark.asyncio
async def test_buffer_includes_booking_on_following_day(client):
    ctx = await _setup_spa(client)
    ah, ch, staff = ctx["ah"], ctx["ch"], ctx["staff"][0]
    await client.patch(f"{B}/tenants/me", headers=ah, json={"open_time": "00:00:00", "close_time": "23:59:00", "buffer_minutes": 30})
    await client.put(f"{B}/staff/{staff}/schedules", headers=ah, json={"schedules": [
        {"day_of_week": d, "start_time": "00:00:00", "end_time": "23:59:00"} for d in range(7)
    ]})
    day = _day()
    assert (await client.post(f"{B}/bookings", headers=ch, json=_body(f"{day + timedelta(days=1)}T00:00:00+07:00", [ctx["s30"]], staff))).status_code == 201
    response = await client.get(f"{B}/bookings/available-slots", headers=ch, params={"date": str(day), "service_ids": [ctx["s30"]["id"]], "staff_id": staff})
    assert not any(s["start_time"].startswith(f"{day}T23:15") for s in response.json()["slots"])
    assert (await client.post(f"{B}/bookings", headers=ch, json=_body(f"{day}T23:15:00+07:00", [ctx["s30"]], staff))).status_code == 409


@pytest.mark.asyncio
async def test_naive_package_expiry_is_normalized(client):
    ctx = await _setup_spa(client)
    response = await client.post(f"{B}/customer-packages", headers=ctx["ah"], json={
        "customer_id": ctx["customer_id"], "service_id": ctx["pkg_svc"]["id"],
        "expiry_date": f"{_day(10)}T12:00:00",
    })
    assert response.status_code == 201, response.text
    from datetime import datetime
    assert datetime.fromisoformat(response.json()["expiry_date"].replace("Z", "+00:00")).hour == 5


@pytest.mark.asyncio
async def test_concurrent_subscription_is_idempotent(client):
    ctx = await _setup_spa(client)
    body = {"endpoint": "https://push.example.com/audit/" + uuid.uuid4().hex, "keys": {"p256dh": "test", "auth": "test"}}
    results = await asyncio.gather(*[client.post(f"{B}/notifications/subscribe", headers=ctx["ch"], json=body) for _ in range(5)], return_exceptions=True)
    assert [getattr(r, "status_code", repr(r)) for r in results] == [201] * 5
    assert len({r.json()["id"] for r in results}) == 1


@pytest.mark.asyncio
async def test_all_business_tables_force_rls(client):
    tables = {"users", "staff_schedules", "services", "customer_packages", "bookings", "booking_items", "push_subscriptions", "notifications", "manual_booking_batches"}
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(text("SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class WHERE relnamespace = 'public'::regnamespace"))).all()
        assert {name for name, enabled, forced in rows if enabled and forced} >= tables
        assert not (await session.execute(text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user"))).scalar_one()
        for table in sorted(tables):
            assert (await session.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one() == 0


@pytest.mark.asyncio
async def test_notification_fk_locks_do_not_deadlock_booking(client):
    from app.services.notification_service import Draft, _deliver

    ctx = await _setup_spa(client)
    staff_id = uuid.UUID(ctx["staff"][0])
    response = await client.post(f"{B}/bookings", headers=ctx["ch"], json=_body(f"{_day()}T09:00:00+07:00", [ctx["s30"]], str(staff_id)))
    assert response.status_code == 201
    booking = response.json()
    tenant_id, booking_id = uuid.UUID(booking["tenant_id"]), uuid.UUID(booking["id"])
    async with AsyncSessionLocal() as holder, AsyncSessionLocal() as observer:
        await set_tenant_context(holder, tenant_id)
        holder_pid = (await holder.execute(text("SELECT pg_backend_pid()"))).scalar_one()
        await svc._lock_staff_row(holder, tenant_id, staff_id)
        delivery = asyncio.create_task(_deliver(tenant_id, [Draft(staff_id, "Audit", "FK lock order")], "BOOKING_RESCHEDULED", booking_id))
        try:
            async def wait_for_blocked_delivery():
                while True:
                    blocked = (await observer.execute(text(
                        "SELECT EXISTS (SELECT 1 FROM pg_stat_activity WHERE :pid = ANY(pg_blocking_pids(pid)))"
                    ), {"pid": holder_pid})).scalar_one()
                    if blocked:
                        return
                    if delivery.done():
                        await delivery
                        pytest.fail("Notification did not acquire the expected recipient lock")
                    await asyncio.sleep(0.01)
            await asyncio.wait_for(wait_for_blocked_delivery(), 5)
            tenant = await svc.load_tenant(holder, tenant_id)
            start, end = svc.local_day_bounds(_day())
            busy = await asyncio.wait_for(svc.fetch_busy(holder, tenant, [staff_id], start, end, lock=True), 3)
            assert len(busy[staff_id]) == 1
            await holder.rollback()
            await asyncio.wait_for(delivery, 5)
        finally:
            await holder.rollback()
            if not delivery.done():
                delivery.cancel()
            await asyncio.gather(delivery, return_exceptions=True)
