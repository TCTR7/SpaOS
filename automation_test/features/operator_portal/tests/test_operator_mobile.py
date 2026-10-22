import pytest
from playwright.sync_api import expect
from common_setup.config import config
from features.operator_portal.pages.operator_page import OperatorPage


@pytest.mark.parametrize("width", [320, 390, 768, 1366])
def test_operator_routes_long_names_error_retry_and_brand_preview(operator_ui, width):
    page_for, _ = operator_ui
    page = page_for()
    page.set_viewport_size({"width": width, "height": 844})
    page.goto(config.frontend_url + "/operator/login")
    expect(page.get_by_label("Số điện thoại quản trị", exact=True)).to_be_visible()
    expect(page.get_by_label("Mật khẩu", exact=True)).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
    ui = OperatorPage(page)
    ui.login()
    page.locator("#ownerName").fill("LongOwnerName" * 18)
    page.locator("#firstBranch").fill("LongBranchName" * 18)
    page.locator("#ownerPhone").fill("0901234567")
    for color in ["#ffff00", "#000080"]:
        page.locator("#ownerThemeColor").fill(color)
        expect(page.get_by_test_id("preview-ownerThemeColor")).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
    page.evaluate("document.documentElement.classList.add('dark')")
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
    # Reload only before creating any provisioning attempt.
    pattern = "**/api/v1/operator/owners?*"
    page.route(pattern, lambda r: r.fulfill(status=503, json={"detail": "LongOwnerListFailure" * 30}))
    page.reload()
    expect(page.get_by_role("alert").filter(has_text="Chưa thể xử lý yêu cầu. Vui lòng thử lại sau.")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
    page.unroute(pattern)
    page.get_by_role("button", name="Thử tải lại danh sách", exact=True).click()
    expect(page.locator("#ownerName")).to_be_visible()
    expect(page.get_by_role("alert").filter(has_text="Chưa thể xử lý yêu cầu. Vui lòng thử lại sau.")).to_have_count(0)
