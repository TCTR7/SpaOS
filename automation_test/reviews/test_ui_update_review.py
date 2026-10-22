"""UI review regressions and brand probe; console only."""
from playwright.sync_api import expect
from common_setup.config import config
from features.customer_regressions.conftest import scenario


def test_review_profile_feedback(scenario):
    s = scenario
    page = s["page"]()
    page.goto(s["url"] + "/profile")
    page.locator("summary").filter(has_text="Sửa hồ sơ và mật khẩu").click()
    page.get_by_label("Họ và tên", exact=True).fill("Review Updated Name")
    page.get_by_role("button", name="Lưu họ tên", exact=True).click()
    expect(page.get_by_role("main").get_by_text("Review Updated Name", exact=True)).to_be_visible()
    expect(page.get_by_text("Đã cập nhật họ tên.", exact=True)).to_be_visible()
    expect(page.locator("details").filter(has_text="Sửa hồ sơ và mật khẩu")).to_have_attribute("open", "")
    page.reload()
    expect(page.get_by_role("main").get_by_text("Review Updated Name", exact=True)).to_be_visible()


def test_review_recovery_spacing(scenario):
    s = scenario
    page = s["page"](s["admin"], True)
    page.set_viewport_size({"width": 1366, "height": 900})
    page.goto(config.frontend_url + "/admin/customers")
    page.get_by_role("button").filter(has_text="QA Customer").first.click()
    page.locator("summary").filter(has_text="Giúp khách đăng nhập").click()
    password = page.locator("#recoveryOwnerPassword")
    action = page.get_by_role("button", name="Cấp liên kết cho khách", exact=True)
    expect(password).to_be_visible()
    expect(action).to_be_visible()
    a, b = password.bounding_box(), action.bounding_box()
    assert b["y"] - a["y"] - a["height"] >= 12


def test_review_light_brand_action_link(scenario):
    s = scenario
    s["call"]("PATCH", "/tenants/me", json={"theme_color": "#ffff00"})
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/dashboard")
    link = page.get_by_role("link", name="Xem toàn bộ khoản cần thu", exact=True)
    expect(link).to_be_visible()
    print("REVIEW_LINK_COLOR", link.evaluate("e => ({color:getComputedStyle(e).color, background:getComputedStyle(e).backgroundColor, primary:getComputedStyle(e).getPropertyValue('--primary'), text:getComputedStyle(e).getPropertyValue('--primary-text')})"))
