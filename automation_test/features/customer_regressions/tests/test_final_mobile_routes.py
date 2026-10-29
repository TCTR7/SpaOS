import pytest
from playwright.sync_api import expect
from common_setup.config import config


def fits(page):
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), page.url


@pytest.mark.parametrize("width", [320, 360, 1366])
@pytest.mark.parametrize("admin", [False, True])
def test_notifications_fit_retry_many_long_rows_back_and_focus(scenario, width, admin):
    s = scenario
    page = s["page"](s["admin"] if admin else s["token"], admin)
    page.set_viewport_size({"width": width, "height": 600})
    pattern = "**/api/v1/notifications?*"
    page.route(pattern, lambda r: r.fulfill(status=503, json={"detail": "QA unavailable"}))
    page.goto(config.frontend_url + "/admin/dashboard" if admin else s["url"] + "/profile")
    opener = page.get_by_role("button", name="Thông báo" if admin else "Thông báo lịch hẹn", exact=True)
    opener.click()
    modal = page.get_by_role("dialog", name="Bảng thông báo", exact=True)
    expect(modal.get_by_role("alert")).to_contain_text("Không tải được thông báo")
    expect(modal.get_by_text("Chưa có thông báo", exact=False)).to_have_count(0)
    page.unroute(pattern)
    title = "LongNotificationTitle" * 18
    page.route(pattern, lambda r: r.fulfill(json={"unread_count": 30, "items": [dict(
        id=str(i), title=title, body="LongCustomerAndTreatment" * 24, is_read=False,
        created_at="2026-10-19T00:00:00Z", type="BOOKING_CONFIRMED") for i in range(30)]}))
    modal.get_by_role("button", name="Làm mới thông báo", exact=True).click()
    expect(modal.get_by_text(title, exact=True)).to_have_count(30)
    expect(modal.get_by_role("alert")).to_have_count(0)
    fits(page)
    assert modal.evaluate("e=>Array.from(e.querySelectorAll('*')).every(n=>n.getBoundingClientRect().right<=innerWidth+1 && n.getBoundingClientRect().left>=-1)")
    page.evaluate("history.back()")
    expect(modal).to_have_count(0)
    expect(opener).to_be_focused()
    opener.click()
    page.keyboard.press("Escape")
    expect(modal).to_have_count(0)
    expect(opener).to_be_focused()
    page.unroute(pattern)
    page.route(pattern, lambda r: r.fulfill(json={"unread_count": 0, "items": []}))
    opener.click()
    expect(modal.get_by_text("Chưa có thông báo", exact=False)).to_be_visible()


@pytest.mark.parametrize("width", [320, 390, 768, 1366])
def test_dashboard_scoped_actions_metrics_error_retry_and_read_only_all(scenario, width):
    s = scenario
    s["call"]("POST","/branches",json={"name":"Second QA branch"})
    s["call"]("PATCH", "/tenants/me", json={"name": "LongBranchName" * 15})
    page = s["page"](s["admin"], True)
    page.set_viewport_size({"width": width, "height": 844})
    pattern = "**/api/v1/dashboard?*"
    page.route(pattern, lambda r: r.fulfill(status=503, json={"detail": "QA dashboard unavailable"}))
    page.goto(config.frontend_url + "/admin/dashboard")
    expect(page.get_by_role("main").get_by_role("alert")).to_contain_text("Chưa thể xử lý yêu cầu. Vui lòng thử lại sau.")
    page.unroute(pattern)
    page.get_by_role("button", name="Thử tải lại tổng quan", exact=True).click()
    metrics = page.get_by_test_id("branch-dashboard")
    expect(metrics).to_be_visible()
    expect(metrics).to_have_attribute("aria-busy", "false")
    expect(page.get_by_test_id("dashboard-appointments")).not_to_have_attribute("open", "")
    page.get_by_test_id("dashboard-outstanding").locator("summary").click()
    expect(page.get_by_role("main").get_by_role("link", name="Thu tiền", exact=True)).to_be_visible()
    fits(page)
    page.locator("#activeBranch").select_option("all")
    expect(page.get_by_role("heading", name="Tổng quan", exact=True)).to_be_visible()
    expect(page.get_by_text("Chọn một chi nhánh trên thanh đầu trang để xử lý lịch hẹn hoặc thu tiền.", exact=True)).to_be_visible()
    page.get_by_test_id("dashboard-outstanding").locator("summary").click()
    expect(page.get_by_role("main").get_by_role("link", name="Thu tiền", exact=True)).to_have_count(0)
    fits(page)
    page.get_by_role("link", name="Tổng quan", exact=True).click()
    expect(page.locator("#activeBranch")).not_to_have_value("all")
    page.go_back()
    expect(page.locator("#activeBranch")).to_have_value("all")
    page.go_forward()
    expect(page.locator("#activeBranch")).not_to_have_value("all")


@pytest.mark.parametrize("width", [320, 390, 768, 1366])
def test_remaining_public_auth_and_admin_routes_long_errors_labels(scenario, width):
    s = scenario
    long_name = "LongSpaBranch" * 18
    s["call"]("PATCH", "/tenants/me", json={"name": long_name})
    page = s["page"]("", True)
    page.set_viewport_size({"width": width, "height": 844})
    s["call"]("POST","/branches",json={"name":"Second QA public branch"})
    pattern = "**/api/v1/branches/public?*"
    page.route(pattern, lambda r: r.fulfill(status=503, json={"detail": "QA unavailable"}))
    page.goto(config.frontend_url + "/s/"+s["slug"]+"/")
    expect(page.get_by_role("main").get_by_role("alert")).to_be_visible()
    page.unroute(pattern)
    page.get_by_role("button", name="Thử tải lại chi nhánh", exact=True).click()
    expect(page.locator('a[href="/s/'+s["slug"]+'/b/' + s["slug"] + '"]')).to_contain_text(long_name)
    fits(page)
    detail = "LongLoginFailure" * 30
    page.route("**/api/v1/auth/login", lambda r: r.fulfill(status=503, json={"detail": detail}))
    for path, phone, password, submit in [
        ("/admin/login", "phone", "password", "Đăng nhập"),
        ("/" + s["slug"] + "/login", "custPhone", "custPassword", "Đăng nhập"),
    ]:
        page.goto(config.frontend_url + path)
        page.locator("#" + phone).fill("0901234567")
        page.locator("#" + password).fill("NeverLogged@123")
        page.get_by_role("button", name=submit, exact=True).click()
        expect(page.get_by_role("alert").filter(has_text="Chưa thể xử lý yêu cầu. Vui lòng thử lại sau.")).to_be_visible()
        fits(page)
        if path == "/admin/login":
            expect(page.locator('a[href="/admin/register-tenant"]')).to_have_count(0)
    page.goto(s["url"] + "/register")
    expect(page.get_by_label("Họ và tên của bạn", exact=True)).to_be_visible()
    expect(page.get_by_role("main").get_by_text(long_name, exact=True)).to_be_visible()
    fits(page)
    admin = s["page"](s["admin"], True)
    admin.set_viewport_size({"width": width, "height": 844})
    for path in ["branches", "settings"]:
        admin.goto(config.frontend_url + "/admin/" + path)
        expect(admin.locator("#activeBranch")).to_be_attached()
        if path == "settings":
            expect(admin.locator("#spaName")).to_have_value(long_name)
        else:
            expect(admin.get_by_label("Tên chi nhánh", exact=True)).to_be_visible()
        fits(admin)
        admin.evaluate("document.documentElement.classList.add('dark')")
        fits(admin)


def test_settings_failed_load_cannot_save_defaults_and_retry_recovers(scenario):
    s = scenario
    page = s["page"](s["admin"], True)
    pattern = "**/api/v1/tenants/me"
    page.route(pattern, lambda r: r.fulfill(status=503, json={"detail": "QA settings unavailable"}))
    page.goto(config.frontend_url + "/admin/settings")
    expect(page.get_by_role("main").get_by_role("alert")).to_contain_text("Chưa thể xử lý yêu cầu. Vui lòng thử lại sau.")
    expect(page.get_by_role("button", name="Lưu thay đổi", exact=True)).to_be_disabled()
    page.unroute(pattern)
    page.get_by_role("button", name="Thử tải lại cấu hình", exact=True).click()
    expect(page.locator("#spaName")).to_have_value("QA Spa")
    expect(page.get_by_role("button", name="Lưu thay đổi", exact=True)).to_be_enabled()
