from datetime import date, timedelta
from playwright.sync_api import Page

from common_setup.api_helper import ApiHelper, unique_suffix
from common_setup.config import config
from features.admin_bookings.pages.booking_calendar_page import (
    AdminBookingCalendarPage,
)
from features.client_pwa_booking.pages.booking_wizard_page import (
    BookingWizardPage,
)
from features.client_pwa_booking.pages.my_appointments_page import (
    MyAppointmentsPage,
)


def test_customer_pwa_4step_booking_and_admin_calendar_sync(
    customer_pwa_page: Page, admin_page: Page, api_helper: ApiHelper
) -> None:
    token = api_helper.get_admin_token()
    single_services = api_helper.list_services(token, is_package=False)
    assert len(single_services) > 0
    chosen_service_name = single_services[0]["name"]

    booking_day = (date.today() + timedelta(days=4)).isoformat()
    unique_note = f"PWA_E2E_BOOKING_{unique_suffix()}"

    # 1. Customer completes 4-step wizard on Mobile PWA
    wizard = BookingWizardPage(customer_pwa_page)
    wizard.open_wizard(config.tenant_slug)
    wizard.step1_select_service_by_name(chosen_service_name)
    wizard.step2_choose_auto_assign_staff()
    wizard.step3_select_date_and_first_slot(booking_day)
    wizard.step4_confirm_booking(unique_note)

    # 2. Verify redirect to /[tenant_slug]/appointments ("Sắp tới")
    my_appts = MyAppointmentsPage(customer_pwa_page)
    my_appts.wait_for_url_contains(f"/{config.tenant_slug}/appointments")
    my_appts.verify_booking_success_banner()
    my_appts.wait_for_text(chosen_service_name)

    # 3. Verify booking appears simultaneously on Admin Calendar
    admin_cal = AdminBookingCalendarPage(admin_page)
    admin_cal.open()
    admin_cal.select_date(booking_day)
    admin_cal.wait_for_text(unique_note)
