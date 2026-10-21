"""T11a navigation: real routes, dialog history, role visibility, no image collectors."""
import pytest
from playwright.sync_api import expect
from common_setup.config import config


def admin_page(s, width=390, height=844, token=None):
    page = s["page"](token or s["admin"], True)
    page.set_viewport_size({"width": width, "height": height})
    page.goto(config.frontend_url + "/admin/services")
    expect(page.locator("#activeBranch")).to_be_visible()
    return page


@pytest.mark.parametrize("width,height", [(320, 568), (360, 800), (390, 844), (667, 375)])
def test_admin_navigation_more_history_and_content_clearance(scenario, width, height):
    page = admin_page(scenario, width, height)
    nav = page.get_by_role("navigation", name="Điều hướng chính", exact=True)
    expect(nav.get_by_role("link")).to_have_count(4)
    more = nav.get_by_role("button", name="Thêm", exact=True)
    expect(more).to_have_attribute("aria-current", "page")
    expect(nav).to_be_in_viewport()
    page.reload()
    expect(more).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    assert page.locator("main").evaluate("e => parseFloat(getComputedStyle(e).paddingBottom)") >= nav.bounding_box()["height"]
    more.click()
    modal = page.get_by_role("dialog", name="Thêm", exact=True)
    expect(modal).to_be_visible()
    links = modal.get_by_role("link")
    assert set(links.evaluate_all("es=>es.map(e=>e.getAttribute('href'))")) == {
        "/admin/services", "/admin/staff", "/admin/reports", "/admin/settings", "/admin/branches", "/admin/account"}
    page.evaluate("history.back()")
    expect(modal).to_have_count(0)
    expect(more).to_be_focused()
    expect(page).to_have_url(config.frontend_url + "/admin/services")
    more.click()
    modal.get_by_role("link", name="Nhân sự & Ca làm việc", exact=True).click()
    expect(page).to_have_url(config.frontend_url + "/admin/staff")
    expect(modal).to_have_count(0)
    page.go_back()
    expect(page).to_have_url(config.frontend_url + "/admin/services")
    expect(modal).to_have_count(0)
    nav.get_by_role("link", name="Lịch hẹn", exact=True).click()
    expect(nav.get_by_role("link", name="Lịch hẹn", exact=True)).to_have_attribute("aria-current", "page")
    page.get_by_role("button", name="Tạo lịch hẹn", exact=True).click()
    form = page.get_by_role("dialog", name="Tạo lịch hẹn tại quầy", exact=True)
    expect(form).to_be_visible()
    # Native modal keeps bottom navigation inert and its footer operable.
    nav.get_by_role("link").first.evaluate("e=>e.focus()")
    assert form.evaluate("e=>e.contains(document.activeElement)")
    action = form.get_by_role("button", name="Xác nhận tạo lịch", exact=True).bounding_box()
    assert action["y"] + action["height"] <= height + 1


def test_staff_only_authorized_navigation(scenario, api_helper):
    s = scenario
    token = api_helper.login(s["slug"], s["staff"]["phone_number"], "Staff@123")["access_token"]
    page = admin_page(s, token=token)
    nav = page.get_by_role("navigation", name="Điều hướng chính", exact=True)
    expect(nav.get_by_role("link")).to_have_count(2)
    assert nav.get_by_role("link").evaluate_all("es=>es.map(e=>e.getAttribute('href'))") == ["/admin/bookings", "/admin/customers"]
    nav.get_by_role("button", name="Thêm", exact=True).click()
    modal = page.get_by_role("dialog", name="Thêm", exact=True)
    expect(modal.get_by_role("link")).to_have_count(3)
    assert set(modal.get_by_role("link").evaluate_all("es=>es.map(e=>e.getAttribute('href'))")) == {"/admin/services", "/admin/work-hours", "/admin/account"}


def test_more_escape_resize_and_desktop_navigation(scenario):
    page = admin_page(scenario)
    nav = page.get_by_role("navigation", name="Điều hướng chính", exact=True)
    more = nav.get_by_role("button", name="Thêm", exact=True)
    modal = page.get_by_role("dialog", name="Thêm", exact=True)
    more.click()
    page.keyboard.press("Escape")
    expect(modal).to_have_count(0)
    expect(more).to_be_focused()
    more.click()
    page.set_viewport_size({"width": 844, "height": 390})
    expect(modal).to_have_count(0)
    expect(nav).to_be_hidden()
    expect(page.locator("aside").get_by_role("link")).to_have_count(10)
    expect(page.locator("aside").get_by_role("link", name="Danh mục Dịch vụ", exact=True)).to_have_attribute("aria-current", "page")
    page.set_viewport_size({"width": 390, "height": 844})
    expect(more).to_be_visible()
    more.click()
    expect(modal).to_be_visible()


@pytest.mark.parametrize("width,height", [(320, 568), (667, 375), (1366, 768)])
def test_customer_navigation_active_reload_and_clearance(scenario, width, height):
    s = scenario
    page = s["page"]()
    page.set_viewport_size({"width": width, "height": height})
    page.goto(s["url"] + "/profile")
    nav = page.get_by_role("navigation", name="Điều hướng khách hàng", exact=True)
    expect(nav.get_by_role("link")).to_have_count(4)
    profile = nav.get_by_role("link", name="Thẻ & Hồ sơ", exact=True)
    expect(profile).to_have_attribute("aria-current", "page")
    page.reload()
    expect(profile).to_have_attribute("aria-current", "page")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    assert page.locator("main").evaluate("e=>parseFloat(getComputedStyle(e).paddingBottom)") >= nav.bounding_box()["height"]
    nav.get_by_role("link", name="Đặt lịch", exact=True).click()
    expect(nav.get_by_role("link", name="Đặt lịch", exact=True)).to_have_attribute("aria-current", "page")
    page.go_back()
    expect(profile).to_have_attribute("aria-current", "page")
