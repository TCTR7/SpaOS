import asyncio
import uuid
import pytest
from fastapi import HTTPException
from tests.conftest import unique_phone
from tests.test_sprint4_reports_notifications import B, _setup, _day
from app.services import booking_service


def payload(c, **extra):
    return dict(request_id=str(uuid.uuid4()), new_customer={"full_name": "Batch Customer", "phone_number": unique_phone()},
        items=[{"service_id": c["pkg_svc"]["id"]}],
        start_times=[f"{_day(i)}T10:00:00+07:00" for i in (3, 4, 5)], **extra)


@pytest.mark.asyncio
@pytest.mark.parametrize("code", [409, 503])
async def test_second_row_failure_rolls_back_customer_package_bookings_and_audit(client, monkeypatch, code):
    c = await _setup(client)
    data = payload(c)
    original = booking_service.create_booking
    calls = 0
    async def fail(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise HTTPException(code, "QA second row failure")
        return await original(*args, **kwargs)
    monkeypatch.setattr(booking_service, "create_booking", fail)
    r = await client.post(f"{B}/bookings/manual-batches", headers=c["ah"], json=data)
    assert r.status_code == code, r.text
    assert (await client.get(f"{B}/customers", headers=c["ah"], params={"q": data["new_customer"]["phone_number"]})).json() == []
    assert (await client.get(f"{B}/bookings", headers=c["ah"])).json() == []
    assert (await client.get(f"{B}/customer-packages", headers=c["ah"])).json() == []
    assert (await client.get(f"{B}/bookings/manual-batches/{data['request_id']}", headers=c["ah"])).status_code == 404
    monkeypatch.setattr(booking_service, "create_booking", original)
    retry = await client.post(f"{B}/bookings/manual-batches", headers=c["ah"], json=data)
    assert retry.status_code == 201, retry.text
    assert len(retry.json()["booking_ids"]) == 3


@pytest.mark.asyncio
async def test_concurrent_same_request_replays_ids_and_checks_permissions(client):
    c, other = await _setup(client), await _setup(client)
    data = payload(c)
    responses = await asyncio.gather(*(client.post(f"{B}/bookings/manual-batches", headers=c["ah"], json=data) for _ in range(3)))
    assert all(r.status_code == 201 for r in responses), [r.text for r in responses]
    result = responses[0].json()
    assert all(r.json() == result for r in responses)
    assert len((await client.get(f"{B}/bookings", headers=c["ah"])).json()) == 3
    assert len((await client.get(f"{B}/customer-packages", headers=c["ah"])).json()) == 1
    path = f"{B}/bookings/manual-batches/{data['request_id']}"
    assert (await client.get(path, headers=c["ah"])).json() == result
    for h in (other["ah"], c["staff"][0]["h"]):
        assert (await client.get(path, headers=h)).status_code == 404
    assert (await client.get(path, headers=c["ch"])).status_code == 403
    assert (await client.post(f"{B}/bookings/manual-batches", headers=c["ah"], json={**data, "note": "Different"})).status_code == 409
    assert (await client.post(f"{B}/bookings/manual-batches", headers=c["ch"], json=data)).status_code == 403
    assert (await client.post(f"{B}/bookings/manual-batches", headers=c["ah"], json={**data, "tenant_id": other["admin_id"]})).status_code == 422


@pytest.mark.asyncio
async def test_batch_conflicts_and_package_capacity_are_atomic(client):
    c = await _setup(client, staff_count=1)
    data = payload(c, staff_id=c["staff"][0]["id"])
    data["start_times"] = [f"{_day()}T10:00:00+07:00", f"{_day()}T10:15:00+07:00"]
    r = await client.post(f"{B}/bookings/manual-batches", headers=c["ah"], json=data)
    assert r.status_code == 409, r.text
    assert (await client.get(f"{B}/bookings", headers=c["ah"])).json() == []

    data = payload(c)
    data["start_times"] += [f"{_day(i)}T10:00:00+07:00" for i in range(6, 15)]
    r = await client.post(f"{B}/bookings/manual-batches", headers=c["ah"], json=data)
    assert r.status_code == 409, r.text
    assert (await client.get(f"{B}/bookings", headers=c["ah"])).json() == []


@pytest.mark.asyncio
async def test_distinct_batches_same_auto_staff_cannot_double_book(client):
    c = await _setup(client, staff_count=1)
    requests = [payload(c) for _ in range(2)]
    responses = await asyncio.wait_for(asyncio.gather(*(client.post(f"{B}/bookings/manual-batches", headers=c["ah"], json=p) for p in requests)), timeout=20)
    assert sorted(r.status_code for r in responses) == [201, 409], [r.text for r in responses]
    assert len((await client.get(f"{B}/bookings", headers=c["ah"])).json()) == 3
    assert len((await client.get(f"{B}/customer-packages", headers=c["ah"])).json()) == 1


@pytest.mark.asyncio
async def test_legacy_separate_requests_leave_partial_state_on_second_failure(client, monkeypatch):
    """T01a reproduction of the former UI sequence, before switching it to batch."""
    c = await _setup(client)
    data = payload(c)
    customer = (await client.post(f"{B}/customers", headers=c["ah"], json=data["new_customer"])).json()
    package = (await client.post(f"{B}/customer-packages", headers=c["ah"], json={"customer_id": customer["id"], "service_id": c["pkg_svc"]["id"]})).json()
    first = await client.post(f"{B}/bookings", headers=c["ah"], json={"customer_id": customer["id"], "start_time": data["start_times"][0], "items": [{"service_id": c["pkg_svc"]["id"], "customer_package_id": package["id"]}]})
    assert first.status_code == 201, first.text
    async def fail(*args, **kwargs):
        raise HTTPException(503, "QA legacy second row failure")
    monkeypatch.setattr(booking_service, "create_booking", fail)
    second = await client.post(f"{B}/bookings", headers=c["ah"], json={"customer_id": customer["id"], "start_time": data["start_times"][1], "items": [{"service_id": c["pkg_svc"]["id"]}]})
    assert second.status_code == 503
    assert len((await client.get(f"{B}/bookings", headers=c["ah"])).json()) == 1
    assert len((await client.get(f"{B}/customers/{customer['id']}/packages", headers=c["ah"])).json()) == 1


@pytest.mark.asyncio
async def test_staff_replay_is_denied_after_customer_ownership_transfer(client):
    c = await _setup(client)
    assigned = await client.patch(f"{B}/customers/{c['customer_id']}/assignment", headers=c["ah"], json={"assigned_staff_id": c["staff"][0]["id"]})
    assert assigned.status_code == 200
    data = payload(c)
    del data["new_customer"]
    data["customer_id"] = c["customer_id"]
    r = await client.post(f"{B}/bookings/manual-batches", headers=c["staff"][0]["h"], json=data)
    assert r.status_code == 201, r.text
    moved = await client.patch(f"{B}/customers/{c['customer_id']}/assignment", headers=c["ah"], json={"assigned_staff_id": c["staff"][1]["id"]})
    assert moved.status_code == 200
    assert (await client.get(f"{B}/bookings/manual-batches/{data['request_id']}", headers=c["staff"][0]["h"])).status_code == 404
    assert (await client.post(f"{B}/bookings/manual-batches", headers=c["staff"][0]["h"], json=data)).status_code == 404
