import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import expect
from common_setup.api_helper import random_phone
from common_setup.config import config
from features.client_pwa_booking.pages.booking_wizard_page import BookingWizardPage


def test_customer_outside_first_200_has_name_and_is_searchable_for_manual_booking(scenario):
    s = scenario
    # Real isolated QA data: put the actual customer beyond the first 200 names.
    for i in range(201):
        s["call"]("POST", "/customers", json={"full_name": f"AAA Lookup {i:03d}", "phone_number": random_phone()})
    booking = s["book"]()
    page = s["page"](s["admin"], True)
    reads, writes = [], []
    page.on("request", lambda r: reads.append(r.url) if "/api/v1/customers?" in r.url else None)
    page.on("request", lambda r: writes.append(r.url) if r.method == "POST" and any(r.url.endswith(path) for path in ("/bookings", "/bookings/manual-batches", "/booking-requests")) else None)
    page.goto(config.frontend_url + "/admin/bookings")
    day = datetime.fromisoformat(booking["start_time"].replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=7))).date().isoformat()
    page.locator("input[type=date]").first.fill(day)
    card = page.get_by_test_id("booking-card-" + booking["id"])
    expect(card).to_contain_text("QA Customer")
    expect(card).to_contain_text("QA Staff")
    page.get_by_role("button", name="Tạo lịch hẹn", exact=True).click()
    modal = page.get_by_role("dialog")
    expect(modal.get_by_role("group", name="Khách đặt lịch").get_by_role("button", name="QA Customer", exact=False)).to_have_count(0)
    expect(modal.get_by_text("Đã tải 50 khách", exact=False)).to_contain_text("còn kết quả")
    with page.expect_response(lambda r: "/customers?" in r.url and "q=" in r.url):
        modal.locator("#manualCustomerSearch").fill(s["phone"])
    modal.get_by_role("group", name="Khách đặt lịch").get_by_role("button", name="QA Customer", exact=False).click()
    expect(modal.get_by_text("QA One Session", exact=True)).to_be_visible()
    card = modal.locator("label").filter(has_text="QA One Session")
    expect(card).to_contain_text("Đã đặt trước 1")
    expect(card.get_by_role("checkbox")).to_be_disabled()
    assert writes == [], "Searching/selecting a customer must not submit the booking form"
    assert len(reads) == 2, "No per-card lookup or automatic crawl of the CRM"
    assert "limit=50" in reads[0]


def calendar_pages(s, page, hold_more=False):
    booking = s["book"]()
    rows = [{**booking, "id": str(uuid.uuid4()), "customer_name": "Customer outside CRM page",
             "staff_name": "Technician display name"} for _ in range(205)]
    state = {"held": [], "fail_more": False}
    def intercept(route):
        query = parse_qs(urlsplit(route.request.url).query)
        offset = int(query.get("offset", ["0"])[0])
        if query.get("status"):
            route.fulfill(json=[], headers={"X-Has-More": "false"})
        elif offset and hold_more:
            state["held"].append(route)
        elif offset and state["fail_more"]:
            route.fulfill(status=503, json={"detail": "QA page unavailable"})
        else:
            limit = int(query.get("limit", ["200"])[0])
            route.fulfill(json=rows[offset:offset + limit], headers={"X-Has-More": str(offset + limit < len(rows)).lower()})
    page.route("**/api/v1/bookings?*", intercept)
    page.goto(config.frontend_url + "/admin/bookings")
    expect(page.locator('[data-testid^="booking-card-"]')).to_have_count(200)
    return state, rows


def test_calendar_more_than_200_rows_reports_partial_retries_and_loads_next(scenario):
    page = scenario["page"](scenario["admin"], True)
    state, rows = calendar_pages(scenario, page)
    expect(page.get_by_text("Đã tải 200 lịch", exact=False)).to_contain_text("còn dữ liệu")
    expect(page.get_by_test_id("booking-card-" + rows[0]["id"])).to_contain_text("Customer outside CRM page")
    state["fail_more"] = True
    page.get_by_role("button", name="Tải thêm lịch", exact=True).click()
    expect(page.get_by_role("main").get_by_role("alert")).to_contain_text("Chưa thể xử lý yêu cầu. Vui lòng thử lại sau.")
    expect(page.locator('[data-testid^="booking-card-"]')).to_have_count(200)
    state["fail_more"] = False
    page.get_by_role("button", name="Tải thêm lịch", exact=True).click()
    expect(page.locator('[data-testid^="booking-card-"]')).to_have_count(205)
    expect(page.get_by_role("button", name="Tải thêm lịch", exact=True)).to_have_count(0)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")


@pytest.mark.parametrize("old_status", [200, 503])
def test_late_calendar_page_cannot_replace_new_filter(scenario, old_status):
    page = scenario["page"](scenario["admin"], True)
    state, rows = calendar_pages(scenario, page, hold_more=True)
    with page.expect_request(lambda r: "/bookings?" in r.url and "offset=200" in r.url):
        page.get_by_role("button", name="Tải thêm lịch", exact=True).click()
    page.get_by_role("combobox", name="Lọc trạng thái lịch", exact=True).select_option("CONFIRMED")
    expect(page.locator('[data-testid^="booking-card-"]')).to_have_count(0)
    expect(page.get_by_text("Đã tải 0 lịch", exact=False)).to_be_visible()
    assert state["held"]
    for route in state["held"]:
        with page.expect_response(lambda r: "/bookings?" in r.url and "offset=200" in r.url) as old:
            if old_status == 200:
                route.fulfill(json=rows[200:], headers={"X-Has-More": "false"})
            else:
                route.fulfill(status=503, json={"detail": "QA old page error"})
        old.value.finished()
    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
    expect(page.locator('[data-testid^="booking-card-"]')).to_have_count(0)
    expect(page.get_by_role("main").get_by_role("alert")).to_have_count(0)


def test_public_staff_follows_daily_workplace_and_returns_on_next_working_day(scenario):
    s = scenario
    today = datetime.now(timezone(timedelta(hours=7))).date()
    dow = (today.weekday() + 1) % 7
    s["call"]("PUT", "/staff/" + s["staff"]["id"] + "/schedules", json={"schedules": [
        {"day_of_week": d, "start_time": "00:00:00", "end_time": "23:59:00", "is_day_off": d == dow} for d in range(7)]})
    page = s["page"]()
    wizard = BookingWizardPage(page)
    wizard.open_wizard(s["slug"])
    wizard.step1_select_service_by_name("QA Treatment")
    page.locator("details > summary").click()
    staff = page.get_by_role("button", name="QA Staff", exact=False)
    expect(staff).to_have_count(0)
    expect(page.get_by_text("Rất tiếc, ngày", exact=False)).to_be_visible()
    page.get_by_role("button", name="Quay lại", exact=True).click()
    page.get_by_role("button", name="Tiếp tục", exact=True).click()
    expect(staff).to_have_count(0)
    page.locator("#wizDate").fill((today + timedelta(days=1)).isoformat())
    expect(staff).to_be_visible()
    staff.click()
    expect(staff).to_have_attribute("aria-pressed", "true")
    expect(page.get_by_role("button", name="Tiếp tục", exact=True)).to_be_disabled()
    page.locator("button:has-text('KTV trống')").first.click()
    expect(page.get_by_role("button", name="Tiếp tục", exact=True)).to_be_enabled()


@pytest.mark.parametrize("long_name", [False, True], ids=["normal-name", "long-name"])
def test_customer_history_has_explicit_pagination_and_named_staff(scenario, long_name):
    s = scenario
    booking = s["book"]()
    staff_name = "QA Staff " + "LongName" * 25 if long_name else "QA Staff"
    rows = [{**booking, "id": str(uuid.uuid4()), "staff_name": staff_name, "status": "COMPLETED"} for _ in range(55)]
    page = s["page"]()
    def intercept(route):
        query = parse_qs(urlsplit(route.request.url).query)
        offset = int(query.get("offset", ["0"])[0])
        route.fulfill(json=rows[offset:offset + 50], headers={"X-Has-More": str(offset == 0).lower()})
    page.route("**/api/v1/bookings?*", intercept)
    page.goto(s["url"] + "/appointments")
    page.get_by_role("button", name="Lịch sử", exact=True).click()
    expect(page.locator('[data-testid^="customer-booking-"]')).to_have_count(50)
    expect(page.get_by_text("KTV: " + staff_name, exact=True)).to_have_count(50)
    assert page.get_by_text("KTV: " + staff_name, exact=True).first.evaluate("""el => {
      const range = document.createRange(); range.selectNodeContents(el);
      const text = range.getBoundingClientRect();
      const card = el.closest('[data-testid^="customer-booking-"]').getBoundingClientRect();
      return text.left >= card.left - 1 && text.right <= card.right + 1;
    }""")
    page.get_by_role("button", name="Tải thêm lịch", exact=True).click()
    expect(page.locator('[data-testid^="customer-booking-"]')).to_have_count(55)
    expect(page.get_by_role("button", name="Tải thêm lịch", exact=True)).to_have_count(0)
