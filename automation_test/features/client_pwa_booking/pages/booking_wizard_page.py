from common_setup.base_page import BasePage


class BookingWizardPage(BasePage):
    """Page Object for Customer 4-Step Booking Wizard /[tenant_slug]/book."""

    DATE_INPUT = "#wizDate"
    NOTE_INPUT = "#wizNote"

    def open_wizard(self, tenant_slug: str) -> None:
        self.navigate(f"/{tenant_slug}/book")
        self.wait_for_text("1. Dịch vụ")

    def step1_select_service_by_name(self, service_name: str) -> None:
        self.click_by_text(service_name)
        self.click_by_text("Tiếp tục")

    def step2_choose_auto_assign_staff(self) -> None:
        self.wait_for_text("Spa tự sắp xếp Kỹ thuật viên")
        self.click_by_text("Spa tự sắp xếp Kỹ thuật viên")
        self.click_by_text("Tiếp tục")

    def step3_select_date_and_first_slot(self, date_iso: str) -> None:
        with self.page.expect_response(
            lambda response: "/bookings/available-slots?" in response.url
            and f"date={date_iso}" in response.url
        ) as pending:
            self.fill_field(self.DATE_INPUT, date_iso)
        assert pending.value.status == 200
        slot_btn = self.page.locator("button:has-text('KTV trống')").first
        slot_btn.wait_for(state="visible", timeout=10000)
        slot_btn.click()
        self.click_by_text("Tiếp tục")

    def step4_confirm_booking(self, note: str) -> None:
        self.wait_for_text("Xác nhận lịch hẹn")
        self.fill_field(self.NOTE_INPUT, note)
        self.click_by_text("Xác nhận Đặt lịch")
