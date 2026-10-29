import asyncio
import uuid
from datetime import date, timedelta
from typing import Dict, List, Optional

import pytest

from app.core.config import settings
from tests.conftest import unique_phone, unique_slug

B = "/api/v1"


def _day(offset: int = 3) -> date:
    return date.today() + timedelta(days=offset)


def _dow(d: date) -> int:
    return (d.weekday() + 1) % 7  # 0 = Chủ nhật


async def _setup_spa(client, staff_count: int = 1) -> Dict:
    """Tạo Spa mới (09:00-20:00, buffer 10) + KTV có ca 09:00-20:00 cả tuần + 2 dịch vụ lẻ + 1 gói + 1 khách."""
    slug = unique_slug("bk")
    r = await client.post(
        f"{B}/auth/register-tenant",
        json={
            "tenant_name": "Spa " + slug, "tenant_slug": slug, "admin_full_name": "Admin",
            "phone_number": unique_phone(), "password": "secret123",
        },
    )
    assert r.status_code == 201, r.text
    ah = {"Authorization": "Bearer " + r.json()["access_token"]}
    r = await client.patch(
        f"{B}/tenants/me", headers=ah,
        json={"open_time": "09:00:00", "close_time": "20:00:00", "buffer_minutes": 10},
    )
    assert r.status_code == 200, r.text

    staff: List[str] = []
    for _ in range(staff_count):
        r = await client.post(
            f"{B}/staff", headers=ah, json={"full_name": "KTV", "phone_number": unique_phone(), "password": "secret123"}
        )
        sid = r.json()["id"]
        staff.append(sid)
        r = await client.put(
            f"{B}/staff/{sid}/schedules", headers=ah,
            json={"schedules": [{"day_of_week": d, "start_time": "09:00:00", "end_time": "20:00:00"} for d in range(7)]},
        )
        assert r.status_code == 200, r.text

    async def svc(name, minutes, price, **extra):
        r = await client.post(
            f"{B}/services", headers=ah,
            json={"name": name, "duration_minutes": minutes, "price": price, **extra},
        )
        assert r.status_code == 201, r.text
        return r.json()

    s60 = await svc("Massage 60", 60, "300000")
    s30 = await svc("Goi dau 30", 30, "100000")
    pkg_svc = await svc("Lieu trinh 2 buoi", 60, "2000000", is_package=True, total_sessions=2)

    cphone = unique_phone()
    r = await client.post(
        f"{B}/auth/register", headers={"X-Tenant-Slug": slug},
        json={"full_name": "Khach", "phone_number": cphone, "password": "secret123"},
    )
    assert r.status_code == 201, r.text
    return {
        "slug": slug, "ah": ah, "staff": staff, "s60": s60, "s30": s30, "pkg_svc": pkg_svc,
        "customer_id": r.json()["user"]["id"],
        "ch": {"Authorization": "Bearer " + r.json()["access_token"]},
    }


def _body(start: str, services, staff_id: Optional[str] = None, **extra) -> Dict:
    return {"start_time": start, "staff_id": staff_id, "items": [{"service_id": s["id"]} for s in services], **extra}


# ------------------------------------------------------------------ available slots
@pytest.mark.asyncio
async def test_available_slots_rules(client):
    ctx = await _setup_spa(client)
    day = _day()
    staff = ctx["staff"][0]
    params = {"date": day.isoformat(), "service_ids": [ctx["s60"]["id"], ctx["s30"]["id"]]}

    # Khách chưa đăng nhập dùng X-Tenant-Slug; tổng thời lượng = 90 phút
    r = await client.get(f"{B}/bookings/available-slots", headers={"X-Tenant-Slug": ctx["slug"]}, params=params)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total_duration_minutes"] == 90 and data["buffer_minutes"] == 10
    assert data["slots"][0]["start_time"].startswith(f"{day}T09:00:00+07:00")
    assert data["slots"][-1]["end_time"].startswith(f"{day}T20:00:00+07:00")  # slot cuối kết thúc đúng giờ đóng cửa
    assert data["slots"][0]["available_staff_ids"] == [staff]

    # Không JWT, không slug -> 401; dịch vụ lạ -> 404; slug sai -> 404
    assert (await client.get(f"{B}/bookings/available-slots", params=params)).status_code == 401
    bad = {"date": day.isoformat(), "service_ids": [str(uuid.uuid4())]}
    assert (await client.get(f"{B}/bookings/available-slots", headers=ctx["ch"], params=bad)).status_code == 404
    assert (await client.get(f"{B}/bookings/available-slots", headers={"X-Tenant-Slug": "khong-co"}, params=params)).status_code == 404

    # Đặt 09:00-10:30 -> slot kế tiếp của KTV là 10:45 (buffer 10 phút, bước 15 phút)
    r = await client.post(f"{B}/bookings", headers=ctx["ch"], json=_body(data["slots"][0]["start_time"], [ctx["s60"], ctx["s30"]], staff))
    assert r.status_code == 201, r.text
    booking_id = r.json()["id"]
    r = await client.get(f"{B}/bookings/available-slots", headers=ctx["ch"], params={**params, "staff_id": staff})
    assert r.json()["slots"][0]["start_time"].startswith(f"{day}T10:45:00+07:00")

    # Ngày nghỉ (is_day_off) -> không có slot
    sched = [{"day_of_week": d, "start_time": "09:00:00", "end_time": "20:00:00"} for d in range(7) if d != _dow(day)]
    sched.append({"day_of_week": _dow(day), "start_time": "09:00:00", "end_time": "20:00:00", "is_day_off": True})
    assert (await client.put(f"{B}/staff/{staff}/schedules", headers=ctx["ah"], json={"schedules": sched})).status_code == 409
    # The new assignment policy requires resolving occupied appointments first.
    assert (await client.patch(f"{B}/bookings/{booking_id}/status", headers=ctx["ah"], json={"status":"CANCELLED"})).status_code == 200
    assert (await client.put(f"{B}/staff/{staff}/schedules", headers=ctx["ah"], json={"schedules": sched})).status_code == 200
    r = await client.get(f"{B}/bookings/available-slots", headers=ctx["ch"], params=params)
    assert r.json()["slots"] == []

    # Slot tối thiểu: giới hạn bởi giờ đóng cửa của Spa (ca KTV 09-20 nhưng Spa đóng 12:00)
    sched = [{"day_of_week": d, "start_time": "09:00:00", "end_time": "20:00:00"} for d in range(7)]
    await client.put(f"{B}/staff/{staff}/schedules", headers=ctx["ah"], json={"schedules": sched})
    await client.patch(f"{B}/tenants/me", headers=ctx["ah"], json={"close_time": "12:00:00"})
    r = await client.get(f"{B}/bookings/available-slots", headers=ctx["ch"], params={"date": _day(4).isoformat(), "service_ids": [ctx["s60"]["id"]]})
    assert r.json()["slots"][-1]["end_time"].startswith(f"{_day(4)}T12:00:00+07:00")


# ------------------------------------------------------------------ create booking
@pytest.mark.asyncio
async def test_create_booking_rules(client):
    ctx = await _setup_spa(client, staff_count=2)
    day = _day()
    start = f"{day}T10:00:00+07:00"
    staff0, staff1 = ctx["staff"]

    r = await client.post(f"{B}/bookings", headers=ctx["ch"], json=_body(start, [ctx["s60"], ctx["s30"]], staff0, note="Ghi chu"))
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["status"] == "PENDING" and b["staff_id"] == staff0 and b["customer_id"] == ctx["customer_id"]
    assert b["total_duration_minutes"] == 90 and float(b["total_price"]) == 400000
    assert len(b["items"]) == 2 and b["start_time"].startswith(f"{day}T03:00:00")  # lưu UTC (10:00+07 = 03:00Z)

    # Trùng giờ + KTV -> 409; chồng lấn trong buffer (kết thúc 11:30, buffer tới 11:40) -> 409
    assert (await client.post(f"{B}/bookings", headers=ctx["ch"], json=_body(start, [ctx["s30"]], staff0))).status_code == 409
    assert (await client.post(f"{B}/bookings", headers=ctx["ch"], json=_body(f"{day}T11:30:00+07:00", [ctx["s30"]], staff0))).status_code == 409
    assert (await client.post(f"{B}/bookings", headers=ctx["ch"], json=_body(f"{day}T11:45:00+07:00", [ctx["s30"]], staff0))).status_code == 201

    # "Spa tự sắp xếp" -> gán KTV còn trống (staff1)
    r = await client.post(f"{B}/bookings", headers=ctx["ch"], json=_body(start, [ctx["s60"]]))
    assert r.status_code == 201 and r.json()["staff_id"] == staff1
    # Hết KTV -> 409
    assert (await client.post(f"{B}/bookings", headers=ctx["ch"], json=_body(start, [ctx["s60"]]))).status_code == 409

    # Ngoài giờ làm việc / quá khứ / dịch vụ lạ / KTV lạ
    assert (await client.post(f"{B}/bookings", headers=ctx["ch"], json=_body(f"{day}T08:00:00+07:00", [ctx["s30"]], staff0))).status_code == 409
    assert (await client.post(f"{B}/bookings", headers=ctx["ch"], json=_body(f"{day}T19:30:00+07:00", [ctx["s60"]], staff0))).status_code == 409
    past = f"{date.today() - timedelta(days=1)}T10:00:00+07:00"
    assert (await client.post(f"{B}/bookings", headers=ctx["ch"], json=_body(past, [ctx["s30"]], staff0))).status_code == 422
    assert (await client.post(f"{B}/bookings", headers=ctx["ch"], json={"start_time": start, "items": [{"service_id": str(uuid.uuid4())}]})).status_code == 404
    assert (await client.post(f"{B}/bookings", headers=ctx["ch"], json=_body(f"{day}T16:00:00+07:00", [ctx["s30"]], str(uuid.uuid4())))).status_code == 404
    # Dịch vụ gói (is_package) vẫn đặt bình thường như dịch vụ có giá
    # Admin tạo tại quầy: bắt buộc customer_id
    assert (await client.post(f"{B}/bookings", headers=ctx["ah"], json=_body(f"{day}T16:00:00+07:00", [ctx["s30"]], staff0))).status_code == 422
    r = await client.post(
        f"{B}/bookings", headers=ctx["ah"],
        json={**_body(f"{day}T16:00:00+07:00", [ctx["s30"]], staff0), "customer_id": ctx["customer_id"]},
    )
    assert r.status_code == 201 and r.json()["customer_id"] == ctx["customer_id"]
    # Khách không đặt thay người khác
    r = await client.post(f"{B}/bookings", headers=ctx["ch"], json={**_body(f"{day}T17:00:00+07:00", [ctx["s30"]], staff0), "customer_id": str(uuid.uuid4())})
    assert r.status_code == 403


# ------------------------------------------------------------------ concurrency
@pytest.mark.asyncio
async def test_concurrent_booking_same_staff_only_one_succeeds(client):
    """5 request song song đặt cùng 1 KTV, cùng khung giờ -> đúng 1 thành công, 4 request còn lại 409."""
    ctx = await _setup_spa(client)
    start = f"{_day()}T14:00:00+07:00"
    staff = ctx["staff"][0]

    results = await asyncio.gather(
        *[client.post(f"{B}/bookings", headers=ctx["ch"], json=_body(start, [ctx["s60"]], staff)) for _ in range(5)]
    )
    codes = sorted(r.status_code for r in results)
    assert codes == [201, 409, 409, 409, 409], codes

    r = await client.get(f"{B}/bookings", headers=ctx["ah"], params={"staff_id": staff})
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_concurrent_auto_assign_distributes_staff(client):
    """5 request 'Spa tự sắp xếp' cùng slot với 3 KTV -> đúng 3 thành công (3 KTV khác nhau), 2 request 409."""
    ctx = await _setup_spa(client, staff_count=3)
    start = f"{_day()}T14:00:00+07:00"
    results = await asyncio.gather(
        *[client.post(f"{B}/bookings", headers=ctx["ch"], json=_body(start, [ctx["s60"]])) for _ in range(5)]
    )
    codes = sorted(r.status_code for r in results)
    assert codes == [201, 201, 201, 409, 409], codes
    assert {r.json()["staff_id"] for r in results if r.status_code == 201} == set(ctx["staff"])


@pytest.mark.asyncio
async def test_concurrent_package_overbooking_blocked(client):
    """Thẻ còn 2 buổi: 4 request song song (khung giờ khác nhau) -> đúng 2 thành công."""
    ctx = await _setup_spa(client, staff_count=4)
    r = await client.post(f"{B}/customer-packages", headers=ctx["ah"], json={"customer_id": ctx["customer_id"], "service_id": ctx["pkg_svc"]["id"]})
    assert r.status_code == 201, r.text
    pkg = r.json()

    def book(hour: int):
        return client.post(
            f"{B}/bookings", headers=ctx["ch"],
            json={
                "start_time": f"{_day()}T{hour:02d}:00:00+07:00",
                "items": [{"service_id": ctx["pkg_svc"]["id"], "customer_package_id": pkg["id"]}],
            },
        )

    results = await asyncio.gather(*[book(h) for h in (9, 11, 13, 15)])
    codes = sorted(r.status_code for r in results)
    assert codes == [201, 201, 409, 409], codes


# ------------------------------------------------------------------ package + status flow
@pytest.mark.asyncio
async def test_package_booking_and_auto_deduct_on_completed(client):
    ctx = await _setup_spa(client)
    ah, cid = ctx["ah"], ctx["customer_id"]
    pkg = (await client.post(f"{B}/customer-packages", headers=ah, json={"customer_id": cid, "service_id": ctx["pkg_svc"]["id"]})).json()
    day = _day()

    def pbody(hour, **extra):
        return {
            "start_time": f"{day}T{hour:02d}:00:00+07:00",
            "items": [{"service_id": ctx["pkg_svc"]["id"], "customer_package_id": pkg["id"]}],
            **extra,
        }

    # Sai dịch vụ so với thẻ -> 422; thẻ của khách khác -> 422
    r = await client.post(f"{B}/bookings", headers=ctx["ch"], json={"start_time": f"{day}T09:00:00+07:00", "items": [{"service_id": ctx["s60"]["id"], "customer_package_id": pkg["id"]}]})
    assert r.status_code == 422
    r = await client.post(f"{B}/auth/register", headers={"X-Tenant-Slug": ctx["slug"]}, json={"full_name": "K2", "phone_number": unique_phone(), "password": "secret123"})
    other_h = {"Authorization": "Bearer " + r.json()["access_token"]}
    assert (await client.post(f"{B}/bookings", headers=other_h, json=pbody(9))).status_code == 422

    # Buổi dùng thẻ có giá 0; thẻ còn 2 buổi -> booking thứ 3 bị 409
    b1 = await client.post(f"{B}/bookings", headers=ctx["ch"], json=pbody(9))
    assert b1.status_code == 201, b1.text
    assert float(b1.json()["total_price"]) == 0 and float(b1.json()["items"][0]["price"]) == 0
    b2 = await client.post(f"{B}/bookings", headers=ctx["ch"], json=pbody(11))
    assert b2.status_code == 201
    assert (await client.post(f"{B}/bookings", headers=ctx["ch"], json=pbody(13))).status_code == 409

    # Hủy 1 booking -> trả lại buổi giữ chỗ -> đặt lại được
    assert (await client.post(f"{B}/bookings/{b2.json()['id']}/cancel", headers=ctx["ch"])).status_code == 200
    b3 = await client.post(f"{B}/bookings", headers=ctx["ch"], json=pbody(13))
    assert b3.status_code == 201

    async def pkg_state():
        return (await client.get(f"{B}/customer-packages", headers=ah, params={"customer_id": cid})).json()[0]

    # Luồng trạng thái hợp lệ / không hợp lệ
    url = f"{B}/bookings/{b1.json()['id']}/status"
    assert (await client.patch(url, headers=ah, json={"status": "COMPLETED"})).status_code == 409  # PENDING -> COMPLETED
    assert (await client.patch(url, headers=ctx["ch"], json={"status": "CONFIRMED"})).status_code == 403  # khách không đổi
    for st in ("CONFIRMED", "IN_PROGRESS"):
        assert (await client.patch(url, headers=ah, json={"status": st})).status_code == 200
    assert (await pkg_state())["used_sessions"] == 0  # chưa trừ khi chưa COMPLETED

    r = await client.patch(url, headers=ah, json={"status": "COMPLETED"})
    assert r.status_code == 200 and r.json()["status"] == "COMPLETED"
    assert (await pkg_state())["used_sessions"] == 1
    # Idempotent: COMPLETED lần 2 không trừ thêm; trạng thái cuối không chuyển tiếp được
    assert (await client.patch(url, headers=ah, json={"status": "COMPLETED"})).status_code == 200
    assert (await pkg_state())["used_sessions"] == 1
    assert (await client.patch(url, headers=ah, json={"status": "CANCELLED"})).status_code == 409

    # Hoàn thành buổi 2 -> used == total -> thẻ COMPLETED, và 2 request COMPLETED song song vẫn chỉ trừ 1 lần
    url3 = f"{B}/bookings/{b3.json()['id']}/status"
    await client.patch(url3, headers=ah, json={"status": "CONFIRMED"})
    rs = await asyncio.gather(*[client.patch(url3, headers=ah, json={"status": "COMPLETED"}) for _ in range(3)])
    assert [r.status_code for r in rs] == [200, 200, 200]
    state = await pkg_state()
    assert state["used_sessions"] == 2 and state["status"] == "COMPLETED" and state["remaining_sessions"] == 0

    # Thẻ đã COMPLETED không đặt thêm được
    assert (await client.post(f"{B}/bookings", headers=ctx["ch"], json=pbody(15))).status_code == 422


@pytest.mark.asyncio
async def test_no_show_and_expired_package(client):
    ctx = await _setup_spa(client)
    ah, cid = ctx["ah"], ctx["customer_id"]
    day = _day()
    b = (await client.post(f"{B}/bookings", headers=ctx["ch"], json=_body(f"{day}T10:00:00+07:00", [ctx["s30"]]))).json()
    url = f"{B}/bookings/{b['id']}/status"
    assert (await client.patch(url, headers=ah, json={"status": "NO_SHOW"})).status_code == 409  # PENDING -> NO_SHOW
    await client.patch(url, headers=ah, json={"status": "CONFIRMED"})
    assert (await client.patch(url, headers=ah, json={"status": "NO_SHOW"})).json()["status"] == "NO_SHOW"

    # Thẻ hết hạn trước giờ hẹn -> 422
    exp = (date.today() + timedelta(days=1)).isoformat() + "T00:00:00+07:00"
    pkg = (await client.post(f"{B}/customer-packages", headers=ah, json={"customer_id": cid, "service_id": ctx["pkg_svc"]["id"], "expiry_date": exp})).json()
    r = await client.post(
        f"{B}/bookings", headers=ctx["ch"],
        json={"start_time": f"{day}T12:00:00+07:00", "items": [{"service_id": ctx["pkg_svc"]["id"], "customer_package_id": pkg["id"]}]},
    )
    assert r.status_code == 422, r.text


# ------------------------------------------------------------------ list / cancel / isolation
@pytest.mark.asyncio
async def test_list_cancel_and_visibility(client, monkeypatch):
    ctx = await _setup_spa(client, staff_count=2)
    ah, ch = ctx["ah"], ctx["ch"]
    day = _day()
    staff0, staff1 = ctx["staff"]

    b1 = (await client.post(f"{B}/bookings", headers=ch, json=_body(f"{day}T10:00:00+07:00", [ctx["s60"]], staff0))).json()
    b2 = (await client.post(f"{B}/bookings", headers=ch, json=_body(f"{day}T10:00:00+07:00", [ctx["s60"]], staff1))).json()

    # Admin lọc theo ngày / KTV / trạng thái
    r = await client.get(f"{B}/bookings", headers=ah, params={"date_from": day.isoformat(), "date_to": day.isoformat()})
    assert len(r.json()) == 2
    r = await client.get(f"{B}/bookings", headers=ah, params={"staff_id": staff1})
    assert [x["id"] for x in r.json()] == [b2["id"]]
    assert (await client.get(f"{B}/bookings", headers=ah, params={"date_from": _day(9).isoformat()})).json() == []
    assert (await client.get(f"{B}/bookings", headers=ah, params={"status": "CONFIRMED"})).json() == []
    assert (await client.get(f"{B}/bookings", headers=ah, params={"scope": "bad"})).status_code == 422

    # Khách khác không thấy lịch của khách này
    r = await client.post(f"{B}/auth/register", headers={"X-Tenant-Slug": ctx["slug"]}, json={"full_name": "K2", "phone_number": unique_phone(), "password": "secret123"})
    other_h = {"Authorization": "Bearer " + r.json()["access_token"]}
    assert (await client.get(f"{B}/bookings", headers=other_h)).json() == []
    assert (await client.get(f"{B}/bookings/{b1['id']}", headers=other_h)).status_code == 404
    assert (await client.post(f"{B}/bookings/{b1['id']}/cancel", headers=other_h)).status_code == 404

    # Khách: upcoming có 2 lịch, history rỗng
    assert len((await client.get(f"{B}/bookings", headers=ch, params={"scope": "upcoming"})).json()) == 2
    assert (await client.get(f"{B}/bookings", headers=ch, params={"scope": "history"})).json() == []
    detail = await client.get(f"{B}/bookings/{b1['id']}", headers=ch)
    assert detail.status_code == 200 and len(detail.json()["items"]) == 1

    # Quy tắc hủy của khách: phải cách giờ hẹn tối thiểu X giờ
    monkeypatch.setattr(settings, "CANCELLATION_MIN_HOURS", 24 * 365)
    assert (await client.post(f"{B}/bookings/{b1['id']}/cancel", headers=ch)).status_code == 409
    monkeypatch.setattr(settings, "CANCELLATION_MIN_HOURS", 2)
    r = await client.post(f"{B}/bookings/{b1['id']}/cancel", headers=ch)
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    assert (await client.post(f"{B}/bookings/{b1['id']}/cancel", headers=ch)).status_code == 200  # idempotent

    # Khách không hủy được lịch đã CONFIRMED->IN_PROGRESS; admin hủy được lịch đang làm dở
    url = f"{B}/bookings/{b2['id']}/status"
    for st in ("CONFIRMED", "IN_PROGRESS"):
        await client.patch(url, headers=ah, json={"status": st})
    assert (await client.post(f"{B}/bookings/{b2['id']}/cancel", headers=ch)).status_code == 409
    assert (await client.post(f"{B}/bookings/{b2['id']}/cancel", headers=ah)).json()["status"] == "CANCELLED"

    # Lịch đã hủy -> nằm trong history, KTV rảnh lại
    assert len((await client.get(f"{B}/bookings", headers=ch, params={"scope": "history"})).json()) == 2
    r = await client.get(f"{B}/bookings/available-slots", headers=ch, params={"date": day.isoformat(), "service_ids": [ctx["s60"]["id"]], "staff_id": staff0})
    assert r.json()["slots"][0]["start_time"].startswith(f"{day}T09:00:00")


@pytest.mark.asyncio
async def test_booking_multi_tenant_isolation(client):
    a = await _setup_spa(client)
    b = await _setup_spa(client)
    day = _day()
    booking = (await client.post(f"{B}/bookings", headers=a["ch"], json=_body(f"{day}T10:00:00+07:00", [a["s60"]], a["staff"][0]))).json()

    # Admin Spa B không thấy / không đổi / không hủy được lịch của Spa A
    assert (await client.get(f"{B}/bookings", headers=b["ah"])).json() == []
    assert (await client.get(f"{B}/bookings/{booking['id']}", headers=b["ah"])).status_code == 404
    assert (await client.patch(f"{B}/bookings/{booking['id']}/status", headers=b["ah"], json={"status": "CONFIRMED"})).status_code == 404
    assert (await client.post(f"{B}/bookings/{booking['id']}/cancel", headers=b["ah"])).status_code == 404

    # Đặt lịch ở Spa B bằng KTV/dịch vụ/khách của Spa A -> 404
    start = f"{day}T10:00:00+07:00"
    assert (await client.post(f"{B}/bookings", headers=b["ch"], json=_body(start, [b["s60"]], a["staff"][0]))).status_code == 404
    assert (await client.post(f"{B}/bookings", headers=b["ch"], json=_body(start, [a["s60"]]))).status_code == 404
    r = await client.post(f"{B}/bookings", headers=b["ah"], json={**_body(start, [b["s60"]]), "customer_id": a["customer_id"]})
    assert r.status_code == 404
    # available-slots không lộ KTV của Spa khác
    r = await client.get(f"{B}/bookings/available-slots", headers=b["ch"], params={"date": day.isoformat(), "service_ids": [b["s60"]["id"]]})
    assert all(a["staff"][0] not in s["available_staff_ids"] for s in r.json()["slots"])
