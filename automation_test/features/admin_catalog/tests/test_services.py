from playwright.sync_api import Page

from common_setup.api_helper import unique_suffix
from features.admin_catalog.pages.service_page import AdminServicePage


def test_admin_create_single_and_package_services(admin_page: Page) -> None:
    svc_page = AdminServicePage(admin_page)
    svc_page.open()

    single_name = f"Massage Đá Nóng E2E {unique_suffix()}"
    svc_page.create_single_service(single_name, duration=45, price=300000)
    svc_page.wait_for_text(single_name)

    pkg_name = f"Liệu Trình Trẻ Hóa E2E {unique_suffix()}"
    svc_page.create_package_service(
        pkg_name, duration=60, price=3500000, total_sessions=8
    )
    svc_page.wait_for_text(pkg_name)
    svc_page.wait_for_text("Gói liệu trình (8 buổi)")
