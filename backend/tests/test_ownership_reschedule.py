import asyncio
from datetime import datetime, timedelta, timezone
import pytest
from app.schemas.booking import BookingUpdate
from app.services.booking_service import ensure_aware
from pydantic import ValidationError
from tests.test_sprint4_reports_notifications import B, _setup, _book, _day


def test_edit_schema_rejects_customer_items_and_timezone_normalizes():
    with pytest.raises(ValidationError):
        BookingUpdate(start_time="2030-01-01T10:00:00+07:00", customer_id="forged")
    value = ensure_aware(datetime(2030, 1, 1, 10))
    assert value.utcoffset() == timedelta(hours=7)


@pytest.mark.asyncio
async def test_fixed_owner_permissions_and_admin_transfer(client):
    c = await _setup(client)
    a, b = c["staff"]
    pkg = (await client.post(f"{B}/customer-packages", headers=c["ah"],
          json={"customer_id": c["customer_id"], "service_id": c["pkg_svc"]["id"]})).json()
    booking = await _book(client, c["ch"], f"{_day()}T10:00:00+07:00", [c["pkg_svc"]], a["id"], package_id=pkg["id"])
    async def denied(headers):
        assert (await client.get(f"{B}/customers", headers=headers)).json() == []
        assert (await client.get(f"{B}/bookings", headers=headers)).json() == []
        assert (await client.get(f"{B}/customer-packages", headers=headers)).json() == []
        for path in (f"/bookings/{booking['id']}", f"/customers/{c['customer_id']}/packages"):
            assert (await client.get(B+path, headers=headers)).status_code == 404
        for path, payload in (
            (f"/customers/{c['customer_id']}", {"notes": "forbidden"}),
            (f"/bookings/{booking['id']}/status", {"status": "CONFIRMED"}),
            (f"/bookings/{booking['id']}", {"start_time": f"{_day()}T15:00:00+07:00"})):
            assert (await client.patch(B+path, headers=headers, json=payload)).status_code == 404
        assert (await client.post(f"{B}/bookings/{booking['id']}/cancel", headers=headers)).status_code == 404
        assert (await client.post(f"{B}/customer-packages", headers=headers,
                json={"customer_id": c["customer_id"], "service_id": c["pkg_svc"]["id"]})).status_code == 404
        assert (await client.get(f"{B}/notifications", headers=headers)).json()["items"] == []
    await denied(b["h"])
    r = await client.patch(f"{B}/customers/{c['customer_id']}", headers=a["h"], json={"notes": "owner notes"})
    assert r.status_code == 200
    assert r.json()["assigned_staff_id"] == a["id"]
    assert (await client.patch(f"{B}/customers/{c['customer_id']}/assignment", headers=a["h"],
            json={"assigned_staff_id": b["id"]})).status_code == 403
    r = await client.patch(f"{B}/customers/{c['customer_id']}/assignment", headers=c["ah"],
                           json={"assigned_staff_id": b["id"]})
    assert r.status_code == 200
    await denied(a["h"])
    assert (await client.get(f"{B}/bookings/{booking['id']}", headers=b["h"])).status_code == 200
    # A later appointment with A must not silently transfer the permanent owner back.
    await _book(client, c["ch"], f"{_day()}T16:00:00+07:00", [c["s30"]], a["id"])
    rows = (await client.get(f"{B}/customers", headers=b["h"])).json()
    assert rows[0]["assigned_staff_id"] == b["id"]


@pytest.mark.asyncio
async def test_transfer_rejects_foreign_tenant_and_nonstaff(client):
    c, other = await _setup(client), await _setup(client)
    for wrong in (other["staff"][0]["id"], c["customer_id"], c["admin_id"]):
        r = await client.patch(f"{B}/customers/{c['customer_id']}/assignment", headers=c["ah"],
                               json={"assigned_staff_id": wrong})
        assert r.status_code == 404
    assert (await client.get(f"{B}/customers", headers=c["staff"][0]["h"])).json() == []


@pytest.mark.asyncio
async def test_reschedule_preserves_identity_price_status_and_reservation(client):
    c = await _setup(client)
    pkg = (await client.post(f"{B}/customer-packages", headers=c["ah"],
          json={"customer_id": c["customer_id"], "service_id": c["pkg_svc"]["id"]})).json()
    old = await _book(client, c["ch"], f"{_day()}T10:00:00+07:00", [c["pkg_svc"]], c["staff"][0]["id"], package_id=pkg["id"])
    await client.patch(f"{B}/bookings/{old['id']}/status", headers=c["ah"], json={"status": "CONFIRMED"})
    await client.patch(f"{B}/services/{c['pkg_svc']['id']}", headers=c["ah"], json={"price": 999999, "duration_minutes": 120})
    r = await client.patch(f"{B}/bookings/{old['id']}", headers=c["ch"],
                           json={"start_time": f"{_day()}T14:00:00+07:00", "staff_id": c["staff"][1]["id"], "note": "moved"})
    assert r.status_code == 200, r.text
    new = r.json()
    for field in ("id", "items", "total_price", "total_duration_minutes", "customer_id"):
        assert new[field] == old[field]
    assert new["status"] == "CONFIRMED" and new["note"] == "moved"
    cards = (await client.get(f"{B}/customer-packages/me", headers=c["ch"])).json()
    assert (cards[0]["used_sessions"], cards[0]["reserved_sessions"]) == (0, 1)


@pytest.mark.asyncio
async def test_reschedule_conflict_rolls_back_and_parallel_edits_cannot_overlap(client):
    c = await _setup(client, staff_count=1)
    staff = c["staff"][0]["id"]
    a = await _book(client, c["ch"], f"{_day()}T09:00:00+07:00", [c["s30"]], staff)
    b = await _book(client, c["ch"], f"{_day()}T11:00:00+07:00", [c["s30"]], staff)
    r = await client.patch(f"{B}/bookings/{a['id']}", headers=c["ah"],
                           json={"start_time": b["start_time"], "staff_id": staff})
    assert r.status_code == 409
    unchanged = (await client.get(f"{B}/bookings/{a['id']}", headers=c["ah"])).json()
    assert unchanged == a
    results = await asyncio.wait_for(asyncio.gather(*[
        client.patch(f"{B}/bookings/{bk['id']}", headers=c["ah"],
                     json={"start_time": f"{_day()}T15:00:00+07:00", "staff_id": staff})
        for bk in (a, b)]), timeout=15)
    assert sorted(r.status_code for r in results) == [200, 409]


@pytest.mark.asyncio
async def test_reschedule_rejects_past_terminal_and_foreign_booking(client):
    c, other = await _setup(client), await _setup(client)
    bk = await _book(client, c["ch"], f"{_day()}T09:00:00+07:00", [c["s30"]])
    url = f"{B}/bookings/{bk['id']}"
    assert (await client.patch(url, headers=other["ah"], json={"start_time": f"{_day()}T12:00:00+07:00"})).status_code == 404
    assert (await client.patch(url, headers=c["ah"], json={"start_time": (datetime.now(timezone.utc)-timedelta(days=1)).isoformat()})).status_code == 422
    await client.post(url+"/cancel", headers=c["ah"])
    assert (await client.patch(url, headers=c["ah"], json={"start_time": f"{_day()}T12:00:00+07:00"})).status_code == 409


@pytest.mark.asyncio
async def test_different_customers_reschedule_into_same_staff_slot(client):
    from tests.conftest import unique_phone
    c = await _setup(client, staff_count=1)
    other = (await client.post(f"{B}/auth/register", headers={"X-Tenant-Slug": c["slug"]},
             json={"full_name": "Other", "phone_number": unique_phone(), "password": "secret123"})).json()
    other_headers = {"Authorization": "Bearer " + other["access_token"]}
    a = await _book(client, c["ch"], f"{_day()}T09:00:00+07:00", [c["s30"]])
    b = await _book(client, other_headers, f"{_day()}T11:00:00+07:00", [c["s30"]])
    responses = await asyncio.wait_for(asyncio.gather(*[
        client.patch(f"{B}/bookings/{bk['id']}", headers=c["ah"],
                     json={"start_time": f"{_day()}T15:00:00+07:00"})
        for bk in (a, b)]), 15)
    assert sorted(r.status_code for r in responses) == [200, 409]
    loser = (a, b)[next(i for i, r in enumerate(responses) if r.status_code == 409)]
    assert (await client.get(f"{B}/bookings/{loser['id']}", headers=c["ah"])).json() == loser


@pytest.mark.asyncio
async def test_reschedule_rejects_expiry_at_new_date_and_customer_cutoff(client, monkeypatch):
    from app.services import booking_service as svc
    c = await _setup(client, staff_count=1)
    pkg = (await client.post(f"{B}/customer-packages", headers=c["ah"],
          json={"customer_id": c["customer_id"], "service_id": c["pkg_svc"]["id"],
                "expiry_date": f"{_day(4)}T00:00:00+07:00"})).json()
    old = await _book(client, c["ch"], f"{_day()}T10:00:00+07:00", [c["pkg_svc"]],
                      c["staff"][0]["id"], package_id=pkg["id"])
    url = f"{B}/bookings/{old['id']}"
    assert (await client.patch(url, headers=c["ah"],
            json={"start_time": f"{_day(5)}T10:00:00+07:00"})).status_code == 422
    fixed = datetime.fromisoformat(old["start_time"]) - timedelta(hours=1)
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)
    monkeypatch.setattr(svc, "datetime", FixedDateTime)
    assert (await client.patch(url, headers=c["ch"],
            json={"start_time": f"{_day()}T13:00:00+07:00"})).status_code == 409
    assert (await client.get(url, headers=c["ah"])).json() == old


@pytest.mark.asyncio
async def test_stale_notification_draft_does_not_push_to_previous_owner(client, monkeypatch):
    import uuid
    from app.core.config import settings
    from app.services import notification_service as notices
    c = await _setup(client)
    a, b = c["staff"]
    bk = await _book(client, c["ch"], f"{_day()}T09:00:00+07:00", [c["s30"]], a["id"])
    response = await client.post(f"{B}/notifications/subscribe", headers=a["h"],
        json={"endpoint": "https://push.example.com/" + uuid.uuid4().hex, "keys": {"p256dh": "test", "auth": "test"}})
    assert response.status_code == 201
    assert (await client.patch(f"{B}/customers/{c['customer_id']}/assignment", headers=c["ah"],
            json={"assigned_staff_id": b["id"]})).status_code == 200
    sent = []
    async def capture(sub, payload):
        sent.append(payload)
    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", "test")
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", "test")
    monkeypatch.setattr(notices, "_send_one", capture)
    await notices._deliver(uuid.UUID(bk["tenant_id"]),
        [notices.Draft(uuid.UUID(a["id"]), "Sensitive", "Customer information")],
        "BOOKING_CREATED", uuid.UUID(bk["id"]))
    assert sent == []
