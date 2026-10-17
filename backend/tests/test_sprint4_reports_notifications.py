import asyncio
import json
import uuid
from datetime import date, timedelta
from typing import Dict, List

import pytest

from app.core.config import settings
from app.services import notification_service
from tests.conftest import unique_phone, unique_slug

B = "/api/v1"


def _day(offset: int = 3) -> date:
    return date.today() + timedelta(days=offset)


def _h(token: str) -> Dict[str, str]:
    return {"Authorization": "Bearer " + token}


async def _setup(client, staff_count: int = 2) -> Dict:
    slug = unique_slug("s4")
    r = await client.post(
        f"{B}/auth/register-tenant",
        json={
            "tenant_name": "Spa " + slug, "tenant_slug": slug, "admin_full_name": "Admin",
            "phone_number": unique_phone(), "password": "secret123",
        },
    )
    assert r.status_code == 201, r.text
    ah = _h(r.json()["access_token"])
    admin_id = r.json()["user"]["id"]
    await client.patch(f"{B}/tenants/me", headers=ah, json={"open_time": "09:00:00", "close_time": "20:00:00", "buffer_minutes": 10})

    staff = []
    for i in range(staff_count):
        phone = unique_phone()
        r = await client.post(f"{B}/staff", headers=ah, json={"full_name": f"KTV {i}", "phone_number": phone, "password": "secret123"})
        sid = r.json()["id"]
        await client.put(
            f"{B}/staff/{sid}/schedules", headers=ah,
            json={"schedules": [{"day_of_week": d, "start_time": "09:00:00", "end_time": "20:00:00"} for d in range(7)]},
        )
        login = await client.post(f"{B}/auth/login", headers={"X-Tenant-Slug": slug}, json={"phone_number": phone, "password": "secret123"})
        staff.append({"id": sid, "h": _h(login.json()["access_token"])})

    async def svc(name, minutes, price, **extra):
        r = await client.post(f"{B}/services", headers=ah, json={"name": name, "duration_minutes": minutes, "price": price, **extra})
        assert r.status_code == 201, r.text
        return r.json()

    r = await client.post(
        f"{B}/auth/register", headers={"X-Tenant-Slug": slug},
        json={"full_name": "Khach", "phone_number": unique_phone(), "password": "secret123"},
    )
    return {
        "slug": slug, "ah": ah, "admin_id": admin_id, "staff": staff,
        "s60": await svc("Massage", 60, "300000"),
        "s30": await svc("Goi dau", 30, "100000"),
        "pkg_svc": await svc("Lieu trinh", 60, "2000000", is_package=True, total_sessions=5),
        "customer_id": r.json()["user"]["id"], "ch": _h(r.json()["access_token"]),
    }


async def _book(client, headers, start: str, services: List[Dict], staff_id=None, customer_id=None, package_id=None):
    items = [{"service_id": s["id"]} for s in services]
    if package_id:
        items = [{"service_id": services[0]["id"], "customer_package_id": package_id}]
    body = {"start_time": start, "staff_id": staff_id, "items": items}
    if customer_id:
        body["customer_id"] = customer_id
    r = await client.post(f"{B}/bookings", headers=headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def _complete(client, ah, booking_id: str):
    for st in ("CONFIRMED", "IN_PROGRESS", "COMPLETED"):
        r = await client.patch(f"{B}/bookings/{booking_id}/status", headers=ah, json={"status": st})
        assert r.status_code == 200, r.text


# ================================================================== REPORTS
@pytest.mark.asyncio
async def test_staff_performance_report(client):
    ctx = await _setup(client)
    ah, ch = ctx["ah"], ctx["ch"]
    k0, k1 = ctx["staff"][0]["id"], ctx["staff"][1]["id"]
    day = _day()
    pkg = (await client.post(f"{B}/customer-packages", headers=ah, json={"customer_id": ctx["customer_id"], "service_id": ctx["pkg_svc"]["id"]})).json()

    # KTV0: booking A (Massage + Goi dau = 400k), booking B (buổi liệu trình = 0đ) -> COMPLETED
    a = await _book(client, ch, f"{day}T09:00:00+07:00", [ctx["s60"], ctx["s30"]], k0)
    b = await _book(client, ch, f"{day}T12:00:00+07:00", [ctx["pkg_svc"]], k0, package_id=pkg["id"])
    # KTV1: booking C (300k) COMPLETED; booking D (300k) chỉ CONFIRMED; booking E bị CANCELLED -> không tính
    c = await _book(client, ch, f"{day}T09:00:00+07:00", [ctx["s60"]], k1)
    d = await _book(client, ch, f"{day}T12:00:00+07:00", [ctx["s60"]], k1)
    e = await _book(client, ch, f"{day}T15:00:00+07:00", [ctx["s60"]], k1)
    for bk in (a, b, c):
        await _complete(client, ah, bk["id"])
    await client.patch(f"{B}/bookings/{d['id']}/status", headers=ah, json={"status": "CONFIRMED"})
    await client.patch(f"{B}/bookings/{e['id']}/status", headers=ah, json={"status": "CANCELLED"})
    # booking COMPLETED nằm ngoài khoảng lọc (ngày khác) -> chỉ tính khi khoảng ngày bao phủ
    f = await _book(client, ch, f"{_day(5)}T10:00:00+07:00", [ctx["s60"]], k1)
    await _complete(client, ah, f["id"])

    params = {"start_date": day.isoformat(), "end_date": day.isoformat()}
    r = await client.get(f"{B}/reports/staff-performance", headers=ah, params=params)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["timezone"] == "Asia/Ho_Chi_Minh"
    by = {s["staff_id"]: s for s in data["staff"]}
    s0, s1 = by[k0], by[k1]
    assert (s0["completed_bookings_count"], s0["completed_services_count"], s0["single_services_count"], s0["package_sessions_count"]) == (2, 3, 2, 1)
    assert float(s0["total_revenue"]) == 400000
    assert (s1["completed_bookings_count"], s1["completed_services_count"], s1["package_sessions_count"]) == (1, 1, 0)
    assert float(s1["total_revenue"]) == 300000
    assert data["totals"]["completed_bookings_count"] == 3 and float(data["totals"]["total_revenue"]) == 700000

    # Mở rộng khoảng ngày -> cộng thêm booking F; lọc theo staff_id
    r = await client.get(f"{B}/reports/staff-performance", headers=ah, params={"start_date": day.isoformat(), "end_date": _day(5).isoformat(), "staff_id": k1})
    assert [s["staff_id"] for s in r.json()["staff"]] == [k1]
    assert r.json()["staff"][0]["completed_bookings_count"] == 2 and float(r.json()["staff"][0]["total_revenue"]) == 600000

    # Khoảng không có dữ liệu -> các KTV vẫn xuất hiện với giá trị 0
    r = await client.get(f"{B}/reports/staff-performance", headers=ah, params={"start_date": _day(20).isoformat(), "end_date": _day(21).isoformat()})
    assert len(r.json()["staff"]) == 2 and all(s["completed_bookings_count"] == 0 and float(s["total_revenue"]) == 0 for s in r.json()["staff"])

    # Validate + phân quyền
    assert (await client.get(f"{B}/reports/staff-performance", headers=ah, params={"start_date": "2026-02-02", "end_date": "2026-02-01"})).status_code == 422
    assert (await client.get(f"{B}/reports/staff-performance", headers=ah, params={"start_date": "2020-01-01", "end_date": "2026-01-01"})).status_code == 422
    assert (await client.get(f"{B}/reports/staff-performance", headers=ah, params={**params, "staff_id": str(uuid.uuid4())})).status_code == 404
    assert (await client.get(f"{B}/reports/staff-performance", headers=ctx["staff"][0]["h"], params=params)).status_code == 403
    assert (await client.get(f"{B}/reports/staff-performance", headers=ch, params=params)).status_code == 403
    assert (await client.get(f"{B}/reports/staff-performance", params=params)).status_code == 401


@pytest.mark.asyncio
async def test_report_timezone_boundaries(client):
    """Booking 00:30 (+07) = 17:30Z ngày hôm trước (UTC) vẫn phải thuộc ngày địa phương; 23:30 (+07) cũng vậy."""
    ctx = await _setup(client, staff_count=1)
    ah, ch, k = ctx["ah"], ctx["ch"], ctx["staff"][0]["id"]
    await client.patch(f"{B}/tenants/me", headers=ah, json={"open_time": "00:00:00", "close_time": "23:59:00"})
    await client.put(
        f"{B}/staff/{k}/schedules", headers=ah,
        json={"schedules": [{"day_of_week": d, "start_time": "00:00:00", "end_time": "23:59:00"} for d in range(7)]},
    )
    day = _day()
    early = await _book(client, ch, f"{day}T00:30:00+07:00", [ctx["s30"]], k)
    late = await _book(client, ch, f"{day}T23:15:00+07:00", [ctx["s30"]], k)
    other = await _book(client, ch, f"{day + timedelta(days=1)}T00:15:00+07:00", [ctx["s30"]], k)
    for bk in (early, late, other):
        await _complete(client, ah, bk["id"])

    r = await client.get(f"{B}/reports/staff-performance", headers=ah, params={"start_date": day.isoformat(), "end_date": day.isoformat()})
    assert r.json()["staff"][0]["completed_bookings_count"] == 2  # early + late, không lẫn booking 00:15 ngày hôm sau
    nxt = await client.get(f"{B}/reports/staff-performance", headers=ah, params={"start_date": (day + timedelta(days=1)).isoformat(), "end_date": (day + timedelta(days=1)).isoformat()})
    assert nxt.json()["staff"][0]["completed_bookings_count"] == 1


@pytest.mark.asyncio
async def test_report_and_notifications_tenant_isolation(client):
    a, b = await _setup(client), await _setup(client)
    day = _day()
    bk = await _book(client, a["ch"], f"{day}T09:00:00+07:00", [a["s60"]], a["staff"][0]["id"])
    await _complete(client, a["ah"], bk["id"])

    # Admin Spa B không thấy KTV/doanh thu của Spa A
    r = await client.get(f"{B}/reports/staff-performance", headers=b["ah"], params={"start_date": day.isoformat(), "end_date": day.isoformat()})
    ids = {s["staff_id"] for s in r.json()["staff"]}
    assert ids == {s["id"] for s in b["staff"]} and float(r.json()["totals"]["total_revenue"]) == 0
    assert (await client.get(f"{B}/reports/staff-performance", headers=b["ah"], params={"start_date": day.isoformat(), "end_date": day.isoformat(), "staff_id": a["staff"][0]["id"]})).status_code == 404

    # Thông báo của Spa A không lọt sang Spa B
    notes_a = (await client.get(f"{B}/notifications", headers=a["ah"])).json()
    assert notes_a["unread_count"] >= 1
    notes_b = (await client.get(f"{B}/notifications", headers=b["ah"])).json()
    assert notes_b["items"] == [] and notes_b["unread_count"] == 0
    nid = notes_a["items"][0]["id"]
    assert (await client.patch(f"{B}/notifications/{nid}/read", headers=b["ah"])).status_code == 404

    # Subscription của Spa A không bị Spa B nhìn thấy/xóa: unsubscribe cùng endpoint ở Spa B -> deleted = 0
    endpoint = "https://push.example.com/send/" + uuid.uuid4().hex
    sub = {"endpoint": endpoint, "keys": {"p256dh": "BPkey", "auth": "authkey"}}
    assert (await client.post(f"{B}/notifications/subscribe", headers=a["ah"], json=sub)).status_code == 201
    r = await client.request("DELETE", f"{B}/notifications/unsubscribe", headers=b["ah"], json={"endpoint": endpoint})
    assert r.json() == {"deleted": 0}
    r = await client.request("DELETE", f"{B}/notifications/unsubscribe", headers=a["ah"], json={"endpoint": endpoint})
    assert r.json() == {"deleted": 1}


# ================================================================== NOTIFICATIONS
@pytest.mark.asyncio
async def test_subscribe_unsubscribe_and_vapid_key(client, monkeypatch):
    ctx = await _setup(client, staff_count=1)
    ah, ch = ctx["ah"], ctx["ch"]

    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", "")
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", "")
    assert (await client.get(f"{B}/notifications/vapid-public-key")).json() == {"public_key": "", "enabled": False}
    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", "BPublicKeyForTests")
    r = await client.get(f"{B}/notifications/vapid-public-key")
    assert r.status_code == 200 and r.json() == {"public_key": "BPublicKeyForTests", "enabled": False}
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", "private-test-key")
    assert (await client.get(f"{B}/notifications/vapid-public-key")).json()["enabled"] is True

    endpoint = "https://push.example.com/send/" + uuid.uuid4().hex
    sub = {"endpoint": endpoint, "keys": {"p256dh": "key1", "auth": "auth1"}}
    assert (await client.post(f"{B}/notifications/subscribe", json=sub)).status_code == 401
    assert (await client.post(f"{B}/notifications/subscribe", headers=ch, json={**sub, "endpoint": "http://insecure.example.com/x"})).status_code == 422
    assert (await client.post(f"{B}/notifications/subscribe", headers=ch, json={"endpoint": endpoint})).status_code == 422

    r1 = await client.post(f"{B}/notifications/subscribe", headers=ch, json=sub)
    assert r1.status_code == 201 and r1.json()["endpoint"] == endpoint
    # Đăng ký lại cùng endpoint -> cập nhật khoá, không tạo bản ghi mới (idempotent)
    r2 = await client.post(f"{B}/notifications/subscribe", headers=ch, json={**sub, "keys": {"p256dh": "key2", "auth": "auth2"}})
    assert r2.status_code == 201 and r2.json()["id"] == r1.json()["id"]

    # Cùng trình duyệt chuyển sang tài khoản khác: đăng ký của user cũ bị gỡ
    assert (await client.post(f"{B}/notifications/subscribe", headers=ah, json=sub)).status_code == 201
    r = await client.request("DELETE", f"{B}/notifications/unsubscribe", headers=ch, json={"endpoint": endpoint})
    assert r.json() == {"deleted": 0}
    r = await client.request("DELETE", f"{B}/notifications/unsubscribe", headers=ah, json={"endpoint": endpoint})
    assert r.json() == {"deleted": 1}
    # Hủy 2 lần vẫn OK
    r = await client.request("DELETE", f"{B}/notifications/unsubscribe", headers=ah, json={"endpoint": endpoint})
    assert r.status_code == 200 and r.json() == {"deleted": 0}


@pytest.mark.asyncio
async def test_booking_events_create_notifications_and_push(client, monkeypatch):
    ctx = await _setup(client, staff_count=2)
    ah, ch = ctx["ah"], ctx["ch"]
    k0, k1 = ctx["staff"]
    day = _day()

    # Bật Web Push giả lập: ghi nhận các lần gửi, không gọi mạng thật
    sent: List[Dict] = []

    async def fake_send(sub, payload):
        sent.append({"endpoint": sub["endpoint"], "payload": payload})
        return 410 if sub["endpoint"].endswith("dead") else None

    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", "pub")
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", "priv")
    monkeypatch.setattr(notification_service, "_send_one", fake_send)

    ep_admin = "https://push.example.com/admin" + uuid.uuid4().hex
    ep_cust = "https://push.example.com/cust" + uuid.uuid4().hex
    ep_dead = "https://push.example.com/dead-" + uuid.uuid4().hex + "dead"
    keys = {"p256dh": "k", "auth": "a"}
    assert (await client.post(f"{B}/notifications/subscribe", headers=ah, json={"endpoint": ep_admin, "keys": keys})).status_code == 201
    assert (await client.post(f"{B}/notifications/subscribe", headers=ch, json={"endpoint": ep_cust, "keys": keys})).status_code == 201
    assert (await client.post(f"{B}/notifications/subscribe", headers=k1["h"], json={"endpoint": ep_dead, "keys": keys})).status_code == 201

    async def notes(headers):
        return (await client.get(f"{B}/notifications", headers=headers)).json()

    # 1. Khách đặt lịch (chỉ định KTV1) -> Admin + KTV phụ trách cố định nhận thông báo; KTV được chỉ định có tiêu đề riêng
    booking = await _book(client, ch, f"{day}T10:00:00+07:00", [ctx["s60"]], k1["id"])
    admin_n, k0_n, k1_n = await notes(ah), await notes(k0["h"]), await notes(k1["h"])
    assert admin_n["unread_count"] == 1 and admin_n["items"][0]["type"] == "BOOKING_CREATED"
    assert admin_n["items"][0]["booking_id"] == booking["id"] and admin_n["items"][0]["title"] == "Có lịch hẹn mới"
    assert k0_n["unread_count"] == 0 and k1_n["items"][0]["title"] == "Lịch hẹn mới được giao cho bạn"
    assert (await notes(ch))["items"] == []  # người đặt không tự nhận thông báo
    pushed = {s["endpoint"] for s in sent}
    assert all(json.loads(s["payload"])["url"] == "/admin/bookings" for s in sent)
    assert pushed == {ep_admin, ep_dead}  # 2 thiết bị của ADMIN/STAFF đã đăng ký; khách không bị gửi
    assert '"type": "BOOKING_CREATED"' in sent[0]["payload"]
    # Subscription trả 410 bị dọn
    r = await client.request("DELETE", f"{B}/notifications/unsubscribe", headers=k1["h"], json={"endpoint": ep_dead})
    assert r.json() == {"deleted": 0}

    # 2. Admin xác nhận / hoàn thành -> chỉ Customer nhận (admin tự thực hiện không nhận)
    sent.clear()
    await client.patch(f"{B}/bookings/{booking['id']}/status", headers=ah, json={"status": "CONFIRMED"})
    await client.patch(f"{B}/bookings/{booking['id']}/status", headers=ah, json={"status": "CONFIRMED"})  # no-op: không thông báo lại
    cust_n = await notes(ch)
    assert cust_n["unread_count"] == 1 and cust_n["items"][0]["type"] == "BOOKING_CONFIRMED"
    assert cust_n["items"][0]["title"] == "Lịch hẹn đã được xác nhận"
    assert all(json.loads(s["payload"])["url"] == f"/{ctx['slug']}/appointments" for s in sent)
    assert {s["endpoint"] for s in sent} == {ep_cust}
    assert (await notes(ah))["unread_count"] == 1  # không tăng thêm

    # 3. Khách đặt rồi hủy -> Admin/Staff nhận 'BOOKING_CANCELLED'; Admin hủy lịch của khách -> khách nhận
    b2 = await _book(client, ch, f"{day}T14:00:00+07:00", [ctx["s60"]], k0["id"])
    r = await client.post(f"{B}/bookings/{b2['id']}/cancel", headers=ch)
    assert r.status_code == 200
    types = [n["type"] for n in (await notes(ah))["items"]]
    assert types.count("BOOKING_CANCELLED") == 1 and types.count("BOOKING_CREATED") == 2
    b3 = await _book(client, ch, f"{day}T16:00:00+07:00", [ctx["s30"]], k0["id"])
    await client.post(f"{B}/bookings/{b3['id']}/cancel", headers=ah)
    assert (await notes(ch))["items"][0]["type"] == "BOOKING_CANCELLED"

    # 4. Admin tạo lịch thủ công tại quầy -> không phát thông báo "khách đặt"
    before = (await notes(k0["h"]))["unread_count"]
    await _book(client, ah, f"{day}T18:00:00+07:00", [ctx["s30"]], k0["id"], customer_id=ctx["customer_id"])
    assert (await notes(k0["h"]))["unread_count"] == before

    # 5. Đánh dấu đã đọc
    items = (await notes(ch))["items"]
    unread_before = (await notes(ch))["unread_count"]
    r = await client.patch(f"{B}/notifications/{items[0]['id']}/read", headers=ch)
    assert r.status_code == 200 and r.json()["is_read"] is True
    assert (await notes(ch))["unread_count"] == unread_before - 1
    only_unread = (await client.get(f"{B}/notifications", headers=ch, params={"unread_only": True})).json()
    assert all(not n["is_read"] for n in only_unread["items"]) and len(only_unread["items"]) == unread_before - 1
    r = await client.patch(f"{B}/notifications/read-all", headers=ch)
    assert r.status_code == 200 and r.json()["updated"] == unread_before - 1
    assert (await notes(ch))["unread_count"] == 0
    assert (await client.patch(f"{B}/notifications/read-all", headers=ch)).json() == {"updated": 0}
    # Thông báo của người khác -> 404
    other_id = (await notes(ah))["items"][0]["id"]
    assert (await client.patch(f"{B}/notifications/{other_id}/read", headers=ch)).status_code == 404


@pytest.mark.asyncio
async def test_notification_failure_never_breaks_booking(client, monkeypatch):
    """Gửi push lỗi / lỗi trong tác vụ nền không được làm hỏng đặt lịch."""
    ctx = await _setup(client, staff_count=1)
    day = _day()

    async def boom(*args, **kwargs):
        raise RuntimeError("push service down")

    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", "pub")
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", "priv")
    monkeypatch.setattr(notification_service, "_send_one", boom)
    endpoint = "https://push.example.com/" + uuid.uuid4().hex
    await client.post(f"{B}/notifications/subscribe", headers=ctx["ah"], json={"endpoint": endpoint, "keys": {"p256dh": "k", "auth": "a"}})

    booking = await _book(client, ctx["ch"], f"{day}T10:00:00+07:00", [ctx["s60"]])
    assert booking["status"] == "PENDING"
    # Thông báo in-app vẫn được lưu dù push lỗi
    assert (await client.get(f"{B}/notifications", headers=ctx["ah"])).json()["unread_count"] == 1

    # Lỗi ngay trong hàm tạo thông báo cũng không lan ra request
    async def boom_deliver(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(notification_service, "_deliver", boom_deliver)
    b2 = await _book(client, ctx["ch"], f"{day}T14:00:00+07:00", [ctx["s60"]])
    assert b2["status"] == "PENDING"
    r = await client.patch(f"{B}/bookings/{b2['id']}/status", headers=ctx["ah"], json={"status": "CONFIRMED"})
    assert r.status_code == 200 and r.json()["status"] == "CONFIRMED"
