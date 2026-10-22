from datetime import date, timedelta
from playwright.sync_api import Page, expect

from common_setup.api_helper import ApiHelper, random_phone, unique_suffix
from common_setup.config import config
from features.admin_bookings.pages.booking_calendar_page import (
    AdminBookingCalendarPage,
)


def test_complete_booking_on_calendar_deducts_package_session(
    admin_page: Page, api_helper: ApiHelper
) -> None:
    token = api_helper.get_admin_token()

    # 1. Seed a dedicated customer + active treatment package via API
    cust_name = f"Khách Trừ Buổi {unique_suffix()}"
    cust = api_helper.create_customer(token, cust_name, random_phone("095"))

    pkg_services = api_helper.list_services(token, is_package=True)
    assert len(pkg_services) > 0, "Expected at least 1 package service in spa-demo"
    pkg_svc = pkg_services[0]

    issued_pkg = api_helper.issue_customer_package(
        token,
        customer_id=cust["id"],
        service_id=pkg_svc["id"],
        package_name=f"Thẻ Liệu Trình {unique_suffix()}",
        total_sessions=5,
    )
    assert issued_pkg["used_sessions"] == 0

    # 2. Find an available slot on a future day and create a package booking
    booking_day = (date.today() + timedelta(days=3)).isoformat()
    slots_res = api_helper.get_available_slots(
        config.tenant_slug, booking_day, [pkg_svc["id"]]
    )
    assert len(slots_res["slots"]) > 0
    first_slot_start = slots_res["slots"][0]["start_time"]

    api_helper.create_booking(
        token,
        start_time=first_slot_start,
        customer_id=cust["id"],
        items=[
            {
                "service_id": pkg_svc["id"],
                "customer_package_id": issued_pkg["id"],
            }
        ],
        note="E2E test auto deduct session",
    )

    # 3. On Admin Calendar UI, navigate to that date and transition PENDING -> CONFIRMED -> COMPLETED
    cal_page = AdminBookingCalendarPage(admin_page)
    cal_page.open()
    cal_page.select_date(booking_day)
    cal_page.wait_for_text(cust_name)

    cal_page.transition_booking_for_customer(cust_name, "Xác nhận lịch")
    card = admin_page.locator("div.rounded-lg.border", has_text=cust_name).first
    expect(card.get_by_role("button", name="Chi tiết lịch hẹn", exact=True)).to_be_visible()

    cal_page.transition_booking_for_customer(cust_name, "Hoàn thành buổi")
    expect(card.get_by_text("Hoàn thành")).to_be_visible()

    # 4. Verify via API that used_sessions incremented to 1
    updated_pkgs = api_helper.get_customer_packages(token, cust["id"])
    matched = next(p for p in updated_pkgs if p["id"] == issued_pkg["id"])
    assert matched["used_sessions"] == 1
    assert matched["remaining_sessions"] == 4
