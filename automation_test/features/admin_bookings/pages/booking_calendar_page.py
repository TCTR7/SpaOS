from playwright.sync_api import expect

from common_setup.base_page import BasePage


class AdminBookingCalendarPage(BasePage):
    """Page Object for /admin/bookings."""

    DATE_INPUT = "input[type='date']"

    def open(self) -> None:
        with self.page.expect_response(lambda r: "/api/v1/bookings?" in r.url and r.request.method == "GET") as response:
            self.navigate("/admin/bookings")
        assert response.value.status == 200
        self.wait_for_text("Lịch hẹn & Điều phối Kỹ thuật viên")

    def select_date(self, date_iso: str) -> None:
        date_input = self.page.locator(self.DATE_INPUT).first
        date_input.wait_for(state="visible", timeout=10000)
        with self.page.expect_response(lambda r: "/api/v1/bookings?" in r.url and "date_from=" + date_iso in r.url) as response:
            date_input.fill(date_iso)
        assert response.value.status == 200

    def transition_booking_for_customer(
        self, customer_name: str, button_label: str
    ) -> None:
        card = self.page.locator(
            "div.rounded-lg.border", has_text=customer_name
        ).first
        expect(card).to_be_visible(timeout=10000)
        btn = card.get_by_role("button", name=button_label)
        with self.page.expect_response(lambda r: "/bookings/" in r.url and r.url.endswith("/status") and r.request.method == "PATCH") as response:
            btn.click()
        assert response.value.status == 200
