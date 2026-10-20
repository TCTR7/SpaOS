import pytest
from tests.test_sprint4_reports_notifications import B, _setup, _book, _day


@pytest.mark.asyncio
async def test_snapshot_self_exclusion_and_note_keeps_staff(client):
    c = await _setup(client)
    booking = await _book(client, c["ch"], f"{_day()}T10:07:00+07:00", [c["s30"]], c["staff"][1]["id"])
    await client.patch(f"{B}/services/{c['s30']['id']}", headers=c["ah"], json={"duration_minutes": 120, "is_active": False})
    path = f"{B}/bookings/{booking['id']}/available-slots"
    response = await client.get(path, headers=c["ch"], params={"date": str(_day()), "staff_id": c["staff"][1]["id"]})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total_duration_minutes"] == 30
    assert any(row["start_time"].startswith(str(_day()) + "T10:07") for row in data["slots"])
    result = await client.patch(f"{B}/bookings/{booking['id']}", headers=c["ah"], json={"start_time": booking["start_time"], "note": "Note only"})
    assert result.status_code == 200, result.text
    value = result.json()
    for field in ("id", "staff_id", "start_time", "end_time", "items", "total_price", "total_duration_minutes"):
        assert value[field] == booking[field]
    assert value["note"] == "Note only"


@pytest.mark.asyncio
async def test_exclusion_requires_owner_and_does_not_remove_other_bookings(client):
    c, other = await _setup(client), await _setup(client)
    a = c["staff"][0]
    booking = await _book(client, c["ch"], f"{_day()}T10:00:00+07:00", [c["s30"]], a["id"])
    await _book(client, c["ch"], f"{_day()}T11:00:00+07:00", [c["s30"]], a["id"])
    path = f"{B}/bookings/{booking['id']}/available-slots"
    params = {"date": str(_day()), "staff_id": a["id"]}
    for headers in (other["ah"], c["staff"][1]["h"]):
        assert (await client.get(path, headers=headers, params=params)).status_code == 404
    response = await client.get(path, headers=c["ch"], params=params)
    starts = [row["start_time"] for row in response.json()["slots"]]
    assert any("T10:00:" in start for start in starts)
    assert not any("T11:00:" in start or "T10:45:" in start for start in starts)
    await client.patch(f"{B}/bookings/{booking['id']}/status", headers=c["ah"], json={"status": "CANCELLED"})
    assert (await client.get(path, headers=c["ch"], params=params)).status_code == 409


@pytest.mark.asyncio
async def test_suggestion_does_not_bypass_patch_conflict_or_package_reservation(client):
    c = await _setup(client)
    pkg = (await client.post(f"{B}/customer-packages", headers=c["ah"], json={"customer_id": c["customer_id"], "service_id": c["pkg_svc"]["id"]})).json()
    booking = await _book(client, c["ch"], f"{_day()}T10:00:00+07:00", [c["pkg_svc"]], c["staff"][0]["id"], package_id=pkg["id"])
    response = await client.get(f"{B}/bookings/{booking['id']}/available-slots", headers=c["ch"], params={"date": str(_day()), "staff_id": c["staff"][0]["id"]})
    assert response.status_code == 200
    await _book(client, c["ch"], f"{_day()}T15:00:00+07:00", [c["s30"]], c["staff"][0]["id"])
    result = await client.patch(f"{B}/bookings/{booking['id']}", headers=c["ch"], json={"start_time": f"{_day()}T15:00:00+07:00", "staff_id": c["staff"][0]["id"]})
    assert result.status_code == 409
    current = (await client.get(f"{B}/bookings/{booking['id']}", headers=c["ch"])).json()
    assert current["start_time"] == booking["start_time"] and current["items"] == booking["items"]
    package = (await client.get(f"{B}/customer-packages/me", headers=c["ch"])).json()[0]
    assert package["reserved_sessions"] == 1 and package["used_sessions"] == 0
