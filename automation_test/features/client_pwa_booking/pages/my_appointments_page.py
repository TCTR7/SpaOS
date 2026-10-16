from common_setup.base_page import BasePage


class MyAppointmentsPage(BasePage):
    """Page Object for Customer Appointments /[tenant_slug]/appointments."""

    def open_appointments(self, tenant_slug: str) -> None:
        self.navigate(f"/{tenant_slug}/appointments")
        self.wait_for_text("Lịch hẹn của tôi")

    def verify_booking_success_banner(self) -> None:
        self.wait_for_text("Đặt lịch thành công!")
