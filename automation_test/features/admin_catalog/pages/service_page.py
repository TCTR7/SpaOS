from common_setup.base_page import BasePage


class AdminServicePage(BasePage):
    """Page Object for /admin/services."""

    NAME_INPUT = "#svcName"
    DESC_INPUT = "#svcDesc"
    DURATION_INPUT = "#svcDuration"
    PRICE_INPUT = "#svcPrice"
    SESSIONS_INPUT = "#svcSessions"

    def open(self) -> None:
        self.navigate("/admin/services")
        self.wait_for_text("Danh mục Dịch vụ & Gói Liệu trình")

    def create_single_service(
        self, name: str, duration: int, price: int, description: str = ""
    ) -> None:
        self.click_by_text("Thêm dịch vụ mới")
        self.fill_field(self.NAME_INPUT, name)
        if description:
            self.fill_field(self.DESC_INPUT, description)
        self.fill_field(self.DURATION_INPUT, str(duration))
        self.fill_field(self.PRICE_INPUT, str(price))
        self.click_by_text("Lưu dịch vụ")

    def create_package_service(
        self, name: str, duration: int, price: int, total_sessions: int
    ) -> None:
        self.click_by_text("Thêm dịch vụ mới")
        self.fill_field(self.NAME_INPUT, name)
        self.fill_field(self.DURATION_INPUT, str(duration))
        self.fill_field(self.PRICE_INPUT, str(price))
        self.click_by_text("Đây là Gói thẻ liệu trình nhiều buổi")
        self.fill_field(self.SESSIONS_INPUT, str(total_sessions))
        self.click_by_text("Lưu dịch vụ")
