from datetime import datetime, timedelta, timezone

import pytest
from playwright.sync_api import expect
from features.client_pwa_booking.pages.booking_wizard_page import BookingWizardPage


def future_day():
    return (datetime.now(timezone(timedelta(hours=7))) + timedelta(days=7)).date().isoformat()


def assert_no_overflow(page):
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    assert page.get_by_role("navigation", name="Các bước đặt lịch").evaluate(
        "el => el.scrollWidth <= el.clientWidth + 1")


@pytest.mark.parametrize("width", [360, 390, 1366])
def test_three_steps_require_explicit_time_and_back_keeps_draft(scenario, width):
    s = scenario
    name = "QA Treatment " + "LongServiceName" * 12
    s["call"]("PATCH", "/services/" + s["service"]["id"], json={"name": name})
    s["call"]("PATCH", "/staff/" + s["staff"]["id"], json={"full_name": "QA Staff " + "LongStaffName" * 15})
    page = s["page"]()
    page.set_viewport_size({"width": width, "height": 844})
    wizard = BookingWizardPage(page)
    wizard.open_wizard(s["slug"])
    steps = page.get_by_role("navigation", name="Các bước đặt lịch")
    expect(steps.get_by_role("button")).to_have_count(3)
    expect(steps.get_by_role("button", name="3. Xác nhận", exact=True)).to_be_disabled()
    service = page.get_by_role("button").filter(has_text=name)
    service.focus()
    page.keyboard.press("Space")
    expect(service).to_have_attribute("aria-pressed", "true")
    assert_no_overflow(page)
    page.get_by_role("button", name="Tiếp tục", exact=True).click()
    expect(page.get_by_role("button", name="Ngày trước", exact=True)).to_be_disabled()
    today = page.locator("#wizDate").input_value()
    page.locator("#wizDate").fill("2000-01-01")
    expect(page.locator("#wizDate")).to_have_value(today)
    with page.expect_response(lambda r: "/available-slots?" in r.url and "date=" + future_day() in r.url):
        page.locator("#wizDate").fill(future_day())
    slot = page.locator("button:has-text('KTV trống')").nth(3)
    expect(slot).to_be_visible()
    expect(page.get_by_role("button", name="Tiếp tục", exact=True)).to_be_disabled()
    expect(steps.get_by_role("button", name="3. Xác nhận", exact=True)).to_be_disabled()
    assert_no_overflow(page)
    slot.click()
    chosen = slot.text_content()
    page.get_by_role("button", name="Tiếp tục", exact=True).click()
    page.locator("#wizNote").fill("Keep note across steps")
    assert_no_overflow(page)
    page.get_by_role("button", name="Quay lại", exact=True).click()
    expect(page.locator('button[aria-pressed="true"]').filter(has_text="KTV trống")).to_have_text(chosen)
    page.get_by_role("button", name="Quay lại", exact=True).click()
    expect(service).to_have_attribute("aria-pressed", "true")
    steps.get_by_role("button", name="3. Xác nhận", exact=True).click()
    expect(page.locator("#wizNote")).to_have_value("Keep note across steps")


def test_package_confirmation_cannot_double_submit_or_leave_while_pending(scenario):
    s = scenario
    page = s["page"]()
    wizard = BookingWizardPage(page)
    wizard.open_wizard(s["slug"])
    package = page.get_by_role("button").filter(has_text="QA One Session")
    package.click()
    page.get_by_role("button", name="Tiếp tục", exact=True).click()
    wizard.step2_select_date_and_first_slot(future_day())
    expect(page.get_by_text("Dùng 1 buổi trong thẻ", exact=True)).to_be_visible()
    held = []
    def hold(route):
        if route.request.method == "POST":
            held.append(route)
            page.evaluate("window.qaBookingHeld = true")
        else:
            route.continue_()
    page.route("**/api/v1/bookings", hold)
    submit = page.get_by_role("button", name="Xác nhận Đặt lịch", exact=True)
    submit.evaluate("button => { button.click(); button.click(); }")
    page.wait_for_function("window.qaBookingHeld === true")
    expect(page.get_by_role("button", name="Đang gửi lịch hẹn...", exact=True)).to_be_disabled()
    expect(page.get_by_role("button", name="Quay lại", exact=True)).to_be_disabled()
    expect(page.get_by_role("navigation", name="Các bước đặt lịch").get_by_role("button").first).to_be_disabled()
    assert len(held) == 1
    with page.expect_response(lambda r: r.url.endswith("/bookings") and r.request.method == "POST") as response:
        held[0].fulfill(response=held[0].fetch())
    assert response.value.status == 201
    page.wait_for_url("**/appointments?booked=1")
    bookings = s["call"]("GET", "/bookings")
    assert len(bookings) == 1
    assert bookings[0]["items"][0]["customer_package_id"] == s["package"]["id"]
    assert float(bookings[0]["total_price"]) == 0
    packages = s["call"]("GET", "/customer-packages/me", headers={"Authorization": "Bearer " + s["token"]})
    assert packages[0]["reserved_sessions"] == 1 and packages[0]["used_sessions"] == 0
