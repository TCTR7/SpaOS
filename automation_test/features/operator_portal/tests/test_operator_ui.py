"""Real browser + disposable API/database; no operator seeded in the application database."""
from playwright.sync_api import expect
from common_setup.config import config
from features.operator_portal.pages.operator_page import OperatorPage

def test_operator_login_uses_separate_session(operator_ui):
    page_for, _ = operator_ui
    page = page_for()
    ui = OperatorPage(page)
    ui.login()
    expect(page.get_by_role("heading", name="Cấp tài khoản chủ spa", exact=True)).to_be_visible()
    assert page.evaluate("sessionStorage.getItem('spaos_operator_token')") is not None
    assert page.evaluate("localStorage.getItem('spaos_admin_token')") is None
    page.get_by_role("button", name="Đăng xuất", exact=True).click()
    expect(page).to_have_url(config.frontend_url + "/operator/login")
    assert page.evaluate("sessionStorage.getItem('spaos_operator_token')") is None

def test_operator_creates_vietnamese_owner_then_owner_logs_in(operator_ui):
    page_for, _ = operator_ui
    page = page_for()
    ui = OperatorPage(page)
    ui.login()
    phone = ui.fill_owner()
    with page.expect_response(lambda r: r.url.endswith("/operator/owners") and r.request.method == "POST") as created:
        ui.submit()
    assert created.value.status == 201
    expect(page.get_by_test_id("owner-created")).to_contain_text("Trần Cao Trung")
    expect(page.get_by_test_id("provision-row").filter(has_text=phone)).to_have_count(1)
    expect(page.locator("#ownerPassword")).to_have_value("")
    expect(page.locator("#ownerConfirm")).to_have_value("")
    owner = page_for()
    owner.goto(config.frontend_url + "/admin/login")
    owner.locator("#phone").fill(phone)
    owner.locator("#password").fill("OwnerQa@123")
    owner.get_by_role("button", name="Đăng nhập vào Dashboard", exact=True).click()
    expect(owner).to_have_url(config.frontend_url + "/admin/dashboard")
    expect(owner.get_by_role("heading", name="Tổng quan Chi nhánh Đà Nẵng")).to_be_visible()
    expect(owner.get_by_test_id("branch-dashboard")).to_be_visible()
    assert owner.evaluate("sessionStorage.getItem('spaos_operator_token')") is None

def test_operator_retry_preserves_request_after_lost_response(operator_ui):
    page_for, backend = operator_ui
    page = page_for()
    ui = OperatorPage(page)
    ui.login()
    phone = ui.fill_owner()
    calls = []
    def lose_first(route):
        calls.append(route.request.post_data_json)
        response = route.fetch(url=backend+"/api/v1/operator/owners")
        assert response.status == 201
        if len(calls) == 1:
            route.abort("failed")
        else:
            route.fulfill(response=response)
    page.route("**/api/v1/operator/owners", lose_first)
    ui.submit()
    expect(page.get_by_role("button", name="Thử lại tạo tài khoản", exact=True)).to_be_enabled()
    expect(page.locator("#ownerName")).to_be_disabled()
    page.get_by_role("button", name="Thử lại tạo tài khoản", exact=True).click()
    expect(page.get_by_test_id("owner-created")).to_be_visible()
    assert len(calls) == 2 and calls[0] == calls[1]
    expect(page.get_by_test_id("provision-row").filter(has_text=phone)).to_have_count(1)
