from playwright.sync_api import Page

from common_setup.api_helper import ApiHelper, random_phone, unique_suffix
from features.admin_crm_packages.pages.customer_package_page import (
    AdminCustomerPackagePage,
)


def test_search_customer_and_issue_treatment_package(
    admin_page: Page, api_helper: ApiHelper
) -> None:
    token = api_helper.get_admin_token()
    cust_name = f"Khách VIP E2E {unique_suffix()}"
    cust_phone = random_phone("096")
    api_helper.create_customer(token, cust_name, cust_phone, notes="Da dầu")

    crm_page = AdminCustomerPackagePage(admin_page)
    crm_page.open()
    crm_page.search_and_select_customer(cust_phone, cust_name)

    pkg_title = f"Thẻ Trị Mụn VIP {unique_suffix()}"
    crm_page.issue_new_package(pkg_title, total_sessions=12)

    crm_page.wait_for_text(pkg_title)
    crm_page.wait_for_text("0 / 12 buổi")
    crm_page.wait_for_text("Còn lại: 12 buổi")
