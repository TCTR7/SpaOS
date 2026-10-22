import uuid
from urllib.parse import parse_qs, urlsplit
import pytest
from playwright.sync_api import expect
from common_setup.config import config
from common_setup.api_helper import random_phone


def admin_page(s, path, width=390):
    page = s["page"](s["admin"], True)
    page.set_viewport_size({"width": width, "height": 844})
    return page, config.frontend_url + "/admin/" + path


@pytest.mark.parametrize("width", [360, 390, 1366])
def test_crm_loads_beyond_100_and_mobile_back_keeps_search_scroll_focus(scenario, width):
    s = scenario
    rows = [{**s["customer"], "id": str(uuid.uuid4()), "full_name": f"CRM {i:03d} " + "LongName" * 12,
             "notes": "LongNote" * 35} for i in range(105)]
    page, url = admin_page(s, "customers", width)
    reads = []
    def customers(route):
        q = parse_qs(urlsplit(route.request.url).query)
        offset = int(q.get("offset", [0])[0])
        reads.append(offset)
        route.fulfill(json=rows[offset:offset + 50], headers={"X-Has-More": str(offset + 50 < len(rows)).lower()})
    page.route("**/api/v1/customers?*", customers)
    page.route("**/api/v1/customers/*/packages", lambda r: r.fulfill(json=[]))
    page.goto(url)
    search = page.get_by_placeholder("Tìm theo Tên hoặc Số điện thoại...")
    search.fill("CRM")
    page.get_by_role("button", name="Tìm", exact=True).click()
    expect(page.get_by_text("Đã tải 50 khách", exact=False)).to_be_visible()
    for count in (100, 105):
        page.get_by_role("button", name="Tải thêm khách", exact=True).click()
        expect(page.get_by_text(f"Đã tải {count} khách", exact=False)).to_be_visible()
    target = page.get_by_role("button").filter(has_text="CRM 104")
    target.scroll_into_view_if_needed()
    scroll = page.locator("[data-list-scroll]").evaluate("el => el.scrollTop")
    target.focus()
    page.keyboard.press("Enter")
    expect(page.get_by_role("heading", name=rows[-1]["full_name"], exact=True)).to_be_visible()
    overflow = page.evaluate("Array.from(document.querySelectorAll('main *')).filter(el => el.getBoundingClientRect().right > innerWidth + 1).slice(0, 8).map(el => ({tag:el.tagName, cls:el.className, right:el.getBoundingClientRect().right}))")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), overflow
    if width < 1024:
        expect(search).to_be_hidden()
        page.get_by_role("button", name="Quay lại danh sách khách", exact=True).click()
        expect(search).to_have_value("CRM")
        expect(target).to_be_focused()
        assert abs(page.locator("[data-list-scroll]").evaluate("el => el.scrollTop") - scroll) <= 1
    assert reads == [0, 0, 50, 100]


def test_late_customer_search_cannot_replace_new_results(scenario):
    s = scenario
    page, url = admin_page(s, "customers")
    held = []
    def search(route):
        q = parse_qs(urlsplit(route.request.url).query).get("q", [""])[0]
        if q == "old":
            held.append(route)
            page.evaluate("window.qaCustomerHeld = true")
        else:
            route.fulfill(json=[{**s["customer"], "full_name": "Current customer" if q else "Initial customer"}], headers={"X-Has-More": "false"})
    page.route("**/api/v1/customers?*", search)
    page.goto(url)
    field = page.get_by_placeholder("Tìm theo Tên hoặc Số điện thoại...")
    field.fill("old")
    page.get_by_role("button", name="Tìm", exact=True).click()
    page.wait_for_function("window.qaCustomerHeld === true")
    field.fill("new")
    page.get_by_role("button", name="Tìm", exact=True).click()
    expect(page.get_by_role("button").filter(has_text="Current customer")).to_be_visible()
    with page.expect_response(lambda r: "q=old" in r.url):
        held[0].fulfill(json=[{**s["customer"], "full_name": "Stale customer"}])
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    expect(page.get_by_text("Stale customer", exact=True)).to_have_count(0)


def test_customer_package_error_has_retry_instead_of_empty_state(scenario):
    s = scenario
    page, url = admin_page(s, "customers")
    pattern = "**/api/v1/customers/" + s["customer"]["id"] + "/packages"
    page.route(pattern, lambda r: r.fulfill(status=503, json={"detail": "QA packages unavailable"}))
    page.goto(url)
    page.get_by_role("button").filter(has_text="QA Customer").click()
    expect(page.get_by_role("main").get_by_role("alert")).to_contain_text("Chưa thể xử lý yêu cầu. Vui lòng thử lại sau.")
    expect(page.get_by_text("Khách hàng này chưa có thẻ", exact=False)).to_have_count(0)
    page.unroute(pattern)
    page.get_by_role("button", name="Thử tải lại thẻ", exact=True).click()
    expect(page.get_by_text("QA One Session", exact=True)).to_be_visible()


def test_failed_staff_read_cannot_save_defaults_and_back_keeps_draft(scenario):
    s = scenario
    other = s["call"]("POST", "/staff", json={"full_name": "QA Second", "phone_number": random_phone(), "password": "Staff@123"})
    page, url = admin_page(s, "staff", 360)
    pattern = "**/api/v1/staff/" + s["staff"]["id"] + "/schedules"
    page.route(pattern, lambda r: r.fulfill(status=503, json={"detail": "QA schedules unavailable"}))
    page.goto(url)
    page.get_by_role("button").filter(has_text="QA Staff").click()
    expect(page.get_by_role("main").get_by_role("alert")).to_contain_text("Chưa thể xử lý yêu cầu. Vui lòng thử lại sau.")
    expect(page.get_by_role("button", name="Lưu lịch tuần", exact=True)).to_be_disabled()
    expect(page.locator("input[type=time]")).to_have_count(0)
    page.unroute(pattern)
    page.get_by_role("button", name="Thử tải lại ca làm", exact=True).click()
    expect(page.locator("input[type=time]")).to_have_count(14)
    page.locator("input[type=time]").first.fill("02:00")
    page.get_by_role("button", name="Quay lại danh sách KTV", exact=True).click()
    page.get_by_role("button").filter(has_text="QA Staff").click()
    expect(page.locator("input[type=time]").first).to_have_value("02:00")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    page.get_by_role("button", name="Quay lại danh sách KTV", exact=True).click()
    page.get_by_role("button").filter(has_text="QA Second").click()
    expect(page.get_by_role("dialog", name="Bỏ thay đổi chưa lưu?", exact=True)).to_be_visible()
    page.get_by_role("button", name="Bỏ thay đổi và chọn KTV", exact=True).click()
    expect(page.get_by_role("heading", name="Lịch làm việc 7 ngày — QA Second", exact=True)).to_be_visible()


def test_old_customer_packages_cannot_replace_new_profile(scenario):
    s = scenario
    other_id = str(uuid.uuid4())
    page, url = admin_page(s, "customers", 1366)
    page.route("**/api/v1/customers?*", lambda r: r.fulfill(json=[s["customer"], {**s["customer"], "id": other_id, "full_name": "Second Customer"}], headers={"X-Has-More": "false"}))
    held = []
    def packages(route):
        if s["customer"]["id"] in route.request.url:
            held.append(route)
            page.evaluate("window.qaPackagesHeld = true")
        else:
            route.fulfill(json=[{**s["package"], "customer_id": other_id, "package_name": "Second profile package"}])
    page.route("**/api/v1/customers/*/packages", packages)
    page.goto(url)
    page.wait_for_function("window.qaPackagesHeld === true")
    page.get_by_role("button").filter(has_text="Second Customer").click()
    expect(page.get_by_text("Second profile package", exact=True)).to_be_visible()
    with page.expect_response(lambda r: s["customer"]["id"] + "/packages" in r.url):
        held[0].fulfill(json=[{**s["package"], "package_name": "Old profile package"}])
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    expect(page.get_by_text("Old profile package", exact=True)).to_have_count(0)
    expect(page.get_by_text("Second profile package", exact=True)).to_be_visible()


def test_mobile_profile_can_return_after_edit_no_longer_matches_search(scenario):
    page, url = admin_page(scenario, "customers")
    page.goto(url)
    field = page.get_by_placeholder("Tìm theo Tên hoặc Số điện thoại...")
    field.fill("QA Customer")
    page.get_by_role("button", name="Tìm", exact=True).click()
    page.get_by_role("button").filter(has_text="QA Customer").click()
    page.get_by_role("button", name="Sửa hồ sơ", exact=True).click()
    page.locator("#custName").fill("Renamed profile")
    page.get_by_role("button", name="Lưu thông tin", exact=True).click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    page.get_by_role("button", name="Quay lại danh sách khách", exact=True).click()
    expect(field).to_have_value("QA Customer")
    expect(page.get_by_text("Không tìm thấy khách hàng nào.", exact=True)).to_be_visible()


def test_old_staff_schedule_cannot_replace_new_staff(scenario):
    s = scenario
    second = s["call"]("POST", "/staff", json={"full_name": "ZZ Second Staff", "phone_number": random_phone(), "password": "Staff@123"})
    page, url = admin_page(s, "staff")
    held = []
    def hold(route):
        held.append(route)
        page.evaluate("window.qaScheduleHeld = true")
    page.route("**/api/v1/staff/" + s["staff"]["id"] + "/schedules", hold)
    page.goto(url)
    page.get_by_role("button").filter(has_text="QA Staff").click()
    page.wait_for_function("window.qaScheduleHeld === true")
    page.get_by_role("button", name="Quay lại danh sách KTV", exact=True).click()
    page.get_by_role("button").filter(has_text="ZZ Second Staff").click()
    expect(page.locator("input[type=time]").first).to_have_value("09:00")

    for route in held:
        with page.expect_response(lambda r: s["staff"]["id"] + "/schedules" in r.url):
            route.fulfill(json=[{"day_of_week": d, "start_time": "15:00:00", "end_time": "18:00:00", "is_day_off": False} for d in range(7)])
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    expect(page.locator("input[type=time]").first).to_have_value("09:00")


def test_issue_package_pins_customer_while_search_finishes(scenario):
    s = scenario
    other = s["call"]("POST", "/customers", json={"full_name": "Other search customer", "phone_number": random_phone()})
    page, url = admin_page(s, "customers", 1366)
    held = []
    def search(route):
        if "q=other" in route.request.url:
            held.append(route)
            page.evaluate("window.qaSearchForIssueHeld = true")
        else:
            route.fulfill(json=[s["customer"]], headers={"X-Has-More": "false"})
    page.route("**/api/v1/customers?*", search)
    page.goto(url)
    expect(page.get_by_text("QA One Session", exact=True)).to_be_visible()
    page.get_by_placeholder("Tìm theo Tên hoặc Số điện thoại...").fill("other")
    page.get_by_role("button", name="Tìm", exact=True).click()
    page.wait_for_function("window.qaSearchForIssueHeld === true")
    page.get_by_role("button", name="Cấp thẻ liệu trình", exact=True).click()
    with page.expect_response(lambda r: "q=other" in r.url):
        held[0].fulfill(json=[other], headers={"X-Has-More": "false"})
    page.locator("#pkgCustomName").fill("Pinned customer package")
    with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/customer-packages")) as saved:
        page.get_by_role("button", name="Xác nhận cấp thẻ", exact=True).click()
    assert saved.value.status == 201
    assert saved.value.json()["customer_id"] == s["customer"]["id"]
    assert s["call"]("GET", "/customers/" + other["id"] + "/packages") == []
