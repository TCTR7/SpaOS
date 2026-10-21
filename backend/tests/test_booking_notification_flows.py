import asyncio
import json
import uuid

import pytest
from app.core.config import settings
from app.services import notification_service as notices
from tests.test_sprint4_reports_notifications import B, _setup, _book, _day


async def notes(client, headers):
    response = await client.get(f"{B}/notifications", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["items"]


@pytest.mark.asyncio
async def test_assigned_technician_gets_notification_and_read_only_appointment(client, monkeypatch):
    c, other = await _setup(client, staff_count=3), await _setup(client, staff_count=1)
    owner, assigned, unrelated = c["staff"]
    response = await client.patch(f"{B}/customers/{c['customer_id']}/assignment", headers=c["ah"],
        json={"assigned_staff_id": owner["id"]})
    assert response.status_code == 200
    sent = []
    async def capture(sub, payload):
        sent.append((sub["endpoint"], json.loads(payload)))
    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", "test")
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", "test")
    monkeypatch.setattr(notices, "_send_one", capture)
    for key, headers in [("admin", c["ah"]), ("owner", owner["h"]), ("assigned", assigned["h"]),
                         ("unrelated", unrelated["h"]), ("foreign", other["ah"])]:
        r = await client.post(f"{B}/notifications/subscribe", headers=headers,
            json={"endpoint": "https://push.example.com/" + key,
                  "keys": {"p256dh": "test", "auth": "test"}})
        assert r.status_code == 201
    bk = await _book(client, c["ch"], f"{_day()}T10:00:00+07:00", [c["s30"]], assigned["id"])
    assert {ep.rsplit("/", 1)[-1] for ep, _ in sent} == {"admin", "owner", "assigned"}
    assigned_notes = await notes(client, assigned["h"])
    assert len(assigned_notes) == 1 and assigned_notes[0]["title"] == "Lịch hẹn mới được giao cho bạn"
    assert await notes(client, unrelated["h"]) == []
    assert await notes(client, other["ah"]) == []
    assert (await client.get(f"{B}/bookings/{bk['id']}", headers=other["ah"])).status_code == 404
    for headers in (owner["h"], assigned["h"]):
        detail = await client.get(f"{B}/bookings/{bk['id']}", headers=headers)
        assert detail.status_code == 200
        assert detail.json()["can_manage"] == (headers == owner["h"])
    rows = (await client.get(f"{B}/bookings", headers=assigned["h"])).json()
    assert len(rows) == 1 and rows[0]["id"] == bk["id"] and rows[0]["can_manage"] is False
    assert (await client.get(f"{B}/customers", headers=assigned["h"])).json() == []
    assert (await client.get(f"{B}/customers/{c['customer_id']}/packages", headers=assigned["h"])).status_code == 404
    for path, body in [(f"/customers/{c['customer_id']}", {"notes": "forbidden"}),
                       (f"/bookings/{bk['id']}/status", {"status": "CONFIRMED"}),
                       (f"/bookings/{bk['id']}", {"start_time": f"{_day()}T12:00:00+07:00"})]:
        assert (await client.patch(B + path, headers=assigned["h"], json=body)).status_code == 404
    assert (await client.post(f"{B}/bookings/{bk['id']}/cancel", headers=assigned["h"])).status_code == 404
    # Removing assignment revokes the notification and appointment without transferring the profile.
    moved = await client.patch(f"{B}/bookings/{bk['id']}", headers=c["ah"],
        json={"start_time": f"{_day()}T12:00:00+07:00", "staff_id": unrelated["id"]})
    assert moved.status_code == 200
    assert await notes(client, assigned["h"]) == []
    assert (await client.get(f"{B}/bookings/{bk['id']}", headers=assigned["h"])).status_code == 404
    assert (await client.patch(f"{B}/notifications/{assigned_notes[0]['id']}/read", headers=assigned["h"])).status_code == 404
    sent.clear()
    await notices._deliver(uuid.UUID(bk["tenant_id"]),
        [notices.Draft(uuid.UUID(assigned["id"]), "Stale", "Do not deliver")],
        "BOOKING_CREATED", uuid.UUID(bk["id"]))
    assert sent == []


@pytest.mark.asyncio
@pytest.mark.parametrize("as_staff", [False, True])
async def test_counter_single_booking_notifies_customer(client, monkeypatch, as_staff):
    c = await _setup(client, staff_count=1)
    owner = c["staff"][0]
    assert (await client.patch(f"{B}/customers/{c['customer_id']}/assignment", headers=c["ah"],
        json={"assigned_staff_id": owner["id"]})).status_code == 200
    sent = []
    async def capture(sub, payload):
        sent.append(json.loads(payload))
    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", "test")
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", "test")
    monkeypatch.setattr(notices, "_send_one", capture)
    assert (await client.post(f"{B}/notifications/subscribe", headers=c["ch"],
        json={"endpoint": "https://push.example.com/customer", "keys": {"p256dh": "test", "auth": "test"}})).status_code == 201
    bk = await _book(client, owner["h"] if as_staff else c["ah"], f"{_day()}T10:00:00+07:00",
                     [c["s30"]], owner["id"], customer_id=c["customer_id"])
    customer_notes = await notes(client, c["ch"])
    assert len(customer_notes) == 1 and customer_notes[0]["type"] == "BOOKING_CREATED"
    assert customer_notes[0]["title"] == "Bạn có lịch hẹn mới"
    assert len(sent) == 1 and sent[0]["url"] == f"/{c['slug']}/appointments"
    assert sent[0]["booking_id"] == bk["id"]
    assert await notes(client, owner["h"]) == []
    assert await notes(client, c["ah"]) == []


@pytest.mark.asyncio
async def test_counter_batch_retry_notifies_once_per_appointment(client, monkeypatch):
    c = await _setup(client, staff_count=1)
    sent = []
    async def capture(sub, payload):
        sent.append(json.loads(payload))
    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", "test")
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", "test")
    monkeypatch.setattr(notices, "_send_one", capture)
    assert (await client.post(f"{B}/notifications/subscribe", headers=c["ch"],
        json={"endpoint": "https://push.example.com/customer", "keys": {"p256dh": "test", "auth": "test"}})).status_code == 201
    data = {"request_id": str(uuid.uuid4()), "customer_id": c["customer_id"],
            "staff_id": c["staff"][0]["id"], "items": [{"service_id": c["s30"]["id"]}],
            "start_times": [f"{_day()}T10:00:00+07:00", f"{_day()}T12:00:00+07:00"]}
    replies = await asyncio.wait_for(asyncio.gather(*(client.post(f"{B}/bookings/manual-batches", headers=c["ah"], json=data) for _ in range(3))), timeout=30)
    assert all(r.status_code == 201 for r in replies), [r.text for r in replies]
    assert all(r.json() == replies[0].json() for r in replies)
    ids = set(replies[0].json()["booking_ids"])
    rows = await notes(client, c["ch"])
    assert len(rows) == 2 and {r["booking_id"] for r in rows} == ids
    assert len(sent) == 2 and {r["booking_id"] for r in sent} == ids
    # GET recovery and sequential retry do not create another notification.
    assert (await client.get(f"{B}/bookings/manual-batches/{data['request_id']}", headers=c["ah"])).status_code == 200
    assert (await client.post(f"{B}/bookings/manual-batches", headers=c["ah"], json=data)).status_code == 201
    assert len(await notes(client, c["ch"])) == 2 and len(sent) == 2


@pytest.mark.asyncio
async def test_failed_counter_batch_has_no_customer_notification(client):
    c = await _setup(client, staff_count=1)
    data = {"request_id": str(uuid.uuid4()), "customer_id": c["customer_id"],
            "staff_id": c["staff"][0]["id"], "items": [{"service_id": c["s60"]["id"]}],
            "start_times": [f"{_day()}T10:00:00+07:00", f"{_day()}T10:15:00+07:00"]}
    response = await client.post(f"{B}/bookings/manual-batches", headers=c["ah"], json=data)
    assert response.status_code == 409
    assert await notes(client, c["ch"]) == []
    assert (await client.get(f"{B}/bookings", headers=c["ah"])).json() == []
