import re
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
    owner.get_by_role("button", name="Đăng nhập", exact=True).click()
    expect(owner).to_have_url(re.compile(re.escape(config.frontend_url)+r"/s/[^/]+/admin/dashboard$"))
    expect(owner.get_by_role("heading", name="Tổng quan",exact=True)).to_be_visible()
    expect(owner.get_by_test_id("branch-dashboard")).to_be_visible()
    assert owner.evaluate("sessionStorage.getItem('spaos_operator_token')") is None


def test_operator_provisions_independent_brand_colors_and_owner_can_update(operator_ui):
    page_for,backend=operator_ui
    page=page_for();ui=OperatorPage(page);ui.login()
    phone=ui.fill_owner()
    page.locator("#newSpaName").fill("Blue Brand QA")
    page.locator("#ownerThemeColor").fill("#2563eb")
    ui.submit()
    expect(page.get_by_test_id("owner-created")).to_be_visible()
    owner=page_for();owner.goto(config.frontend_url+"/admin/login")
    owner.locator("#phone").fill(phone);owner.locator("#password").fill("OwnerQa@123")
    # Full-document login navigation can discard the browser response body.
    auth=owner.request.post(backend+"/api/v1/auth/login",data={"phone_number":phone,"password":"OwnerQa@123"}).json()
    slug=auth["spa_slug"]
    owner.get_by_role("button",name="Đăng nhập",exact=True).click()
    expect(owner).to_have_url(config.frontend_url+"/s/"+slug+"/admin/dashboard")
    expect(owner.locator("html")).to_have_css("--brand-color","#2563eb")
    me=owner.request.get(backend+"/api/v1/auth/me",headers={"Authorization":"Bearer "+auth["access_token"]}).json()
    customer=page_for();customer.goto(config.frontend_url+"/s/"+slug+"/b/"+me["tenant"]["slug"])
    sign_in=customer.get_by_role("link",name="Đăng nhập",exact=True)
    expect(sign_in).to_have_css("background-color","rgb(37, 99, 235)")
    ui.fill_owner();page.locator("#newSpaName").fill("Pink Brand QA");page.locator("#ownerThemeColor").fill("#be185d");ui.submit()
    expect(page.get_by_test_id("owner-created")).to_contain_text("Trần Cao Trung")
    expect(page.locator("#ownerPassword")).to_have_value("")
    assert page.request.get(backend+"/api/v1/spas/public/"+slug).json()["theme_color"]=="#2563eb"
    changed=owner.request.patch(backend+"/api/v1/spas/me",headers={"Authorization":"Bearer "+auth["access_token"]},
        data={"name":"Blue Brand QA","theme_color":"#ffff00"})
    assert changed.status==200
    customer.reload();expect(sign_in).to_have_css("background-color","rgb(255, 255, 0)")
    expect(sign_in).to_have_css("color","rgb(0, 0, 0)")
    owner.reload();expect(owner.locator("html")).to_have_css("--brand-color","#ffff00")
    assert customer.locator('meta[name="theme-color"]').first.get_attribute("content")=="#ffff00"


def test_operator_keeps_per_spa_editor_available_for_next_owner(operator_ui):
    page_for,_=operator_ui
    page=page_for();ui=OperatorPage(page);ui.login()
    expect(page.locator("#ownerThemeColor")).to_be_visible()
    expect(page.locator("#deploymentColor")).to_have_count(0)
    ui.fill_owner();ui.submit()
    expect(page.get_by_test_id("owner-created")).to_be_visible()
    page.reload()
    expect(page.get_by_test_id("provision-row").first).to_be_visible()
    expect(page.locator("#ownerThemeColor")).to_be_visible()
    expect(page.locator("#deploymentColor")).to_have_count(0)

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
