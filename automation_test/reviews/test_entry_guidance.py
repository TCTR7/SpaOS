"""First-use onboarding, manual help and PWA identity on disposable QA data."""
import pytest
from playwright.sync_api import expect
from common_setup.config import config
from features.customer_regressions.conftest import scenario


def test_single_branch_redirect_and_management_entry(scenario):
    s = scenario
    page = s["page"]("", True)
    page.route("**/api/v1/branches/public", lambda r: r.fulfill(json={"brand_name": "QA Spa", "branches": [{"id": "one", "name": "QA Spa", "slug": s["slug"]}]}))
    page.goto(config.frontend_url + "/")
    expect(page).to_have_url(s["url"])
    page.get_by_role("button", name="Thêm", exact=True).click()
    page.get_by_role("link", name="Đăng nhập quản lý", exact=True).click()
    expect(page).to_have_url(config.frontend_url + "/admin/login")
    expect(page.get_by_role("link", name="Quản trị hệ thống", exact=True)).to_have_attribute("href", "/operator/login")


@pytest.mark.parametrize("admin,ua", [(True, "Android"), (False, "iPhone")])
def test_role_guides_and_manifest(scenario, admin, ua):
    s = scenario
    page = s["page"](s["admin"] if admin else s["token"], admin, show_guide=True)
    page.add_init_script("Object.defineProperty(navigator,'userAgent',{get:()=>" + repr(ua) + "});")
    page.goto(config.frontend_url + "/admin/dashboard" if admin else s["url"])
    welcome = page.get_by_role("dialog", name="Bắt đầu sử dụng SpaOS", exact=True)
    expect(welcome).to_be_visible()
    expect(page.get_by_role("button", name="Hướng dẫn & Cài ứng dụng", exact=True)).to_have_count(0)
    expected = "/admin/app.webmanifest" if admin else "/" + s["slug"] + "/app.webmanifest"
    expect(page.locator('link[rel="manifest"]')).to_have_attribute("href", expected)
    data = page.request.get(config.frontend_url + expected).json()
    assert data["start_url"] == ("/admin" if admin else "/" + s["slug"])
    assert data["start_url"].startswith(data["scope"])
    welcome.get_by_role("button").filter(has_text="Xem hướng dẫn nhanh").click()
    dialog = page.get_by_role("dialog", name="Trợ giúp & Cài ứng dụng", exact=True)
    expect(dialog).to_contain_text("Thiết lập spa" if admin else "Tìm thời gian phù hợp")
    dialog.get_by_role("button", name="Tiếp theo", exact=True).click()
    expect(dialog).to_contain_text("Bước 2/3")
    dialog.get_by_role("button", name="Tiếp theo", exact=True).click()
    dialog.get_by_role("button", name="Hoàn tất hướng dẫn", exact=True).click()
    expect(dialog).not_to_be_visible()
    page.goto(config.frontend_url + "/admin/help" if admin else s["url"] + "/help")
    page.get_by_role("button", name="Cài ứng dụng", exact=True).click()
    expect(page.get_by_text("Thêm ứng dụng vào màn hình chính", exact=True)).to_be_visible()
    expect(page.locator("main")).to_contain_text("Chrome/Android" if admin else "Safari trên iPhone/iPad")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")


def test_install_prompt_is_only_on_user_action(scenario):
    s = scenario
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/help")
    page.get_by_role("button", name="Cài ứng dụng", exact=True).click()
    page.evaluate("""() => {window.qaPrompts=0;const e=new Event('beforeinstallprompt',{cancelable:true});e.prompt=async()=>{window.qaPrompts++;};e.userChoice=Promise.resolve({outcome:'dismissed'});window.dispatchEvent(e);}""")
    install = page.get_by_role("button", name="Cài ứng dụng trên thiết bị", exact=True)
    expect(install).to_be_visible()
    assert page.evaluate("window.qaPrompts") == 0
    install.click()
    assert page.evaluate("window.qaPrompts") == 1
    expect(install).to_have_count(0)


@pytest.mark.parametrize("dismiss", ["Để sau", "Đóng", "Escape"])
def test_dismissal_survives_reload_navigation_and_branch_switch(scenario, dismiss):
    s = scenario
    branch = s["call"]("POST", "/branches", json={"name": "QA Second"})["tenant"]
    page = s["page"](s["admin"], True, show_guide=True)
    page.goto(config.frontend_url + "/admin/dashboard")
    welcome = page.get_by_role("dialog", name="Bắt đầu sử dụng SpaOS", exact=True)
    expect(welcome).to_be_visible()
    if dismiss == "Escape":
        page.keyboard.press("Escape")
    else:
        welcome.get_by_role("button", name=dismiss, exact=True).click()
    page.reload()
    expect(page.locator("#activeBranch")).to_be_visible()
    expect(welcome).to_have_count(0)
    page.goto(config.frontend_url + "/admin/customers")
    expect(page.get_by_role("heading", name="Khách hàng & Thẻ liệu trình", exact=True)).to_be_visible()
    expect(welcome).to_have_count(0)
    page.locator("#activeBranch").select_option(branch["id"])
    expect(page.locator("#activeBranch")).to_have_value(branch["id"])
    expect(welcome).to_have_count(0)
    page.get_by_role("button", name="Thêm", exact=True).click()
    page.get_by_role("link", name="Trợ giúp & Cài ứng dụng", exact=True).click()
    expect(page.get_by_role("heading", name="Trợ giúp & Cài ứng dụng", exact=True)).to_be_visible()


def test_staff_first_use_and_already_installed_help(scenario, api_helper):
    s = scenario
    token = api_helper.login(s["slug"], s["staff"]["phone_number"], "Staff@123")["access_token"]
    page = s["page"](token, True, show_guide=True)
    page.add_init_script("""window.matchMedia = ((original) => (query) => query === '(display-mode: standalone)' ? {matches:true, addEventListener(){},removeEventListener(){}} : original(query))(window.matchMedia.bind(window));""")
    page.goto(config.frontend_url + "/admin/bookings")
    welcome = page.get_by_role("dialog", name="Bắt đầu sử dụng SpaOS", exact=True)
    welcome.get_by_role("button").filter(has_text="Xem hướng dẫn nhanh").click()
    dialog = page.get_by_role("dialog", name="Trợ giúp & Cài ứng dụng", exact=True)
    expect(dialog).to_contain_text("Xem công việc được giao")
    dialog.get_by_role("button", name="Cài ứng dụng", exact=True).click()
    expect(dialog).to_contain_text("Bạn đang dùng ứng dụng đã cài.")
    expect(dialog.get_by_role("button", name="Cài ứng dụng trên thiết bị")).to_have_count(0)
