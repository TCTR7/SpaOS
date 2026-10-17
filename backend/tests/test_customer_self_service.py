import pytest

from tests.test_sprint4_reports_notifications import B, _setup, _book, _day, _h
from tests.conftest import unique_phone


@pytest.mark.asyncio
async def test_my_packages_isolation_and_permissions(client):
    a, b = await _setup(client, staff_count=1), await _setup(client, staff_count=1)
    other = await client.post(f"{B}/auth/register", headers={"X-Tenant-Slug": a["slug"]},
                              json={"full_name": "Other", "phone_number": unique_phone(), "password": "secret123"})
    ids = []
    for ctx, customer in ((a, a["customer_id"]), (a, other.json()["user"]["id"]), (b, b["customer_id"])):
        r = await client.post(f"{B}/customer-packages", headers=ctx["ah"],
                             json={"customer_id": customer, "service_id": ctx["pkg_svc"]["id"]})
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    r = await client.get(f"{B}/customer-packages/me", headers=a["ch"],
                         params={"customer_id": b["customer_id"], "tenant_id": b["admin_id"]})
    assert r.status_code == 200, r.text
    assert [p["id"] for p in r.json()] == [ids[0]]
    r = await client.get(f"{B}/customer-packages/me", headers=_h(other.json()["access_token"]))
    assert [p["id"] for p in r.json()] == [ids[1]]
    assert (await client.get(f"{B}/customer-packages/me")).status_code == 401
    for headers in (a["ah"], a["staff"][0]["h"]):
        assert (await client.get(f"{B}/customer-packages/me", headers=headers)).status_code == 403
    assert (await client.get(f"{B}/customer-packages", headers=a["ch"])).status_code == 403


@pytest.mark.asyncio
async def test_my_packages_reservations_completion_and_cancel(client):
    ctx = await _setup(client, staff_count=1)
    r = await client.post(f"{B}/customer-packages", headers=ctx["ah"],
                         json={"customer_id": ctx["customer_id"], "service_id": ctx["pkg_svc"]["id"]})
    package = r.json()

    async def counts(used, held):
        response = await client.get(f"{B}/customer-packages/me", headers=ctx["ch"])
        assert response.status_code == 200, response.text
        p = response.json()[0]
        assert (p["used_sessions"], p["reserved_sessions"], p["available_sessions"]) == (used, held, 5-used-held)

    await counts(0, 0)
    booking = await _book(client, ctx["ch"], f"{_day()}T10:00:00+07:00",
                          [ctx["pkg_svc"]], ctx["staff"][0]["id"], package_id=package["id"])
    await counts(0, 1)
    for status in ("CONFIRMED", "IN_PROGRESS"):
        r = await client.patch(f"{B}/bookings/{booking['id']}/status", headers=ctx["ah"], json={"status": status})
        assert r.status_code == 200, r.text
        await counts(0, 1)
    for _ in range(2):
        r = await client.patch(f"{B}/bookings/{booking['id']}/status", headers=ctx["ah"], json={"status": "COMPLETED"})
        assert r.status_code == 200, r.text
        await counts(1, 0)
    booking = await _book(client, ctx["ch"], f"{_day()}T14:00:00+07:00",
                          [ctx["pkg_svc"]], ctx["staff"][0]["id"], package_id=package["id"])
    await counts(1, 1)
    assert (await client.post(f"{B}/bookings/{booking['id']}/cancel", headers=ctx["ch"])).status_code == 200
    await counts(1, 0)
