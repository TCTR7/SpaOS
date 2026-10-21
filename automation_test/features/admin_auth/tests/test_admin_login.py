from playwright.sync_api import Page, expect

from common_setup.config import config
from features.admin_auth.pages.login_page import AdminLoginPage


def test_admin_login_success(unauthenticated_page: Page) -> None:
    login_page = AdminLoginPage(unauthenticated_page)
    login_page.open()
    login_page.login(
        config.tenant_slug, config.admin_phone, config.admin_password
    )
    assert login_page.last_login_status == 200
    login_page.wait_for_url_contains("/admin/dashboard")
    expect(
        unauthenticated_page.get_by_role("heading", name="Tổng quan", exact=False)
    ).to_be_visible()


def test_admin_login_wrong_password_or_phone(unauthenticated_page: Page) -> None:
    login_page = AdminLoginPage(unauthenticated_page)
    login_page.open()

    # Wrong password
    login_page.login(config.tenant_slug, config.admin_phone, "WrongPass999")
    assert login_page.last_login_status == 401
    expect(unauthenticated_page.get_by_text("Sai số điện thoại hoặc mật khẩu", exact=True)).to_be_visible()

    # Non-existent phone number
    login_page.login(
        config.tenant_slug, "099999999999999", config.admin_password
    )
    assert login_page.last_login_status == 401
    expect(unauthenticated_page.get_by_text("Sai số điện thoại hoặc mật khẩu", exact=True)).to_be_visible()


def test_unauthenticated_redirect_to_login(unauthenticated_page: Page) -> None:
    login_page = AdminLoginPage(unauthenticated_page)
    login_page.navigate("/admin/services")
    login_page.wait_for_url_contains("/admin/login")
    expect(
        unauthenticated_page.get_by_role("heading", name="Đăng nhập", exact=True)
    ).to_be_visible()
