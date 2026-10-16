from common_setup.base_page import BasePage


class TenantHomePage(BasePage):
    """Page Object for Customer PWA Home /[tenant_slug]."""

    def open_tenant(self, tenant_slug: str) -> None:
        self.navigate(f"/{tenant_slug}")

    def go_to_booking_wizard(self) -> None:
        self.click_by_text("Đặt lịch hẹn ngay")
