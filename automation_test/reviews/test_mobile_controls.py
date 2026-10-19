"""Focused acceptance for mobile targets and selected-slot brand contrast."""
from datetime import datetime, timedelta, timezone

import pytest
from playwright.sync_api import expect

from common_setup.config import config
from features.customer_regressions.conftest import scenario


def test_calendar_toolbar_fits_320px(scenario):
    s = scenario
    booking = s["book"]()
    day = datetime.fromisoformat(booking["start_time"].replace("Z", "+00:00")).astimezone(
        timezone(timedelta(hours=7))).date().isoformat()
    page = s["page"](s["admin"], True)
    page.set_viewport_size({"width": 320, "height": 844})
    page.goto(config.frontend_url + "/admin/bookings")
    with page.expect_response(lambda r: "/bookings?" in r.url and "date_from=" + day in r.url):
        page.locator("input[type=date]").first.fill(day)
    expect(page.get_by_test_id("booking-card-" + booking["id"])).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")


@pytest.mark.parametrize("width", [320, 390, 1366])
def test_login_controls_remain_readable(unauthenticated_page, width):
    page = unauthenticated_page
    page.set_viewport_size({"width": width, "height": 844})
    page.goto(config.frontend_url + "/admin/login")
    phone = page.get_by_label("Số điện thoại", exact=True)
    password = page.get_by_label("Mật khẩu", exact=True)
    expect(phone).to_be_visible()
    expect(password).to_be_visible()
    submit = page.locator('button[type="submit"]')
    expect(submit).to_be_enabled()
    if width < 640:
        for control in (phone, password, submit):
            assert control.bounding_box()["height"] >= 44
        assert phone.evaluate("e => parseFloat(getComputedStyle(e).fontSize)") >= 16
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")


@pytest.mark.parametrize("color,background,foreground", [
    ("#ffff00", "rgb(255, 255, 0)", "rgb(0, 0, 0)"),
    ("#fffffe", "rgb(255, 255, 254)", "rgb(0, 0, 0)"),
    ("#000080", "rgb(0, 0, 128)", "rgb(255, 255, 255)"),
    ("#000000", "rgb(0, 0, 0)", "rgb(255, 255, 255)"),
])
def test_selected_slot_secondary_text_uses_brand_foreground(scenario, color, background, foreground):
    s = scenario
    page = s["page"]()
    # CustomerShell must receive the brand too; it overrides html variables.
    page.route("**/api/v1/branding", lambda route: route.fulfill(
        json={"theme_color": color, "configured": True}))
    page.goto(s["url"] + "/book?service_id=" + s["service"]["id"])
    page.get_by_role("button", name="Tiếp tục", exact=True).click()
    page.get_by_role("button", name="Tiếp tục", exact=True).click()
    day = (datetime.now(timezone(timedelta(hours=7))) + timedelta(days=5)).date().isoformat()
    with page.expect_response(lambda r: "/bookings/available-slots?" in r.url and "date=" + day in r.url):
        page.locator("#wizDate").fill(day)
    slot = page.locator("button").filter(has_text="KTV trống").first
    expect(slot).to_be_visible()
    slot.click()
    main = slot.locator("span").first
    secondary = slot.locator("span").last
    expect(slot).to_have_attribute("aria-pressed", "true")
    expect(slot).to_have_css("background-color", background)
    expect(main).to_have_css("color", foreground)
    expect(secondary).to_have_css("color", foreground)
    slot.focus()
    expect(slot).to_be_focused()


@pytest.mark.parametrize("with_extra_service", [False, True], ids=["package-only", "mixed"])
def test_package_copy_preserves_extra_charge(scenario, with_extra_service):
    s = scenario
    if with_extra_service:
        s["call"]("POST", "/services", json={"name": "QA Extra Service", "price": 125000,
                  "duration_minutes": 15, "is_package": False, "total_sessions": 1})
    page = s["page"]()
    page.goto(s["url"] + "/book")
    package_card = page.get_by_text("QA One Session", exact=True).locator("../..")
    expect(package_card).to_contain_text("Dùng 1 buổi trong thẻ")
    expect(package_card).not_to_contain_text("0₫")
    package_card.click()
    expect(package_card).to_contain_text("Đã chọn 1 buổi")
    if with_extra_service:
        page.get_by_text("QA Extra Service", exact=True).click()
    page.get_by_role("button", name="Tiếp tục", exact=True).click()
    page.get_by_role("button", name="Tiếp tục", exact=True).click()
    day = (datetime.now(timezone(timedelta(hours=7))) + timedelta(days=5)).date().isoformat()
    with page.expect_response(lambda r: "/bookings/available-slots?" in r.url and "date=" + day in r.url):
        page.locator("#wizDate").fill(day)
    page.locator("button").filter(has_text="KTV trống").first.click()
    page.get_by_role("button", name="Tiếp tục", exact=True).click()
    expect(page.get_by_text("Dùng 1 buổi trong thẻ", exact=True)).to_be_visible()
    amount = page.get_by_text("Dự kiến thu thêm ngoài thẻ:", exact=True).locator("..")
    expect(amount).to_contain_text("125.000" if with_extra_service else "0")
    expect(page.get_by_text("Trừ thẻ (0 ₫)", exact=True)).to_have_count(0)
