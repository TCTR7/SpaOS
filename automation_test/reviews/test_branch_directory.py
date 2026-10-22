"""Public directory layout and progressive branding; no artifacts."""
import pytest
from playwright.sync_api import expect
from common_setup.config import config
from features.customer_regressions.conftest import scenario


@pytest.mark.parametrize("width,columns", [(320, 1), (768, 2), (1366, 3)])
def test_directory_layout_branding_and_booking(scenario, width, columns):
    page = scenario["page"]("", True)
    page.set_viewport_size({"width": width, "height": 900})
    branches = [{"id": str(i), "slug": "directory-" + str(i), "name": "An Nhiên Spa — Chi nhánh " + str(i), "address": "12 Nguyễn Huệ, Quận 1", "contact_phone": "0901234567"} for i in range(3)]
    page.route("**/api/v1/branches/public", lambda r: r.fulfill(json={"brand_name": "An Nhiên Spa", "branches": branches}))
    def detail(route):
        i = route.request.url.rsplit("-", 1)[-1]
        route.fulfill(json={"id": i, "slug": "directory-" + i, "logo_url": "/icons/icon-192x192.png", "open_time": "09:00:00", "close_time": "20:00:00"})
    page.route("**/api/v1/public/tenants/directory-*", detail)
    page.goto(config.frontend_url + "/")
    cards = page.get_by_role("article")
    expect(cards).to_have_count(3)
    expect(page.get_by_text("Giờ mở cửa: 09:00 – 20:00", exact=True)).to_have_count(3)
    expect(cards.first.locator("img")).to_have_attribute("src", "/icons/icon-192x192.png")
    expect(page.get_by_role("banner")).to_contain_text("An Nhiên Spa")
    layout = cards.evaluate_all("els => els.map(e => ({x:e.getBoundingClientRect().x,y:e.getBoundingClientRect().y}))")
    assert len({round(p["x"]) for p in layout}) == columns
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    for i in range(3):
        action = cards.nth(i).get_by_role("link", name="Xem lịch trống tại " + branches[i]["name"], exact=True)
        expect(action).to_have_attribute("href", "/directory-" + str(i) + "/book")
        assert action.bounding_box()["height"] >= 44


def test_directory_optional_details_failure_keeps_booking(scenario):
    page = scenario["page"]("", True)
    page.route("**/api/v1/branches/public", lambda r: r.fulfill(json={"brand_name": "SpaOS", "branches": [{"id": "1", "slug": "one", "name": "Spa One"}, {"id":"2","slug":"two","name":"Spa Two"}]}))
    page.route("**/api/v1/public/tenants/one", lambda r: r.fulfill(status=503, json={}))
    page.goto(config.frontend_url + "/")
    expect(page.get_by_role("link", name="Xem lịch trống tại Spa One", exact=True)).to_be_visible()
    expect(page.get_by_role("banner")).to_contain_text("Đặt lịch spa")
    expect(page.get_by_text("Giờ mở cửa:", exact=False)).to_have_count(0)
