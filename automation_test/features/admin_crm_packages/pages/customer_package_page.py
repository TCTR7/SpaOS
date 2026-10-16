from common_setup.base_page import BasePage


class AdminCustomerPackagePage(BasePage):
    """Page Object for /admin/customers."""

    SEARCH_INPUT = "input[placeholder*='Tìm theo Tên hoặc Số điện thoại']"
    PKG_CUSTOM_NAME_INPUT = "#pkgCustomName"
    PKG_SESSIONS_INPUT = "#pkgSessions"

    def open(self) -> None:
        self.navigate("/admin/customers")
        self.wait_for_text("Khách hàng & Quản lý Thẻ Liệu trình (CRM)")

    def search_and_select_customer(self, keyword: str, customer_name: str) -> None:
        self.fill_field(self.SEARCH_INPUT, keyword)
        self.click_by_text("Tìm", exact=True)
        self.click_by_text(customer_name)

    def issue_new_package(self, custom_name: str, total_sessions: int) -> None:
        self.click_by_text("Cấp thẻ liệu trình")
        self.fill_field(self.PKG_CUSTOM_NAME_INPUT, custom_name)
        self.fill_field(self.PKG_SESSIONS_INPUT, str(total_sessions))
        self.click_by_text("Xác nhận cấp thẻ")
