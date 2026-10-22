from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit
import pytest
from playwright.sync_api import expect
from common_setup.config import config
from features.client_pwa_booking.pages.booking_wizard_page import BookingWizardPage
from features.ui_quality.tests.test_dialog_workflows import manual


def day_after(days):
    return (datetime.now(timezone(timedelta(hours=7))) + timedelta(days=days)).date().isoformat()


@pytest.mark.parametrize("status", [404, 503, "network"])
def test_public_tenant_not_found_is_distinct_from_outage_and_can_retry(scenario, status):
    s = scenario
    page = s["page"]()
    pattern = "**/api/v1/public/tenants/" + s["slug"]
    page.route(pattern, lambda route: route.abort("internetdisconnected") if status == "network"
               else route.fulfill(status=status, json={"detail": "QA tenant unavailable"}))
    page.goto(s["url"])
    if status == 404:
        expect(page.get_by_role("heading", name="Không tìm thấy spa", exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="Thử lại", exact=True)).to_have_count(0)
    else:
        expect(page.get_by_role("alert").filter(has_text="Không tải được thông tin Spa")).to_be_visible()
        expect(page.get_by_role("heading", name="Không tìm thấy Spa", exact=False)).to_have_count(0)
        page.unroute(pattern)
        page.get_by_role("button", name="Thử lại", exact=True).click()
        expect(page.get_by_text("QA Treatment", exact=True)).to_be_visible()


def prepare_wizard(s):
    page = s["page"]()
    wizard = BookingWizardPage(page)
    wizard.open_wizard(s["slug"])
    wizard.step1_select_service_by_name("QA Treatment")
    wizard.step2_choose_auto_assign_staff()
    return page


@pytest.mark.parametrize("fault", ["503", "network", "empty"])
def test_wizard_slots_outage_differs_from_successful_empty(scenario, fault):
    s = scenario
    page = prepare_wizard(s)
    pattern = "**/api/v1/bookings/available-slots?*"
    def fail(route):
        if fault == "network":
            route.abort("internetdisconnected")
        elif fault == "empty":
            data = route.fetch().json()
            data["slots"] = []
            route.fulfill(json=data)
        else:
            route.fulfill(status=503, json={"detail": "QA slots unavailable"})
    page.route(pattern, fail)
    page.locator("#wizDate").fill(day_after(6))
    expect(page.get_by_role("button", name="Tiếp tục", exact=True)).to_be_disabled()
    if fault == "empty":
        expect(page.get_by_text("Rất tiếc, ngày", exact=False)).to_be_visible()
        expect(page.get_by_role("button", name="Thử lại khung giờ", exact=True)).to_have_count(0)
    else:
        expect(page.get_by_role("main").get_by_role("alert")).to_contain_text("Không tải được khung giờ")
        expect(page.get_by_text("Rất tiếc, ngày", exact=False)).to_have_count(0)
        page.unroute(pattern)
        page.get_by_role("button", name="Thử lại khung giờ", exact=True).click()
        expect(page.get_by_role("button", name="Tiếp tục", exact=True)).to_be_disabled()
        page.locator("button:has-text('KTV trống')").first.click()
        expect(page.get_by_role("button", name="Tiếp tục", exact=True)).to_be_enabled()


@pytest.mark.parametrize("old_status", [200, 503])
def test_late_slots_cannot_override_new_day(scenario, old_status):
    page = prepare_wizard(scenario)
    a, b = day_after(6), day_after(7)
    held = []
    def intercept(route):
        if parse_qs(urlsplit(route.request.url).query).get("date") == [a]:
            held.append((route, route.fetch() if old_status == 200 else None))
        else:
            route.continue_()
    page.route("**/api/v1/bookings/available-slots?*", intercept)
    with page.expect_request(lambda r: "/available-slots?" in r.url and "date=" + a in r.url):
        page.locator("#wizDate").fill(a)
    with page.expect_response(lambda r: "/available-slots?" in r.url and "date=" + b in r.url):
        page.locator("#wizDate").fill(b)
    expect(page.get_by_role("button", name="Tiếp tục", exact=True)).to_be_disabled()
    page.locator("button:has-text('KTV trống')").first.click()
    expect(page.get_by_role("button", name="Tiếp tục", exact=True)).to_be_enabled()
    assert held
    for route, response in held:
        with page.expect_response(lambda r: "/available-slots?" in r.url and "date=" + a in r.url) as old:
            route.fulfill(response=response) if response else route.fulfill(status=503, json={"detail": "QA stale slots error"})
        old.value.finished()
    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
    expect(page.locator("#wizDate")).to_have_value(b)
    expect(page.get_by_role("button", name="Tiếp tục", exact=True)).to_be_enabled()
    expect(page.get_by_role("main").get_by_role("alert")).to_have_count(0)
    page.get_by_role("button", name="Tiếp tục", exact=True).click()
    expect(page.get_by_text(datetime.fromisoformat(b).strftime("%d/%m/%Y"), exact=False)).to_be_visible()


def test_manual_slots_error_blocks_submission_and_retry_preserves_choice(scenario):
    page, modal, _ = manual(scenario)
    modal.locator("label").filter(has_text="QA One Session").get_by_role("checkbox").check()
    modal.locator("#modalDate").fill(day_after(6))
    first_slot = modal.locator("button").filter(has_text="KTV rảnh").nth(2)
    first_slot.click()
    chosen = first_slot.text_content()
    pattern = "**/api/v1/bookings/available-slots?*"
    page.route(pattern, lambda route: route.fulfill(status=503, json={"detail": "QA slots unavailable"}))
    # Changing staff forces validation while retaining the same valid time.
    modal.locator("#modalStaff").select_option(scenario["staff"]["id"])
    expect(modal.get_by_role("alert")).to_contain_text("Không tải được khung giờ")
    expect(modal.get_by_role("button", name="Xác nhận tạo lịch", exact=True)).to_be_disabled()
    expect(modal.get_by_text("Không còn khung giờ trống nào", exact=False)).to_have_count(0)
    page.unroute(pattern)
    modal.get_by_role("button", name="Thử lại khung giờ", exact=True).click()
    expect(modal.get_by_role("button", name="Xác nhận tạo lịch", exact=True)).to_be_enabled()
    expect(modal.locator("button.bg-primary").filter(has_text="KTV rảnh")).to_have_text(chosen)


@pytest.mark.parametrize("admin", [False, True], ids=["customer", "admin"])
@pytest.mark.parametrize("fault", ["503", "network", "empty"])
def test_reschedule_slots_outage_blocks_submit_and_retry_recovers(scenario, admin, fault):
    s = scenario
    booking = s["book"]()
    page = s["page"](s["admin"] if admin else s["token"], admin)
    if admin:
        page.goto(config.frontend_url + "/admin/bookings")
        page.locator("input[type=date]").first.fill(datetime.fromisoformat(booking["start_time"].replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=7))).date().isoformat())
        page.get_by_test_id("booking-card-" + booking["id"]).get_by_role("button", name="Chi tiết lịch hẹn", exact=True).click()
        page.get_by_role("dialog").get_by_role("button", name="Đổi ngày / giờ / KTV", exact=True).click()
    else:
        page.goto(s["url"] + "/appointments")
        page.get_by_role("button", name="Đổi ngày/giờ", exact=True).click()
    modal = page.get_by_role("dialog")
    pattern = "**/api/v1/bookings/" + booking["id"] + "/available-slots?*"
    def fail(route):
        if fault == "network":
            route.abort("internetdisconnected")
        elif fault == "empty":
            data = route.fetch().json()
            data["slots"] = []
            route.fulfill(json=data)
        else:
            route.fulfill(status=503, json={"detail": "QA reschedule slots unavailable"})
    page.route(pattern, fail)
    modal.locator("#rescheduleDateAdmin" if admin else "#rescheduleDate").fill(day_after(7))
    submit = modal.get_by_role("button", name="Xác nhận đổi lịch", exact=True)
    expect(submit).to_be_disabled()
    if fault == "empty":
        expect(modal.get_by_text("Không còn khung giờ trống nào", exact=False)).to_be_visible()
        expect(modal.get_by_role("button", name="Thử lại khung giờ", exact=True)).to_have_count(0)
    else:
        expect(modal.get_by_role("alert")).to_contain_text("Không tải được khung giờ")
        expect(modal.get_by_text("Không còn khung giờ trống nào", exact=False)).to_have_count(0)
        page.unroute(pattern)
        modal.get_by_role("button", name="Thử lại khung giờ", exact=True).click()
        expect(submit).to_be_disabled()
        modal.locator("button:has-text('KTV')").filter(has_text="00:00").first.click()
        expect(submit).to_be_enabled()
    current = s["call"]("GET", "/bookings/" + booking["id"])
    assert current["start_time"] == booking["start_time"]


def test_inline_login_preserves_selected_booking_draft(scenario):
    s = scenario
    page = s["page"]("")
    wizard = BookingWizardPage(page)
    wizard.open_wizard(s["slug"])
    wizard.step1_select_service_by_name("QA Treatment")
    wizard.step2_choose_auto_assign_staff()
    wizard.step2_select_date_and_first_slot(day_after(6))
    page.locator("#wizNote").fill("Keep draft through verification")
    page.locator("#wizAuthPhone").fill(s["phone"])
    page.locator("#wizAuthPassword").fill("Customer@123")
    page.get_by_role("button", name="Đăng nhập & Tiếp tục", exact=True).click()
    expect(page.get_by_role("button", name="Xác nhận Đặt lịch", exact=True)).to_be_enabled()
    expect(page.locator("#wizNote")).to_have_value("Keep draft through verification")
    expect(page.get_by_text("QA Treatment (30p)", exact=True)).to_be_visible()
