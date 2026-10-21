import json
from datetime import date, timedelta
from playwright.sync_api import expect

from common_setup.api_helper import random_phone, unique_suffix
from common_setup.config import config
from features.client_pwa_booking.pages.booking_wizard_page import BookingWizardPage


def test_customer_uses_own_package_and_sees_reservation(browser_instance, api_helper):
    admin = api_helper.get_admin_token()
    phone = random_phone()
    customer = api_helper.create_customer(admin, "Package E2E", phone)
    token = api_helper.login(config.tenant_slug, phone, "Customer@123")["access_token"]
    service = api_helper.list_services(admin, is_package=True)[0]
    name = "PWA Package " + unique_suffix()
    package = api_helper.issue_customer_package(admin, customer["id"], service["id"], name, 3)
    context = browser_instance.new_context(viewport={"width": 390, "height": 844})
    context.add_init_script("localStorage.setItem(" + json.dumps("spaos_customer_token_" + config.tenant_slug) + ", " + json.dumps(token) + ");")
    page = context.new_page()
    booking_id = None
    try:
        page.goto(config.frontend_url + "/" + config.tenant_slug + "/profile")
        expect(page.get_by_text(name, exact=True)).to_be_visible()
        expect(page.get_by_text("Có thể đặt thêm: 3 buổi", exact=True)).to_be_visible()
        page.get_by_role("link", name="Dùng 1 buổi trong thẻ").click()
        wizard = BookingWizardPage(page)
        expect(page.locator("#wizDate")).to_be_visible()
        wizard.step2_choose_auto_assign_staff()
        wizard.step2_select_date_and_first_slot((date.today() + timedelta(days=8)).isoformat())
        with page.expect_response(lambda r: r.url.endswith("/api/v1/booking-requests") and r.request.method == "POST") as response:
            wizard.step3_confirm_booking("PACKAGE_" + unique_suffix())
        assert response.value.status == 201, response.value.text()
        booking = response.value.json()
        booking_id = booking["id"]
        assert booking["items"][0]["customer_package_id"] == package["id"]
        assert float(booking["total_price"]) == 0
        page.goto(config.frontend_url + "/" + config.tenant_slug + "/profile")
        expect(page.get_by_text("Có thể đặt thêm: 2 buổi", exact=True)).to_be_visible()
        expect(page.get_by_text("Chưa dùng: 3 buổi • Đã đặt lịch: 1 buổi", exact=True)).to_be_visible()
    finally:
        if booking_id:
            response = api_helper.client.post("/bookings/" + booking_id + "/cancel", headers={"Authorization": "Bearer " + token})
            response.raise_for_status()
        context.close()
