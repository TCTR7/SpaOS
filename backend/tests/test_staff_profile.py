import base64
import io
import struct
import zlib

import pytest

from tests.conftest import unique_phone
from tests.test_booking_concurrency import B, _setup_spa, _day


def _png(width: int = 2, height: int = 2) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _jpeg(width: int = 8, height: int = 8) -> bytes:
    sof = b"\xff\xc0" + struct.pack(">HBHHB", 11, 8, height, width, 1) + b"\x01\x11\x00"
    return b"\xff\xd8" + sof + b"\xff\xda\x00\x02" + b"\x00\x01\x02" + b"\xff\xd9"


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


@pytest.mark.asyncio
async def test_staff_profile_fields_skills_and_photo(client):
    ctx = await _setup_spa(client)
    ah, sid = ctx["ah"], ctx["staff"][0]

    r = await client.patch(f"{B}/staff/{sid}", headers=ah, json={
        "job_title": "Chuyên viên da", "bio": "Yêu nghề", "experience_years": 5, "experience_detail": "Từng làm ở spa A"})
    assert r.status_code == 200, r.text
    assert r.json()["job_title"] == "Chuyên viên da" and r.json()["experience_years"] == 5
    assert (await client.patch(f"{B}/staff/{sid}", headers=ah, json={"bio": None})).json()["bio"] is None
    assert (await client.patch(f"{B}/staff/{sid}", headers=ah, json={"experience_years": 99})).status_code == 422

    r = await client.put(f"{B}/staff/{sid}/skills", headers=ah, json={"service_ids": [ctx["s60"]["id"]]})
    assert r.status_code == 200 and r.json()["skill_service_ids"] == [ctx["s60"]["id"]]
    listed = (await client.get(f"{B}/staff", headers=ah)).json()
    assert listed[0]["skill_service_ids"] == [ctx["s60"]["id"]]
    bad = await client.put(f"{B}/staff/{sid}/skills", headers=ah, json={"service_ids": ["00000000-0000-0000-0000-000000000001"]})
    assert bad.status_code == 422

    for data, kind in ((_png(), "image/png"), (_jpeg(), "image/jpeg")):
        r = await client.post(f"{B}/staff/{sid}/photo", headers=ah, json={"data": _b64(data)})
        assert r.status_code == 200, r.text
        url = r.json()["photo_url"]
        assert url.startswith(f"/api/v1/public/tenants/{ctx['slug']}/staff/{sid}/photo")
        got = await client.get(url)
        assert got.status_code == 200 and got.headers["content-type"] == kind and got.content == data
    assert (await client.post(f"{B}/staff/{sid}/photo", headers=ah, json={"data": _b64(b"not an image")})).status_code == 422
    assert (await client.post(f"{B}/staff/{sid}/photo", headers=ah, json={"data": "!!"})).status_code == 422
    r = await client.delete(f"{B}/staff/{sid}/photo", headers=ah)
    assert r.status_code == 200 and r.json()["photo_url"] is None
    assert (await client.get(f"/api/v1/public/tenants/{ctx['slug']}/staff/{sid}/photo")).status_code == 404


@pytest.mark.asyncio
async def test_staff_profile_is_admin_only_and_tenant_scoped(client):
    one, two = await _setup_spa(client), await _setup_spa(client)
    sid = one["staff"][0]
    body = {"service_ids": [one["s60"]["id"]]}
    assert (await client.put(f"{B}/staff/{sid}/skills", headers=one["ch"], json=body)).status_code == 403
    assert (await client.put(f"{B}/staff/{sid}/skills", headers=two["ah"], json=body)).status_code == 404
    assert (await client.post(f"{B}/staff/{sid}/photo", headers=two["ah"], json={"data": _b64(_png())})).status_code == 404
    # Dịch vụ của chi nhánh khác không được gán chéo.
    assert (await client.put(f"{B}/staff/{sid}/skills", headers=one["ah"], json={"service_ids": [two["s60"]["id"]]})).status_code == 422


@pytest.mark.asyncio
async def test_skills_filter_auto_assignment_and_available_slots(client):
    ctx = await _setup_spa(client, staff_count=2)
    ah, (skilled, other) = ctx["ah"], ctx["staff"]
    day = _day()
    # Chưa khai báo kỹ năng: giữ hành vi cũ, cả hai KTV đều nhận lịch.
    q = f"date={day}&service_ids={ctx['s60']['id']}"
    slots = (await client.get(f"{B}/bookings/available-slots?{q}", headers=ah)).json()["slots"]
    assert set(slots[0]["available_staff_ids"]) == {skilled, other}

    await client.put(f"{B}/staff/{skilled}/skills", headers=ah, json={"service_ids": [ctx["s60"]["id"]]})
    await client.put(f"{B}/staff/{other}/skills", headers=ah, json={"service_ids": [ctx["s30"]["id"]]})
    slots = (await client.get(f"{B}/bookings/available-slots?{q}", headers=ah)).json()["slots"]
    assert all(s["available_staff_ids"] == [skilled] for s in slots)

    for hour in (9, 11):
        r = await client.post(f"{B}/bookings", headers=ctx["ch"], json={
            "start_time": f"{day}T{hour:02d}:00:00+07:00", "items": [{"service_id": ctx["s60"]["id"]}]})
        assert r.status_code == 201, r.text
        assert r.json()["staff_id"] == skilled
    # KTV đã khai báo nhưng không khớp dịch vụ thì không được auto-assign dù đang rảnh.
    r = await client.post(f"{B}/bookings", headers=ctx["ch"], json={
        "start_time": f"{day}T09:30:00+07:00", "items": [{"service_id": ctx["s60"]["id"]}]})
    assert r.status_code == 409, r.text
