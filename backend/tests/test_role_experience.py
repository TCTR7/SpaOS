import asyncio
import base64
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select, func, text
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.models import Notification, NotificationEvent, NotificationDispatch, RecoveryGrant
from app.services import notification_service as notices
from app.services.notification_queue import drain_events, drain_push
from app.core.config import settings
from tests.test_sprint4_reports_notifications import B, _setup, _book, _day


@pytest.mark.asyncio
async def test_contact_logo_and_setup_are_scoped(client):
    c, other = await _setup(client, staff_count=1), await _setup(client, staff_count=1)
    response = await client.patch(B + "/tenants/me", headers=c["ah"], json={"address": "123 Nguyen Trai", "contact_phone": "0901234567"})
    assert response.status_code == 200
    public = (await client.get(B + "/public/tenants/" + c["slug"])).json()
    assert public["address"] == "123 Nguyen Trai" and public["contact_phone"] == "0901234567"
    assert (await client.get(B + "/tenants/me/setup", headers=c["staff"][0]["h"])).status_code == 403
    setup = (await client.get(B + "/tenants/me/setup", headers=c["ah"])).json()
    assert setup["services"] == 3 and setup["staff_with_hours"] == 1 and setup["contact_ready"] is True
    png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    uploaded = await client.patch(B + "/tenants/me", headers=c["ah"], json={"logo_data": png})
    assert uploaded.status_code == 200, uploaded.text
    logo = await client.get(uploaded.json()["logo_url"])
    assert logo.status_code == 200 and logo.headers["content-type"] == "image/png" and logo.content == base64.b64decode(png)
    assert (await client.get(B + "/public/tenants/" + other["slug"] + "/logo")).status_code == 404
    assert (await client.patch(B + "/tenants/me", headers=c["ah"], json={"name": "Should rollback", "logo_data": base64.b64encode(b"<svg></svg>").decode()})).status_code == 422
    assert (await client.get(B + "/tenants/me", headers=c["ah"])).json()["name"] != "Should rollback"


@pytest.mark.asyncio
async def test_recovery_link_is_verified_single_use_branch_scoped_and_revokes_old_sessions(client):
    c, other = await _setup(client, staff_count=1), await _setup(client, staff_count=1)
    endpoint = B + "/customers/" + c["customer_id"] + "/recovery-link"
    body = {"current_password": "secret123", "identity_verified": True}
    assert (await client.post(endpoint, headers=c["staff"][0]["h"], json=body)).status_code == 403
    assert (await client.post(endpoint, headers=other["ah"], json=body)).status_code == 404
    assert (await client.post(endpoint, headers=c["ah"], json={**body, "identity_verified": False})).status_code == 422
    assert (await client.post(endpoint, headers=c["ah"], json={**body, "current_password": "wrong"})).status_code == 403
    first = (await client.post(endpoint, headers=c["ah"], json=body)).json()["token"]
    second = (await client.post(endpoint, headers=c["ah"], json=body)).json()["token"]
    payload = {"token": second, "password": "new-secret123"}
    assert (await client.post(B + "/auth/recovery", headers={"X-Tenant-Slug": other["slug"]}, json=payload)).status_code == 400
    assert (await client.post(B + "/auth/recovery", headers={"X-Tenant-Slug": c["slug"]}, json={**payload, "token": first})).status_code == 400
    results = await asyncio.gather(*(client.post(B + "/auth/recovery", headers={"X-Tenant-Slug": c["slug"]}, json=payload) for _ in range(2)))
    assert sorted(r.status_code for r in results) == [200, 400]
    assert (await client.get(B + "/auth/me", headers=c["ch"])).status_code == 401
    assert (await client.get(B + "/bookings/available-slots", headers=c["ch"], params={"date": str(_day()), "service_ids": c["s30"]["id"]})).status_code == 401
    async with AsyncSessionLocal() as db:
        await set_tenant_context(db, uuid.UUID((await client.get(B + "/auth/me", headers=c["ah"])).json()["tenant"]["id"]))
        grant = (await db.execute(select(RecoveryGrant))).scalar_one()
        assert second not in grant.token_hash and grant.consumed_at is not None


@pytest.mark.asyncio
async def test_shared_staff_account_updates_all_branches_and_revokes_tokens(client):
    c = await _setup(client, staff_count=1)
    staff = (await client.get(B + "/staff", headers=c["ah"])).json()[0]
    branch = await client.post(B + "/branches", headers=c["ah"], json={"name": "Second branch"})
    assert branch.status_code == 201
    branch_id = branch.json()["tenant"]["id"]
    granted = await client.post(B + "/branches/" + branch_id + "/staff-access", headers=c["ah"], json={"source_staff_id": staff["id"]})
    assert granted.status_code == 201
    old_other = await client.post(B + "/branches/" + branch_id + "/switch", headers=c["staff"][0]["h"])
    assert old_other.status_code == 200
    result = await client.patch(B + "/staff/" + staff["id"] + "/account", headers=c["ah"], json={"current_password": "secret123", "password": "new-secret123"})
    assert result.status_code == 200, result.text
    for headers in (c["staff"][0]["h"], {"Authorization": "Bearer " + old_other.json()["access_token"]}):
        assert (await client.get(B + "/auth/me", headers=headers)).status_code == 401
    login = await client.post(B + "/auth/login", json={"phone_number": staff["phone_number"], "password": "new-secret123"})
    assert login.status_code == 200
    assert len((await client.get(B + "/branches", headers={"Authorization": "Bearer " + login.json()["access_token"]})).json()) == 2


@pytest.mark.asyncio
async def test_day_override_blocks_availability_and_preserves_existing_bookings(client):
    c = await _setup(client, staff_count=1)
    staff = c["staff"][0]
    endpoint = B + "/staff/" + staff["id"] + "/date-overrides"
    body = {"day": str(_day()), "is_day_off": True}
    assert (await client.put(endpoint, headers=staff["h"], json=body)).status_code == 403
    assert (await client.put(endpoint, headers=c["ah"], json=body)).status_code == 200
    params = {"date": str(_day()), "service_ids": c["s30"]["id"], "staff_id": staff["id"]}
    assert (await client.get(B + "/bookings/available-slots", headers=c["ch"], params=params)).json()["slots"] == []
    own = await client.get(B + "/staff/me/work-hours", headers=staff["h"])
    assert own.status_code == 200 and len(own.json()["overrides"]) == 1
    assert (await client.delete(endpoint + "/" + str(_day()), headers=c["ah"])).status_code == 200
    booking = await _book(client, c["ch"], f"{_day()}T10:00:00+07:00", [c["s30"]], staff["id"])
    assert (await client.put(endpoint, headers=c["ah"], json=body)).status_code == 409
    assert (await client.get(B + "/bookings/" + booking["id"], headers=c["ah"])).json()["status"] == "PENDING"
    assert (await client.get(endpoint, headers=c["ah"])).json() == []


@pytest.mark.asyncio
async def test_handover_read_is_limited_to_assigned_and_never_exposed_to_customer(client):
    c = await _setup(client, staff_count=3)
    owner, assigned, other = c["staff"]
    await client.patch(B + "/customers/" + c["customer_id"] + "/assignment", headers=c["ah"], json={"assigned_staff_id": owner["id"]})
    booking = await _book(client, c["ch"], f"{_day()}T10:00:00+07:00", [c["s30"]], assigned["id"])
    endpoint = B + "/bookings/" + booking["id"] + "/handover"
    assert (await client.put(endpoint, headers=c["ah"], json={"note": "Confirmed instructions for this appointment"})).status_code == 200
    assert (await client.get(endpoint, headers=assigned["h"])).json()["note"].startswith("Confirmed")
    assert (await client.put(endpoint, headers=assigned["h"], json={"note": "no"})).status_code == 404
    assert (await client.get(endpoint, headers=other["h"])).status_code == 404
    assert (await client.get(endpoint, headers=c["ch"])).status_code == 403
    assert "handover" not in (await client.get(B + "/bookings/" + booking["id"], headers=c["ch"])).json()


@pytest.mark.asyncio
async def test_customer_booking_receipt_replays_once_and_rejects_changed_payload(client):
    c = await _setup(client, staff_count=1)
    request_id = str(uuid.uuid4())
    body = {"request_id": request_id, "start_time": f"{_day()}T10:00:00+07:00", "staff_id": c["staff"][0]["id"], "items": [{"service_id": c["s30"]["id"]}]}
    results = await asyncio.gather(*(client.post(B + "/booking-requests", headers=c["ch"], json=body) for _ in range(3)))
    assert all(r.status_code == 201 for r in results), [r.status_code for r in results]
    assert len({r.json()["id"] for r in results}) == 1
    assert (await client.get(B + "/booking-requests/" + request_id, headers=c["ch"])).json()["id"] == results[0].json()["id"]
    assert (await client.post(B + "/booking-requests", headers=c["ch"], json={**body, "note": "changed"})).status_code == 409
    assert (await client.get(B + "/booking-requests/" + request_id, headers=c["ah"])).status_code == 403
    assert len((await client.get(B + "/bookings", headers=c["ch"])).json()) == 1


@pytest.mark.asyncio
async def test_package_history_and_reservations_are_consistent(client):
    c, other = await _setup(client, staff_count=1), await _setup(client, staff_count=1)
    package = (await client.post(B + "/customer-packages", headers=c["ah"], json={"customer_id": c["customer_id"], "service_id": c["pkg_svc"]["id"]})).json()
    booking = await _book(client, c["ch"], f"{_day()}T10:00:00+07:00", [c["pkg_svc"]], c["staff"][0]["id"], package_id=package["id"])
    customer = (await client.get(B + "/customer-packages/me", headers=c["ch"])).json()[0]
    admin = (await client.get(B + "/customers/" + c["customer_id"] + "/packages", headers=c["ah"])).json()[0]
    for key in ("used_sessions", "reserved_sessions", "available_sessions"): assert customer[key] == admin[key]
    history = B + "/customer-packages/" + package["id"] + "/history"
    assert (await client.get(history, headers=c["ch"])).json()[0]["booking_id"] == booking["id"]
    assert (await client.get(history, headers=other["ch"])).status_code == 404
    assert (await client.get(history, headers=c["staff"][0]["h"])).status_code == 200


@pytest.mark.asyncio
async def test_durable_event_recovers_after_failed_background_and_dedupes(client, monkeypatch):
    c = await _setup(client, staff_count=1)
    original = notices._deliver
    async def fail(*args, **kwargs): raise RuntimeError("worker stopped")
    monkeypatch.setattr(notices, "_deliver", fail)
    booking = await _book(client, c["ch"], f"{_day()}T10:00:00+07:00", [c["s30"]], c["staff"][0]["id"])
    tenant_id = uuid.UUID(booking["tenant_id"])
    async with AsyncSessionLocal() as db:
        await set_tenant_context(db, tenant_id)
        event = (await db.execute(select(NotificationEvent).where(NotificationEvent.tenant_id == tenant_id))).scalar_one()
        assert event.processed_at is None and event.attempts == 1
        event.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await db.commit()
    monkeypatch.setattr(notices, "_deliver", original)
    await drain_events(tenant_id)
    first = (await client.get(B + "/notifications", headers=c["ah"])).json()["items"]
    assert len(first) == 1
    async with AsyncSessionLocal() as db:
        await set_tenant_context(db, tenant_id)
        event = (await db.execute(select(NotificationEvent).where(NotificationEvent.tenant_id == tenant_id))).scalar_one()
        event.processed_at = None
        await db.commit()
    await drain_events(tenant_id)
    assert len((await client.get(B + "/notifications", headers=c["ah"])).json()["items"]) == 1


@pytest.mark.asyncio
async def test_push_retry_survives_failure_without_duplicate_in_app(client, monkeypatch):
    c = await _setup(client, staff_count=1)
    await client.post(B + "/notifications/subscribe", headers=c["ah"], json={"endpoint": "https://push.example.test/retry", "keys": {"p256dh": "qa", "auth": "qa"}})
    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", "qa")
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", "qa")
    sent = []
    async def send(sub, payload): sent.append(payload); return 503 if len(sent) == 1 else None
    monkeypatch.setattr(notices, "_send_one", send)
    booking = await _book(client, c["ch"], f"{_day()}T10:00:00+07:00", [c["s30"]], c["staff"][0]["id"])
    tenant_id = uuid.UUID(booking["tenant_id"])
    async with AsyncSessionLocal() as db:
        await set_tenant_context(db, tenant_id)
        job = (await db.execute(select(NotificationDispatch).where(NotificationDispatch.tenant_id == tenant_id))).scalar_one()
        assert job.delivered_at is None
        attempts = job.attempts
        job.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await db.commit()
    if attempts == 0:
        # The initial background drain may precede the DB default due timestamp.
        # Drive the first attempt explicitly instead of relying on clock timing.
        await drain_push(tenant_id)
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tenant_id)
            job = (await db.execute(select(NotificationDispatch).where(NotificationDispatch.tenant_id == tenant_id))).scalar_one()
            assert job.attempts == 1 and job.delivered_at is None
            job.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            await db.commit()
    await drain_push(tenant_id)
    assert len(sent) == 2
    assert len((await client.get(B + "/notifications", headers=c["ah"])).json()["items"]) == 1


@pytest.mark.asyncio
async def test_expired_recovery_and_profile_field_whitelist(client):
    c = await _setup(client, staff_count=1)
    result = await client.post(B + "/customers/" + c["customer_id"] + "/recovery-link", headers=c["ah"],
        json={"current_password": "secret123", "identity_verified": True})
    token = result.json()["token"]
    tenant_id = uuid.UUID((await client.get(B + "/auth/me", headers=c["ah"])).json()["tenant"]["id"])
    async with AsyncSessionLocal() as db:
        await set_tenant_context(db, tenant_id)
        grant = (await db.execute(select(RecoveryGrant).where(RecoveryGrant.tenant_id == tenant_id))).scalar_one()
        grant.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await db.commit()
    assert (await client.post(B + "/auth/recovery", headers={"X-Tenant-Slug": c["slug"]},
        json={"token": token, "password": "another-secret"})).status_code == 400
    for extra in ({"phone_number": "0901234567"}, {"role": "ADMIN"}, {"tenant_id": str(uuid.uuid4())}):
        assert (await client.patch(B + "/account/profile", headers=c["ch"], json={"full_name": "Updated", **extra})).status_code == 422
    response = await client.patch(B + "/account/profile", headers=c["ch"], json={"full_name": " Updated "})
    assert response.status_code == 200 and response.json()["full_name"] == "Updated"


@pytest.mark.asyncio
async def test_own_password_change_validates_current_and_revokes_previous_token(client):
    c = await _setup(client, staff_count=1)
    body = {"current_password": "wrong", "password": "changed-secret123"}
    assert (await client.patch(B + "/account/credentials", headers=c["ch"], json=body)).status_code == 403
    assert (await client.get(B + "/auth/me", headers=c["ch"])).status_code == 200
    changed = await client.patch(B + "/account/credentials", headers=c["ch"], json={**body, "current_password": "secret123"})
    assert changed.status_code == 200
    assert (await client.get(B + "/auth/me", headers=c["ch"])).status_code == 401
    fresh = {"Authorization": "Bearer " + changed.json()["access_token"]}
    assert (await client.get(B + "/auth/me", headers=fresh)).status_code == 200
    assert (await client.patch(B + "/account/credentials", headers=fresh, json={**body, "current_password": "secret123"})).status_code == 403


@pytest.mark.asyncio
async def test_new_business_tables_force_rls(client):
    c = await _setup(client, staff_count=1)
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(text("SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname IN ('staff_date_overrides','tenant_logos','recovery_grants','booking_requests','booking_handovers','notification_events','notification_dispatches')"))).all()
    assert len(rows) == 7 and all(row.relrowsecurity and row.relforcerowsecurity for row in rows)


@pytest.mark.asyncio
async def test_owner_self_change_covers_all_branches_and_legacy_staff_reset_revokes(client):
    c = await _setup(client, staff_count=1)
    branch = (await client.post(B + "/branches", headers=c["ah"], json={"name": "Owner second branch"})).json()
    old_other = (await client.post(B + "/branches/" + branch["tenant"]["id"] + "/switch", headers=c["ah"])).json()["access_token"]
    changed = await client.patch(B + "/account/credentials", headers=c["ah"], json={"current_password": "secret123", "password": "owner-secret123"})
    assert changed.status_code == 200
    fresh = {"Authorization": "Bearer " + changed.json()["access_token"]}
    assert (await client.get(B + "/auth/me", headers=fresh)).status_code == 200
    for headers in (c["ah"], {"Authorization": "Bearer " + old_other}):
        assert (await client.get(B + "/auth/me", headers=headers)).status_code == 401
    reset = await client.patch(B + "/staff/" + c["staff"][0]["id"], headers=fresh, json={"password": "staff-secret123"})
    assert reset.status_code == 200
    assert (await client.get(B + "/auth/me", headers=c["staff"][0]["h"])).status_code == 401
