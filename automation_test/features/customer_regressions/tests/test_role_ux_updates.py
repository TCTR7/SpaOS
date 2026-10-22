"""Real QA flows for the role UX update; no live dataset mutation or proof files."""
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import pytest
from playwright.sync_api import expect
from common_setup.config import config


def login_customer(page, s):
    page.locator("#custPhone").fill(s["phone"])
    page.locator("#custPassword").fill("Customer@123")
    page.get_by_role("button", name="Đăng nhập", exact=True).click()


@pytest.mark.parametrize("destination", ["appointments", "profile"])
def test_login_returns_to_original_customer_task(scenario, destination):
    s = scenario
    page = s["page"]("")
    page.goto(s["url"] + "/" + destination)
    page.get_by_role("main").get_by_role("link", name="Đăng nhập" if destination == "profile" else "Đăng nhập ngay", exact=True).click()
    login_customer(page, s)
    expect(page).to_have_url(s["url"] + "/" + destination)


@pytest.mark.parametrize("destination", ["https://example.org/", "//example.org/", "/other-branch/profile", "/admin/payments"])
def test_login_rejects_external_and_other_branch_destinations(scenario, destination):
    s = scenario
    page = s["page"]("")
    page.goto(s["url"] + "/login?" + urlencode({"returnTo": destination}))
    login_customer(page, s)
    expect(page).to_have_url(s["url"] + "/book")


@pytest.mark.parametrize("kind", ["service", "package"])
def test_deep_link_goes_to_times_without_selecting_a_slot(scenario, kind):
    s = scenario
    page = s["page"]()
    if kind == "service":
        page.goto(s["url"])
        page.get_by_role("link", name="Xem giờ trống", exact=True).click()
    else:
        page.goto(s["url"] + "/profile")
        page.get_by_role("link", name="Dùng 1 buổi trong thẻ", exact=True).click()
    expect(page.locator("#wizDate")).to_be_visible()
    page.locator("#wizDate").fill((datetime.now(timezone(timedelta(hours=7))) + timedelta(days=7)).date().isoformat())
    expect(page.locator("button:has-text('KTV trống')").first).to_be_visible()
    expect(page.get_by_role("button", name="Tiếp tục", exact=True)).to_be_disabled()
    page.get_by_role("button", name="Đổi dịch vụ", exact=True).click()
    expect(page.get_by_role("button").filter(has_text="QA One Session" if kind == "package" else "QA Treatment")).to_have_attribute("aria-pressed", "true")


def test_cancel_can_be_abandoned_without_a_mutation(scenario):
    s = scenario
    booking = s["book"]()
    page = s["page"]()
    writes = []
    page.on("request", lambda r: writes.append(r.url) if r.method == "POST" and r.url.endswith("/cancel") else None)
    page.goto(s["url"] + "/appointments")
    page.get_by_role("button", name="Hủy lịch", exact=True).click()
    dialog = page.get_by_role("dialog", name="Hủy lịch hẹn này?", exact=True)
    expect(dialog).to_contain_text("QA Treatment")
    dialog.get_by_role("button", name="Giữ lịch hẹn", exact=True).click()
    expect(dialog).to_have_count(0)
    assert writes == []
    assert s["call"]("GET", "/bookings/" + booking["id"])["status"] == "PENDING"


def test_nearest_day_search_is_bounded_and_does_not_book(scenario):
    s = scenario
    page = s["page"]()
    seen, writes = [], []
    def empty(route):
        seen.append(route.request.url)
        route.fulfill(json={"date": "", "total_duration_minutes": 30, "buffer_minutes": 15, "slot_step_minutes": 15, "slots": []})
    page.route("**/api/v1/bookings/available-slots?*", empty)
    page.on("request", lambda r: writes.append(r.url) if r.method == "POST" else None)
    page.goto(s["url"] + "/book?service_id=" + s["service"]["id"])
    search = page.get_by_role("button", name="Tìm ngày còn chỗ trong 7 ngày tiếp theo", exact=True)
    expect(search).to_be_enabled()
    before = len(seen)
    search.click()
    expect(page.get_by_role("status").filter(has_text="Chưa tìm thấy giờ phù hợp")).to_be_visible()
    assert len(seen) - before == 7
    expect(page.get_by_role("button", name="Tiếp tục", exact=True)).to_be_disabled()
    assert writes == []


def test_customer_notification_opens_its_actual_booking(scenario):
    s = scenario
    booking = s["book"]()
    s["call"]("PATCH", "/bookings/" + booking["id"] + "/status", json={"status": "CONFIRMED"})
    page = s["page"]()
    page.goto(s["url"] + "/profile")
    page.get_by_role("button", name="Thông báo lịch hẹn", exact=True).click()
    page.get_by_role("dialog", name="Bảng thông báo", exact=True).get_by_role("button", name="Xem lịch hẹn", exact=True).click()
    expect(page).to_have_url(s["url"] + "/appointments?booking_id=" + booking["id"])
    expect(page.get_by_role("region", name="Lịch hẹn được mở", exact=True)).to_contain_text("QA Treatment")


def test_owner_can_find_free_times_without_creating_anything(scenario):
    s = scenario
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/bookings")
    page.get_by_role("button", name="Xem giờ trống", exact=True).click()
    page.locator("#availableService").select_option(s["service"]["id"])
    day = (datetime.now(timezone(timedelta(hours=7))) + timedelta(days=7)).date().isoformat()
    page.locator("#availableDay").fill(day)
    region = page.get_by_role("region", name="Tìm giờ trống", exact=True)
    expect(region.get_by_role("button").filter(has_text="QA Staff").first).to_be_visible()
    region.get_by_role("button").filter(has_text="QA Staff").first.click()
    modal = page.get_by_role("dialog", name="Tạo lịch hẹn tại quầy", exact=True)
    expect(modal).to_be_visible()
    expect(modal.get_by_role("group", name="Khách đặt lịch").get_by_role("button").first).to_have_attribute("aria-pressed", "false")
    expect(modal.locator("#modalDate")).to_have_value(day)
    assert s["call"]("GET", "/bookings") == []


def test_admin_notification_opens_detail_without_changing_status(scenario):
    s = scenario
    booking = s["book"]()
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/bookings?booking_id=" + booking["id"])
    expect(page.get_by_role("dialog", name="Chi tiết lịch hẹn", exact=True)).to_contain_text("QA Customer")
    assert s["call"]("GET", "/bookings/" + booking["id"])["status"] == "PENDING"


def test_late_nearest_day_result_cannot_override_new_date(scenario):
    s = scenario
    page = s["page"]()
    base = datetime.now(timezone(timedelta(hours=7))).date()
    first_day = (base + timedelta(days=1)).isoformat()
    new_day = (base + timedelta(days=10)).isoformat()
    held = []
    def intercept(route):
        if "date=" + first_day in route.request.url:
            held.append(route)
        else:
            route.fulfill(json={"date": "", "total_duration_minutes": 30, "buffer_minutes": 15, "slot_step_minutes": 15, "slots": []})
    page.route("**/api/v1/bookings/available-slots?*", intercept)
    page.goto(s["url"] + "/book?service_id=" + s["service"]["id"])
    search = page.get_by_role("button", name="Tìm ngày còn chỗ trong 7 ngày tiếp theo", exact=True)
    expect(search).to_be_enabled()
    with page.expect_request(lambda r: "/available-slots?" in r.url and "date=" + first_day in r.url):
        search.click()
    page.locator("#wizDate").fill(new_day)
    with page.expect_response(lambda r: "/available-slots?" in r.url and "date=" + first_day in r.url) as old:
        held[0].fulfill(json={"date": first_day, "total_duration_minutes": 30, "buffer_minutes": 15, "slot_step_minutes": 15,
                            "slots": [{"start_time": first_day + "T10:00:00+07:00", "end_time": first_day + "T10:30:00+07:00", "available_staff_ids": [s["staff"]["id"]]}]})
    old.value.finished()
    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
    expect(page.locator("#wizDate")).to_have_value(new_day)
    expect(page.get_by_role("button", name="Tiếp tục", exact=True)).to_be_disabled()


def test_notification_navigation_preserves_dirty_admin_settings(scenario):
    s = scenario
    s["book"]()
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/settings")
    name = page.locator("#spaName")
    expect(name).to_have_value("QA Spa")
    name.fill("Unsent branch name")
    page.get_by_role("button", name="Thông báo", exact=True).click()
    dialog = page.get_by_role("dialog", name="Bảng thông báo", exact=True)
    dialog.get_by_role("button", name="Xem lịch hẹn", exact=True).click()
    expect(dialog.get_by_role("alert")).to_contain_text("Hãy lưu hoặc hoàn tất công việc")
    expect(page).to_have_url(config.frontend_url + "/admin/settings")
    dialog.get_by_role("button", name="Đóng", exact=True).click()
    expect(name).to_have_value("Unsent branch name")


def test_owner_dashboard_links_preserve_selected_day_and_status(scenario):
    s = scenario
    booking = s["book"]()
    day = datetime.fromisoformat(booking["start_time"].replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=7))).date().isoformat()
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/dashboard")
    page.locator("#dashboardDay").fill(day)
    region = page.get_by_role("region", name="Công việc cần xử lý", exact=True)
    expect(region.locator('a[href^="/admin/bookings?booking_id="]').filter(has_text="QA Customer")).to_be_visible()
    region.get_by_role("link", name="Xem toàn bộ lịch chờ xác nhận", exact=True).click()
    expect(page.get_by_label("Ngày xem lịch", exact=True)).to_have_value(day)
    expect(page.get_by_role("combobox", name="Lọc trạng thái lịch", exact=True)).to_have_value("PENDING")
    expect(page.get_by_test_id("booking-card-" + booking["id"])).to_be_visible()


def test_report_quick_period_uses_vietnam_calendar(scenario):
    s = scenario
    page = s["page"](s["admin"], True)
    today = datetime.now(timezone(timedelta(hours=7))).date()
    page.goto(config.frontend_url + "/admin/reports")
    page.get_by_role("button", name="Tuần này", exact=True).click()
    expect(page.locator("#repStart")).to_have_value((today - timedelta(days=today.weekday())).isoformat())
    expect(page.locator("#repEnd")).to_have_value(today.isoformat())
    page.get_by_role("button", name="Tháng này", exact=True).click()
    expect(page.locator("#repStart")).to_have_value(today.replace(day=1).isoformat())
    page.get_by_role("button", name="Hôm nay", exact=True).click()
    expect(page.locator("#repStart")).to_have_value(today.isoformat())


def test_copy_week_hours_is_a_draft_until_explicit_save(scenario):
    s = scenario
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/staff")
    page.get_by_role("button").filter(has_text="QA Staff").first.click()
    monday = page.get_by_label("Giờ bắt đầu Thứ 2", exact=True)
    expect(monday).to_have_value("00:00")
    monday.fill("09:00")
    page.locator("details > summary").click()
    page.get_by_role("button", name="Áp dụng giờ Thứ 2 cho các ngày", exact=True).click()
    expect(page.get_by_label("Giờ bắt đầu Thứ 3", exact=True)).to_have_value("09:00")
    old = s["call"]("GET", "/staff/" + s["staff"]["id"] + "/schedules")
    assert all(row["start_time"].startswith("00:00") for row in old)
    with page.expect_response(lambda r: r.request.method == "PUT" and r.url.endswith("/schedules")) as saved:
        page.get_by_role("button", name="Lưu lịch tuần", exact=True).click()
    assert saved.value.status == 200
    assert all(row["start_time"].startswith("09:00") for row in saved.value.json())
