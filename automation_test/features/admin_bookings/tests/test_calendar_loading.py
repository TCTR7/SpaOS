"""Race tests hold actual QA read responses; no sleeps or automatic retries."""
from datetime import datetime, timedelta, timezone
import re
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import expect

from common_setup.api_helper import random_phone
from common_setup.config import config
from features.customer_regressions.conftest import scenario


def query(url):
    return parse_qs(urlsplit(url).query)


def prepare(s):
    first = s["book"]()
    start = datetime.fromisoformat(first["start_time"].replace("Z", "+00:00")) + timedelta(days=1)
    second = s["call"]("POST", "/bookings", json={"customer_id": s["customer"]["id"],
        "staff_id": s["staff"]["id"], "start_time": start.isoformat(),
        "items": [{"service_id": s["service"]["id"]}]})
    zone = timezone(timedelta(hours=7))
    a = datetime.fromisoformat(first["start_time"].replace("Z", "+00:00")).astimezone(zone).date().isoformat()
    b = start.astimezone(zone).date().isoformat()
    page = s["page"](s["admin"], True)
    # Verify auth/hydration/calendar readiness before arming fault injection.
    with page.expect_response(lambda r: r.request.method == "GET" and "/bookings?" in r.url):
        page.goto(config.frontend_url + "/admin/bookings")
    expect(page.locator("input[type=date]").first).to_be_visible()
    return page, first, second, a, b


def show_day(page, day):
    with page.expect_response(lambda r: "/bookings?" in r.url and query(r.url).get("date_from") == [day]):
        page.locator("input[type=date]").first.fill(day)


def settle_response(response, page):
    response.finished()
    # A paint barrier lets the completed fetch propagate through React before
    # assertions. It is independent of machine speed and network latency.
    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")


@pytest.mark.parametrize("old_status", [200, 503], ids=["late-data", "late-error"])
def test_old_day_response_cannot_replace_new_day(scenario, old_status):
    page, first, second, a, b = prepare(scenario)
    held = []
    def intercept(route):
        if query(route.request.url).get("date_from") == [a]:
            held.append((route, route.fetch() if old_status == 200 else None))
        else:
            route.continue_()
    page.route("**/api/v1/bookings?*", intercept)
    with page.expect_request(lambda r: "/bookings?" in r.url and query(r.url).get("date_from") == [a]):
        page.locator("input[type=date]").first.fill(a)
    show_day(page, b)
    expect(page.get_by_test_id("booking-card-" + second["id"])).to_be_visible()
    assert held, "Old response must be held before new response completes"
    while held:
        with page.expect_response(lambda r: "/bookings?" in r.url and query(r.url).get("date_from") == [a]) as old:
            route, response = held.pop()
            if response:
                route.fulfill(response=response)
            else:
                route.fulfill(status=503, json={"detail": "Old request failed"})
        settle_response(old.value, page)
    expect(page.get_by_test_id("booking-card-" + second["id"])).to_be_visible()
    expect(page.get_by_test_id("booking-card-" + first["id"])).to_have_count(0)
    expect(page.get_by_role("main").get_by_role("alert")).to_have_count(0)


def test_latest_error_does_not_show_previous_day_and_can_retry(scenario):
    page, first, second, a, b = prepare(scenario)
    show_day(page, a)
    expect(page.get_by_test_id("booking-card-" + first["id"])).to_be_visible()
    def fail_new_day(route):
        if query(route.request.url).get("date_from") == [b]:
            route.fulfill(status=503, json={"detail": "New day unavailable"})
        else:
            route.continue_()
    page.route("**/api/v1/bookings?*", fail_new_day)
    show_day(page, b)
    expect(page.get_by_role("main").get_by_role("alert")).to_contain_text("New day unavailable")
    expect(page.get_by_test_id("booking-card-" + first["id"])).to_have_count(0)
    expect(page.get_by_text("Không có lịch hẹn nào trong ngày", exact=False)).to_have_count(0)
    page.unroute("**/api/v1/bookings?*", fail_new_day)
    page.get_by_role("button", name="Thử tải lại lịch", exact=True).click()
    expect(page.get_by_test_id("booking-card-" + second["id"])).to_be_visible()


@pytest.mark.parametrize("filter_kind", ["staff", "status"])
def test_old_refresh_cannot_overwrite_new_filter(scenario, filter_kind):
    s = scenario
    page, first, _, a, _ = prepare(s)
    if filter_kind == "staff":
        staff = s["call"]("POST", "/staff", json={"full_name": "QA Other Staff",
                "phone_number": random_phone(), "password": "Staff@123"})
        page.reload()
    show_day(page, a)
    expect(page.get_by_test_id("booking-card-" + first["id"])).to_be_visible()
    held = []
    def hold_refresh(route):
        if not held and not query(route.request.url).get("staff_id") and not query(route.request.url).get("status"):
            held.append((route, route.fetch()))
        else:
            route.continue_()
    page.route("**/api/v1/bookings?*", hold_refresh)
    with page.expect_request(lambda r: "/bookings?" in r.url):
        page.get_by_role("button", name="Làm mới", exact=True).click()
    if filter_kind == "staff":
        control, value = page.get_by_label("Lọc KTV", exact=True), staff["id"]
    else:
        control, value = page.get_by_label("Lọc trạng thái lịch", exact=True), "CONFIRMED"
    control.select_option(value)
    expect(page.get_by_text("Không có lịch hẹn nào trong ngày", exact=False)).to_be_visible()
    route, response = held.pop()
    with page.expect_response(lambda r: "/bookings?" in r.url and not query(r.url).get("staff_id") and not query(r.url).get("status")) as old:
        route.fulfill(response=response)
    settle_response(old.value, page)
    expect(page.get_by_test_id("booking-card-" + first["id"])).to_have_count(0)
    expect(page.get_by_text("Không có lịch hẹn nào trong ngày", exact=False)).to_be_visible()


def test_pending_read_cannot_undo_status_change(scenario):
    page, first, _, a, _ = prepare(scenario)
    show_day(page, a)
    card = page.get_by_test_id("booking-card-" + first["id"])
    expect(card).to_be_visible()
    patches, reads = [], []
    page.route("**/api/v1/bookings/" + first["id"] + "/status", lambda route: patches.append(route))
    with page.expect_request(lambda r: r.method == "PATCH" and r.url.endswith("/status")):
        card.get_by_role("button", name=re.compile("xác nhận", re.IGNORECASE)).click()
    def hold_read(route):
        if not reads:
            reads.append((route, route.fetch()))
        else:
            route.continue_()
    page.route("**/api/v1/bookings?*", hold_read)
    with page.expect_request(lambda r: "/bookings?" in r.url):
        page.get_by_role("button", name="Làm mới", exact=True).click()
    with page.expect_response(lambda r: r.request.method == "PATCH" and r.url.endswith("/status")):
        route = patches.pop()
        route.fulfill(response=route.fetch())
    expect(card.get_by_text("Đã xác nhận", exact=True)).to_be_visible()
    route, response = reads.pop()
    with page.expect_response(lambda r: "/bookings?" in r.url) as old:
        route.fulfill(response=response)
    settle_response(old.value, page)
    expect(card.get_by_text("Đã xác nhận", exact=True)).to_be_visible()


def test_reference_failure_keeps_calendar_and_blocks_unverified_create(scenario):
    s = scenario
    booking = s["book"]()
    day = datetime.fromisoformat(booking["start_time"].replace("Z", "+00:00")).astimezone(
        timezone(timedelta(hours=7))).date().isoformat()
    page = s["page"](s["admin"], True)
    def fail_services(route):
        route.fulfill(status=503, json={"detail": "QA catalogue unavailable"})
    page.route("**/api/v1/services**", fail_services)
    page.goto(config.frontend_url + "/admin/bookings")
    show_day(page, day)
    expect(page.get_by_test_id("booking-card-" + booking["id"])).to_be_visible()
    expect(page.get_by_test_id("calendar-reference-error")).to_contain_text("Danh mục dịch vụ")
    create = page.get_by_role("button", name="Tạo lịch hẹn thủ công", exact=True)
    expect(create).to_be_disabled()
    page.unroute("**/api/v1/services**", fail_services)
    page.get_by_role("button", name="Thử tải lại thông tin", exact=True).click()
    expect(create).to_be_enabled()
    expect(page.get_by_test_id("calendar-reference-error")).to_have_count(0)


@pytest.mark.parametrize("scope_change", ["filter", "week", "date"])
@pytest.mark.parametrize("outcome", ["success", "rejected", "lost-response"])
def test_mutation_refreshes_current_scope(scenario, scope_change, outcome):
    page, first, second, day, next_day = prepare(scenario)
    show_day(page, day)
    card = page.get_by_test_id("booking-card-" + first["id"])
    expect(card).to_be_visible()
    held, reads = [], []
    page.on("request", lambda request: reads.append(request.url)
            if request.method == "GET" and "/bookings?" in request.url else None)
    page.route("**/api/v1/bookings/" + first["id"] + "/status", lambda route: held.append(route))
    with page.expect_request(lambda r: r.method == "PATCH" and r.url.endswith("/status")):
        card.get_by_role("button", name=re.compile("xác nhận", re.IGNORECASE)).click()
    with page.expect_response(lambda r: r.request.method == "GET" and "/bookings?" in r.url):
        if scope_change == "filter":
            page.get_by_label("Lọc trạng thái lịch", exact=True).select_option("PENDING")
        elif scope_change == "week":
            page.get_by_role("button", name="Theo Tuần", exact=True).click()
        else:
            page.locator("input[type=date]").first.fill(next_day)
    visible_card = card if scope_change != "date" else page.get_by_test_id("booking-card-" + second["id"])
    expect(visible_card.get_by_text("Chờ xác nhận", exact=True)).to_be_visible()
    expected_query = query(reads[-1])
    # Wait for a new GET matching the current scope, not the callback's old scope.
    with page.expect_response(lambda r: r.request.method == "GET" and "/bookings?" in r.url
                              and query(r.url) == expected_query):
        route = held.pop()
        if outcome == "success":
            route.fulfill(response=route.fetch())
        else:
            if outcome == "lost-response":
                committed = route.fetch()
                assert committed.status == 200
            route.fulfill(status=503, json={"detail": "QA update response unavailable"})
    expected_status = "PENDING" if outcome == "rejected" else "CONFIRMED"
    assert scenario["call"]("GET", "/bookings/" + first["id"])["status"] == expected_status
    if scope_change == "filter" and expected_status == "CONFIRMED":
        expect(card).to_have_count(0)
    elif scope_change == "date":
        expect(card).to_have_count(0)
        expect(visible_card.get_by_text("Chờ xác nhận", exact=True)).to_be_visible()
    else:
        expect(card.get_by_text("Chờ xác nhận" if expected_status == "PENDING" else "Đã xác nhận", exact=True)).to_be_visible()
    if outcome != "success":
        expect(page.get_by_role("main").get_by_role("alert")).to_contain_text("QA update response unavailable")
