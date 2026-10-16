from playwright.sync_api import Page, expect

from common_setup.config import config
from features.admin_auth.pages.login_page import AdminLoginPage


def test_admin_login_success(unauthenticated_page: Page) -> None:
    login_page = AdminLoginPage(unauthenticated_page)
    login_page.open()
    login_page.login(
        config.tenant_slug, config.admin_phone, config.admin_password
    )
    login_page.wait_for_url_contains("/admin/bookings")
    expect(
        unauthenticated_page.get_by_text("Lịch hẹn & Điều phối Kỹ thuật viên")
    ).to_be_visible()


def test_admin_login_wrong_password_or_slug(unauthenticated_page: Page) -> None:
    login_page = AdminLoginPage(unauthenticated_page)
    login_page.open()

    # Wrong password
    login_page.login(config.tenant_slug, config.admin_phone, "WrongPass999")
    expect(unauthenticated_page.locator("div.border-rose-300")).to_be_visible()

    # Non-existent tenant slug
    login_page.login(
        "spa-khong-ton-tai-999", config.admin_phone, config.admin_password
    )
    expect(unauthenticated_page.locator("div.border-rose-300")).to_be_visible()


def test_unauthenticated_redirect_to_login(unauthenticated_page: Page) -> None:
    login_page = AdminLoginPage(unauthenticated_page)
    login_page.navigate("/admin/services")
    login_page.wait_for_url_contains("/admin/login")
    expect(
        unauthenticated_page.get_by_text("Đăng nhập Quản trị SpaOS")
    ).to_be_visible()
