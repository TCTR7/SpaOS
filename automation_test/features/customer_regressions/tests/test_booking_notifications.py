import uuid
from datetime import datetime, timedelta

from playwright.sync_api import expect
from common_setup.api_helper import random_phone
from common_setup.config import config


def test_assigned_staff_can_read_appointment_without_edit_controls(scenario):
    s = scenario
    owner = s["call"]("POST", "/staff", json={"full_name": "Profile Owner", "phone_number": random_phone(), "password": "Staff@123"})
    s["call"]("PATCH", "/customers/" + s["customer"]["id"] + "/assignment", json={"assigned_staff_id": owner["id"]})
    booking = s["book"]()
    auth = s["call"]("POST", "/auth/login", headers={"X-Tenant-Slug": s["slug"]},
                     json={"phone_number": s["staff"]["phone_number"], "password": "Staff@123"})
    page = s["page"](auth["access_token"], True)
    page.goto(config.frontend_url + "/admin/bookings")
    page.locator('input[type="date"]').first.fill(booking["start_time"][:10])
    expect(page.get_by_role("main").get_by_text("QA Customer", exact=False)).to_be_visible()
    page.get_by_role("button", name="Chi tiết lịch hẹn", exact=True).click()
    detail = page.get_by_role("dialog", name="Chi tiết lịch hẹn", exact=True)
    expect(detail).to_contain_text("QA Customer")
    expect(detail.get_by_role("button", name="Đổi ngày / giờ / KTV", exact=True)).to_have_count(0)
    expect(detail.get_by_role("button").filter(has_text="→")).to_have_count(0)
    page.keyboard.press("Escape")
    page.get_by_role("button", name="Thông báo", exact=True).click()
    notifications = page.get_by_role("dialog", name="Bảng thông báo", exact=True)
    expect(notifications.get_by_text("Lịch hẹn mới được giao cho bạn", exact=True)).to_be_visible()


def test_customer_sees_counter_booking_notification_once_after_retry(scenario):
    s = scenario
    start = (datetime.now().date() + timedelta(days=5)).isoformat() + "T12:00:00+07:00"
    payload = {"request_id": str(uuid.uuid4()), "customer_id": s["customer"]["id"],
               "staff_id": s["staff"]["id"], "items": [{"service_id": s["service"]["id"], "customer_package_id": s["package"]["id"]}],
               "start_times": [start]}
    first = s["call"]("POST", "/bookings/manual-batches", json=payload)
    assert s["call"]("POST", "/bookings/manual-batches", json=payload) == first
    page = s["page"]()
    page.goto(s["url"] + "/appointments")
    page.get_by_role("button", name="Thông báo lịch hẹn", exact=True).click()
    notifications = page.get_by_role("dialog", name="Bảng thông báo", exact=True)
    expect(notifications.get_by_text("Bạn có lịch hẹn mới", exact=True)).to_have_count(1)
    expect(notifications).to_contain_text("12:00")
