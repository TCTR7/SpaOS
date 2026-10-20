from datetime import datetime, timedelta, timezone
import pytest
from playwright.sync_api import expect
from common_setup.config import config
from common_setup.api_helper import random_phone


def open_edit(s, role, api_helper):
    booking = s["book"]()
    # Fixed customer owner A1, while A2 performs the appointment.
    staff = s["call"]("POST", "/staff", json={"full_name": "QA Cover Staff", "phone_number": random_phone(), "password": "Staff@123"})
    s["call"]("PUT", "/staff/" + staff["id"] + "/schedules", json={"schedules": [
        {"day_of_week": d, "start_time": "00:00:00", "end_time": "23:59:00"} for d in range(7)]})
    booking = s["call"]("PATCH", "/bookings/" + booking["id"], json={"start_time": booking["start_time"], "staff_id": staff["id"]})
    if role == "customer":
        page = s["page"]()
        page.goto(s["url"] + "/appointments")
        page.get_by_role("button", name="Đổi ngày/giờ", exact=True).click()
    else:
        token = s["admin"] if role == "admin" else api_helper.login(s["slug"], s["staff"]["phone_number"], "Staff@123")["access_token"]
        page = s["page"](token, True)
        page.goto(config.frontend_url + "/admin/bookings")
        day = datetime.fromisoformat(booking["start_time"].replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=7))).date().isoformat()
        page.locator("input[type=date]").first.fill(day)
        page.get_by_test_id("booking-card-" + booking["id"]).get_by_role("button", name="Chi tiết lịch hẹn", exact=True).click()
        page.get_by_role("dialog").get_by_role("button", name="Đổi ngày / giờ / KTV", exact=True).click()
    return page, page.get_by_role("dialog"), booking


@pytest.mark.parametrize("role", ["customer", "admin", "staff"])
def test_note_only_keeps_snapshot_and_cover_staff_and_cannot_double_submit(scenario, api_helper, role):
    s = scenario
    page, modal, booking = open_edit(s, role, api_helper)
    # Current menu duration and inactive service must not change the edit slots.
    s["call"]("PATCH", "/services/" + s["service"]["id"], json={"duration_minutes": 120, "is_active": False})
    page.reload()
    if role == "customer":
        page.get_by_role("button", name="Đổi ngày/giờ", exact=True).click()
    else:
        day = datetime.fromisoformat(booking["start_time"].replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=7))).date().isoformat()
        page.locator("input[type=date]").first.fill(day)
        page.get_by_test_id("booking-card-" + booking["id"]).get_by_role("button", name="Chi tiết lịch hẹn", exact=True).click()
        page.get_by_role("dialog").get_by_role("button", name="Đổi ngày / giờ / KTV", exact=True).click()
    submit = modal.get_by_role("button", name="Xác nhận đổi lịch", exact=True)
    expect(submit).to_be_enabled()
    preview = modal.get_by_role("region", name="Thay đổi lịch hẹn", exact=True)
    expect(preview).to_contain_text("30 phút")
    expect(preview).to_contain_text("QA Cover Staff")
    if role != "customer":
        expect(modal.locator("#rescheduleStaffAdmin")).to_have_value(booking["staff_id"])
        if role == "staff":
            expect(modal.locator("#rescheduleStaffAdmin")).to_be_disabled()
    modal.locator("#rescheduleNote" if role == "customer" else "#rescheduleNoteAdmin").fill("Note only, preserve appointment")
    held = []
    def hold_patch(route):
        if route.request.method == "PATCH":
            held.append(route)
            page.evaluate("window.qaHeldPatch = true")
        else:
            route.continue_()
    page.route("**/api/v1/bookings/" + booking["id"], hold_patch)
    with page.expect_request(lambda r: r.method == "PATCH" and r.url.endswith("/bookings/" + booking["id"])):
        modal.locator("form").evaluate("form => { form.requestSubmit(); form.requestSubmit(); }")
    page.wait_for_function("window.qaHeldPatch === true")
    expect(modal.locator('button[type="submit"]')).to_be_disabled()
    page.keyboard.press("Escape")
    expect(modal).to_be_visible()
    assert len(held) == 1
    with page.expect_response(lambda r: r.request.method == "PATCH" and r.url.endswith("/bookings/" + booking["id"])) as saved:
        held[0].fulfill(response=held[0].fetch())
    assert saved.value.status == 200
    expect(modal).to_have_count(0)
    current = s["call"]("GET", "/bookings/" + booking["id"])
    for field in ("id", "start_time", "end_time", "staff_id", "items", "total_price", "total_duration_minutes"):
        assert current[field] == booking[field]
    assert current["note"] == "Note only, preserve appointment"
    package = s["call"]("GET", "/customer-packages/me", headers={"Authorization": "Bearer " + s["token"]})[0]
    assert package["reserved_sessions"] == 1 and package["used_sessions"] == 0


@pytest.mark.parametrize("role", ["customer", "admin"])
def test_new_day_requires_explicit_choice_and_back_keeps_dirty_note(scenario, api_helper, role):
    page, modal, booking = open_edit(scenario, role, api_helper)
    submit = modal.get_by_role("button", name="Xác nhận đổi lịch", exact=True)
    expect(submit).to_be_enabled()

    note = modal.locator("#rescheduleNote" if role == "customer" else "#rescheduleNoteAdmin")
    note.fill("Keep my draft")
    day = (datetime.now(timezone(timedelta(hours=7))) + timedelta(days=8)).date().isoformat()
    with page.expect_response(lambda r: "/available-slots?" in r.url and "date=" + day in r.url):
        modal.locator("#rescheduleDate" if role == "customer" else "#rescheduleDateAdmin").fill(day)
    expect(submit).to_be_disabled()
    expect(modal.get_by_role("region", name="Thay đổi lịch hẹn")).to_contain_text("Chưa chọn giờ hợp lệ")
    page.keyboard.press("Escape")
    modal.get_by_role("button", name="Tiếp tục chỉnh sửa", exact=True).click()
    expect(note).to_have_value("Keep my draft")
    modal.locator("button").filter(has_text="KTV trống" if role == "customer" else "KTV rảnh").first.click()
    expect(submit).to_be_enabled()



def test_completed_booking_cannot_get_new_suggestions_or_be_resubmitted(scenario, api_helper):
    s = scenario
    page, modal, booking = open_edit(s, "customer", api_helper)
    expect(modal.get_by_role("button", name="Xác nhận đổi lịch", exact=True)).to_be_enabled()
    for status in ("CONFIRMED", "COMPLETED"):
        s["call"]("PATCH", "/bookings/" + booking["id"] + "/status", json={"status": status})
    day = (datetime.now(timezone(timedelta(hours=7))) + timedelta(days=9)).date().isoformat()
    modal.locator("#rescheduleDate").fill(day)
    expect(modal.get_by_role("alert")).to_contain_text("Chỉ được sửa lịch PENDING/CONFIRMED")
    expect(modal.get_by_role("button", name="Xác nhận đổi lịch", exact=True)).to_be_disabled()
