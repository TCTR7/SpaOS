"""UI consistency checks on disposable QA data; no artifacts."""
from playwright.sync_api import expect
from common_setup.config import config
from features.customer_regressions.conftest import scenario


def fits(page):
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")


def test_mobile_long_actions_and_customer_targets(scenario):
    s = scenario
    page = s["page"](s["admin"], True)
    page.set_viewport_size({"width": 320, "height": 844})
    page.goto(config.frontend_url + "/admin/branches")
    page.get_by_label("Tên chi nhánh", exact=True).fill("QA New Branch")
    page.get_by_role("button", name="Tạo chi nhánh", exact=True).click()
    next_step = page.get_by_role("button", name="Chuyển sang thiết lập chi nhánh mới", exact=True)
    expect(next_step).to_be_visible()
    fits(page)
    assert next_step.bounding_box()["width"] <= 288
    page.goto(config.frontend_url + "/admin/staff")
    page.get_by_role("button").filter(has_text="QA Staff").first.click()
    page.locator("summary").filter(has_text="Sao chép giờ làm cho cả tuần").click()
    expect(page.get_by_role("button", name="Áp dụng giờ Thứ 2 cho các ngày", exact=True)).to_be_visible()
    fits(page)
    page.goto(s["url"])
    expect(page.get_by_role("link", name="Xem giờ trống", exact=True)).to_be_visible()
    for control in [page.get_by_role("link", name="Xem giờ trống", exact=True), page.get_by_role("link", name="Đặt lịch hẹn ngay", exact=True), page.get_by_role("button", name="Tất cả (1)", exact=True)]:
        assert control.bounding_box()["height"] >= 44
    fits(page)


def test_dashboard_summary_expands_without_duplicate_sections(scenario):
    s = scenario
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/dashboard?scope=all")
    page.get_by_test_id("dashboard-branches").locator("summary").first.click()
    branch = page.get_by_test_id("dashboard-" + s["call"]("GET", "/tenants/me")["id"])
    expect(branch).to_be_visible()
    expect(branch).not_to_have_attribute("open", "")
    branch.locator("summary").click()
    expect(branch).to_have_attribute("open", "")
    expect(branch.get_by_text("Tiền đã thu trong ngày", exact=True)).to_be_visible()
    page.set_viewport_size({"width": 320, "height": 844})
    fits(page)
    page.goto(config.frontend_url + "/admin/dashboard")
    expect(page.get_by_test_id("branch-setup-guide")).to_have_count(1)
    expect(page.get_by_test_id("dashboard-outstanding")).to_have_count(1)
    page.get_by_test_id("dashboard-outstanding").locator("summary").click()
    expect(page.get_by_role("main").get_by_role("link", name="Thu tiền", exact=True)).to_be_visible()
    fits(page)
