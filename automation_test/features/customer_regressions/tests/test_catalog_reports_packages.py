from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit
import uuid
import pytest
from playwright.sync_api import expect
from common_setup.config import config


def no_overflow(page):
    outside = page.evaluate("Array.from(document.querySelectorAll('main *')).filter(e=>e.getBoundingClientRect().right>innerWidth+1).slice(0,6).map(e=>({tag:e.tagName,cls:e.className,right:e.getBoundingClientRect().right}))")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), outside


def report_data(s, url, count=2, name="QA Technician"):
    q = parse_qs(urlsplit(url).query)
    totals = dict(completed_bookings_count=count, completed_services_count=count, single_services_count=count,
                  package_sessions_count=0, total_revenue="9000000000")
    return dict(start_date=q["start_date"][0], end_date=q["end_date"][0], timezone="Asia/Ho_Chi_Minh",
                totals=totals, staff=[dict(staff_id=s["staff"]["id"], full_name=name, is_active=False, **totals)])


@pytest.mark.parametrize("width", [360, 390, 768, 1366])
def test_catalog_and_report_show_full_names_values_without_overflow(scenario, width):
    s = scenario
    name = "QA Long Service " + "LongServiceName" * 12
    s["call"]("PATCH", "/services/" + s["service"]["id"], json={"name": name, "description": "LongNote" * 35, "price": "9000000000", "is_active": False})
    page = s["page"](s["admin"], True)
    page.set_viewport_size({"width": width, "height": 844})
    page.goto(config.frontend_url + "/admin/services")
    row = page.locator("tbody tr").filter(has_text=name)
    expect(row).to_be_visible()
    expect(row).to_contain_text("9.000.000.000")
    expect(row).to_contain_text("Tạm ngưng")
    expect(row.get_by_role("button", name="Chỉnh sửa", exact=True)).to_have_count(1)
    no_overflow(page)
    expect(page.locator("table")).to_have_css("display", "table" if width >= 1024 else "block")
    page.route("**/api/v1/reports/staff-performance?*", lambda r: r.fulfill(json=report_data(s, r.request.url, name="QA Staff " + "LongStaffName" * 15)))
    page.goto(config.frontend_url + "/admin/reports")
    report = page.locator("tbody tr")
    expect(report).to_have_count(1)
    expect(report).to_contain_text("9.000.000.000")
    expect(page.get_by_text("Giá trị dịch vụ hoàn thành không phải tiền đã thu.", exact=False)).to_be_visible()
    page.locator("#commRate").fill("20")
    expect(report).to_contain_text("1.800.000.000")
    expect(page.locator("thead th").last).to_have_text("Hoa hồng ước tính (20%)")
    no_overflow(page)
    expect(page.locator("#repStart")).to_have_count(1)
    expect(page.locator("#repEnd")).to_have_count(1)


@pytest.mark.parametrize("old_status", [200, 503])
def test_old_report_response_cannot_replace_new_period(scenario, old_status):
    s = scenario
    page = s["page"](s["admin"], True)
    today = datetime.now(timezone(timedelta(hours=7))).date()
    old_day, new_day = [(today - timedelta(days=d)).isoformat() for d in (5, 4)]
    held = []
    def respond(route):
        if parse_qs(urlsplit(route.request.url).query)["start_date"] == [old_day]:
            held.append(route)
            page.evaluate("window.qaReportHeld = true")
        else:
            route.fulfill(json=report_data(s, route.request.url, name="Current report staff"))
    page.route("**/api/v1/reports/staff-performance?*", respond)
    page.goto(config.frontend_url + "/admin/reports")
    page.locator("#repStart").fill(old_day)
    page.wait_for_function("window.qaReportHeld === true")
    page.locator("#repStart").fill(new_day)
    expect(page.get_by_text("Current report staff", exact=True)).to_be_visible()
    with page.expect_response(lambda r: "start_date=" + old_day in r.url):
        held[0].fulfill(json=report_data(s, held[0].request.url, name="Stale report staff")) if old_status == 200 else held[0].fulfill(status=503, json={"detail": "QA stale report error"})
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    expect(page.get_by_text("Stale report staff", exact=True)).to_have_count(0)
    expect(page.get_by_role("main").get_by_role("alert")).to_have_count(0)
    expect(page.get_by_text("Khoảng thời gian: " + datetime.fromisoformat(new_day).strftime("%d/%m/%Y"), exact=False)).to_be_visible()


def test_report_error_retries_and_invalid_dates_do_not_show_old_totals(scenario):
    s = scenario
    page = s["page"](s["admin"], True)
    pattern = "**/api/v1/reports/staff-performance?*"
    page.route(pattern, lambda r: r.fulfill(status=503, json={"detail": "QA report unavailable"}))
    page.goto(config.frontend_url + "/admin/reports")
    expect(page.get_by_role("main").get_by_role("alert")).to_contain_text("Chưa thể xử lý yêu cầu. Vui lòng thử lại sau.")
    expect(page.get_by_text("Không có dữ liệu Kỹ thuật viên trong khoảng thời gian này.", exact=True)).to_have_count(0)
    page.unroute(pattern)
    page.get_by_role("button", name="Thử tải lại báo cáo", exact=True).click()
    expect(page.locator("tbody tr")).to_have_count(1)
    page.locator("#repStart").fill("2099-01-01")
    expect(page.get_by_role("main").get_by_role("alert")).to_contain_text("Ngày kết thúc")
    expect(page.get_by_text("Giá trị dịch vụ hoàn thành", exact=True)).to_have_count(0)


@pytest.mark.parametrize("width", [360, 390, 768, 1366])
def test_package_states_and_desktop_width_are_clear(scenario, width):
    s = scenario
    s["call"]("PATCH", "/customers/" + s["customer"]["id"], json={"full_name": "Customer " + "LongName" * 24})
    base = {**s["package"], "total_sessions": 3, "used_sessions": 0, "remaining_sessions": 3, "reserved_sessions": 0, "available_sessions": 3, "status": "ACTIVE", "expiry_date": None}
    rows = [dict(base, id=str(uuid.uuid4()), package_name="Available " + "LongPackage" * 18),
            dict(base, id=str(uuid.uuid4()), package_name="Reserved package", reserved_sessions=3, available_sessions=0),
            dict(base, id=str(uuid.uuid4()), package_name="Completed package", used_sessions=3, remaining_sessions=0, available_sessions=0, status="COMPLETED"),
            dict(base, id=str(uuid.uuid4()), package_name="Expired package", expiry_date="2020-01-01T00:00:00Z", available_sessions=0, reserved_sessions=1)]
    page = s["page"]()
    page.set_viewport_size({"width": width, "height": 844})
    page.route("**/api/v1/customer-packages/me", lambda r: r.fulfill(json=rows))
    page.goto(s["url"] + "/profile")
    cards = page.locator('[data-layout-card="customer-package"]')
    expect(cards).to_have_count(4)
    for state in ("Đang sử dụng", "Đã giữ chỗ hết buổi", "Đã dùng hết", "Đã hết hạn"):
        expect(cards.get_by_text(state, exact=True)).to_be_visible()
    expect(page.get_by_role("link", name="Dùng 1 buổi trong thẻ", exact=True)).to_have_count(1)
    expect(page.get_by_text("Số buổi trong thẻ không xác nhận tình trạng thanh toán.", exact=False)).to_be_visible()
    no_overflow(page)
    if width == 1366:
        assert page.get_by_role("main").bounding_box()["width"] > 800
        page.get_by_role("link", name="Dùng 1 buổi trong thẻ", exact=True).click()
        expect(page.get_by_text("1. Dịch vụ", exact=True)).to_be_visible()
        assert page.get_by_role("main").bounding_box()["width"] < 800
        no_overflow(page)


def test_package_read_error_has_retry(scenario):
    s = scenario
    page = s["page"]()
    pattern = "**/api/v1/customer-packages/me"
    page.route(pattern, lambda r: r.fulfill(status=503, json={"detail": "QA packages unavailable"}))
    page.goto(s["url"] + "/profile")
    expect(page.get_by_role("main").get_by_role("alert")).to_contain_text("Chưa thể xử lý yêu cầu. Vui lòng thử lại sau.")
    page.unroute(pattern)
    page.get_by_role("button", name="Thử tải lại thẻ", exact=True).click()
    expect(page.get_by_text("QA One Session", exact=True)).to_be_visible()
