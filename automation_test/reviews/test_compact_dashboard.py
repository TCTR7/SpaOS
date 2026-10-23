"""Brand assets, saved logo and compact dashboard through the real QA API."""
import base64
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
import uuid
from zoneinfo import ZoneInfo
import pytest
from PIL import Image
from playwright.sync_api import expect
from common_setup.config import config
from features.customer_regressions.conftest import scenario

ICONS = Path(__file__).resolve().parents[2] / "frontend" / "public" / "icons"


@pytest.mark.parametrize("width", [390, 1366])
def test_logo_upload_refresh_reload_and_replace(scenario, width):
    s = scenario
    page = s["page"](s["admin"], True)
    page.set_viewport_size({"width": width, "height": 900})
    page.goto(config.frontend_url + "/admin/settings")
    for icon in ["icon-192x192.png", "icon-512x512.png"]:
        page.locator("#logoFile").set_input_files(str(ICONS / icon))
        preview = page.get_by_role("img", name="Xem trước logo chi nhánh", exact=True)
        expect(preview).to_be_visible()
        with page.expect_response(lambda r: r.request.method == "PATCH" and r.url.endswith("/tenants/me")) as saved:
            page.get_by_role("button", name="Lưu thay đổi", exact=True).click()
        assert saved.value.status == 200
        logo_url = saved.value.json()["logo_url"]
        header = page.locator("header").get_by_role("img", name="Logo QA Spa", exact=True)
        expect(header).to_have_attribute("src", logo_url)
        expect(header).to_be_visible()
        expect(page.get_by_text("Đã lưu cấu hình Spa thành công!", exact=True)).to_be_visible()
        expect(header).to_have_js_property("complete", True)
        assert header.evaluate("(image) => image.naturalWidth > 0")
        image = page.request.get(config.frontend_url + logo_url)
        assert image.status == 200
        assert image.body() == (ICONS / icon).read_bytes()
        page.reload()
        expect(page.locator("header").get_by_role("img", name="Logo QA Spa", exact=True)).to_have_attribute("src", logo_url)
    assert s["call"]("GET", "/tenants/me")["logo_url"] == logo_url


def test_broken_logo_reports_error_with_fallback(scenario):
    s = scenario
    page = s["page"](s["admin"], True)
    page.route("**/missing-logo.png", lambda route: route.fulfill(status=404))
    page.goto(config.frontend_url + "/admin/settings")
    page.locator("#logoUrl").fill(config.frontend_url + "/missing-logo.png")
    expect(page.get_by_role("alert").filter(has_text="Không tải được logo")).to_be_visible()
    expect(page.get_by_role("img", name="Xem trước logo chi nhánh", exact=True)).to_be_visible()
    page.locator("#logoFile").set_input_files(str(ICONS / "icon-192x192.png"))
    expect(page.get_by_role("alert").filter(has_text="Không tải được logo")).to_have_count(0)


def test_branch_switch_uses_own_logo_and_all_scope_uses_app_mark(scenario, api_helper):
    s = scenario
    first = s["call"]("PATCH", "/tenants/me", json={"logo_data": base64.b64encode((ICONS / "icon-192x192.png").read_bytes()).decode()})
    branch = s["call"]("POST", "/branches", json={"name": "QA Logo Branch"})["tenant"]
    switch = s["call"]("POST", "/branches/" + branch["id"] + "/switch")
    response = api_helper.client.patch("/tenants/me", headers={"Authorization": "Bearer " + switch["access_token"]}, json={"logo_data": base64.b64encode((ICONS / "icon-512x512.png").read_bytes()).decode()})
    response.raise_for_status()
    second = response.json()
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/dashboard")
    expect(page.locator("header img")).to_have_attribute("src", first["logo_url"])
    page.locator("#activeBranch").select_option(branch["id"])
    expect(page.locator("header img")).to_have_attribute("src", second["logo_url"])
    page.locator("#activeBranch").select_option("all")
    expect(page.locator("header img")).to_have_attribute("alt", "Logo SpaOS")
    expect(page.locator("header img")).to_have_attribute("src", "/icons/icon-192x192.png?v=20261023")


def test_manifest_pngs_have_a_visible_mark_and_ios_icon(scenario):
    s = scenario
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/dashboard")
    for path in ["/manifest.json", "/manifest.webmanifest", "/admin/app.webmanifest", "/" + s["slug"] + "/app.webmanifest"]:
        response = page.request.get(config.frontend_url + path)
        assert response.status == 200
        manifest = response.json()
        assert {"any", "maskable"}.issubset({icon["purpose"] for icon in manifest["icons"]})
        for icon in manifest["icons"]:
            response = page.request.get(config.frontend_url + icon["src"])
            assert response.status == 200
            image = Image.open(BytesIO(response.body())).convert("RGB")
            assert image.size == tuple(map(int, icon["sizes"].split("x")))
            colors = image.getcolors(image.width * image.height)
            assert len(colors) > 2, "Icon must contain an antialiased mark, not a flat color"
            assert any(color == (255, 255, 255) for _, color in colors)
    apple = page.locator('link[rel="apple-touch-icon"]')
    expect(apple).to_have_attribute("href", "/icons/apple-touch-icon.png?v=20261023")
    image = Image.open(BytesIO(page.request.get(config.frontend_url + apple.get_attribute("href")).body()))
    assert image.size == (180, 180)


@pytest.mark.parametrize("width", [320, 390, 768, 1366])
def test_dashboard_collapsed_lazy_details_and_mobile_fit(scenario, width):
    s = scenario
    page = s["page"](s["admin"], True)
    page.set_viewport_size({"width": width, "height": 900})
    requests = []
    page.on("request", lambda r: requests.append(r.url))
    page.goto(config.frontend_url + "/admin/dashboard")
    panels = page.get_by_test_id("branch-dashboard")
    expect(panels).to_have_attribute("aria-busy", "false")
    for test_id in ["dashboard-appointments", "dashboard-received", "dashboard-outstanding", "dashboard-packages", "branch-setup-guide"]:
        panel = page.get_by_test_id(test_id)
        expect(panel).to_be_visible()
        expect(panel).not_to_have_attribute("open", "")
    assert not any("/api/v1/bookings?" in url or "/api/v1/payments/collections?" in url for url in requests)
    appointments = page.get_by_test_id("dashboard-appointments")
    appointments.locator("summary").click()
    expect(appointments.get_by_role("link", name="Mở lịch hẹn", exact=True)).to_be_visible()
    expect(appointments.get_by_text("Không có lịch.", exact=True)).to_have_count(3)
    appointments.locator("summary").click()
    expect(appointments.get_by_role("link", name="Mở lịch hẹn", exact=True)).to_have_count(0)
    outstanding = page.get_by_test_id("dashboard-outstanding")
    outstanding.locator("summary").click()
    expect(outstanding.get_by_text("QA Customer", exact=True)).to_be_visible()
    expect(outstanding.get_by_role("link", name="Thu tiền", exact=True)).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    assert page.get_by_role("button", name="Hướng dẫn & Cài ứng dụng", exact=True).count() == 0


def test_day_scope_and_current_debt_are_distinct(scenario):
    s = scenario
    invoice = s["call"]("POST", "/payments/invoices", json={"customer_package_id": s["package"]["id"]})
    s["call"]("POST", "/payments/invoices/" + invoice["id"] + "/receipts", json={"amount": "100000", "method": "CASH", "idempotency_key": str(uuid.uuid4())})
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/dashboard")
    received = page.get_by_test_id("dashboard-received")
    debt = page.get_by_test_id("dashboard-outstanding")
    expect(received.locator("summary")).to_contain_text("100.000")
    expect(debt.locator("summary")).to_contain_text("150.000")
    yesterday = (datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date() - timedelta(days=1)).isoformat()
    received.locator("summary").click()
    expect(received).to_have_attribute("open", "")
    page.locator("#dashboardDay").fill(yesterday)
    expect(page.get_by_test_id("branch-dashboard")).to_have_attribute("aria-busy", "false")
    expect(received).not_to_have_attribute("open", "")
    expect(received.locator("summary")).not_to_contain_text("100.000")
    expect(received.locator("summary")).to_contain_text("0")
    expect(debt.locator("summary")).to_contain_text("150.000")
    expect(debt.locator("summary")).to_contain_text("Tất cả ngày")
    page.get_by_role("button", name="Hôm nay", exact=True).click()
    expect(received.locator("summary")).to_contain_text("100.000")


def test_setup_disappears_only_when_all_required_information_exists(scenario):
    s = scenario
    s["call"]("PATCH", "/tenants/me", json={"address": "QA Address", "contact_phone": "0901234567"})
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/dashboard")
    expect(page.get_by_test_id("branch-dashboard")).to_have_attribute("aria-busy", "false")
    expect(page.get_by_test_id("branch-setup-guide")).to_have_count(0)

def test_dashboard_keyboard_toggle(scenario):
    s = scenario
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/dashboard")
    panel = page.get_by_test_id("dashboard-received")
    summary = panel.locator("summary").first
    summary.focus()
    page.keyboard.press("Enter")
    expect(panel).to_have_attribute("open", "")
    expect(panel.get_by_text("Tiền mặt", exact=True)).to_be_visible()
    page.keyboard.press("Space")
    expect(panel).not_to_have_attribute("open", "")


def test_previous_day_response_cannot_replace_current_day(scenario):
    s = scenario
    today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    yesterday = (today - timedelta(days=1)).isoformat()
    old_data = s["call"]("GET", "/dashboard?day=" + today.isoformat())
    old_data["totals"]["net_received"] = "9999999.00"
    held = []
    page = s["page"](s["admin"], True)
    page.route("**/api/v1/dashboard?day=" + today.isoformat() + "&*", lambda route: held.append(route))
    page.goto(config.frontend_url + "/admin/dashboard")
    expect(page.get_by_test_id("dashboard-received").locator("summary")).to_contain_text("Đang tải")
    page.locator("#dashboardDay").fill(yesterday)
    expect(page.get_by_test_id("branch-dashboard")).to_have_attribute("aria-busy", "false")
    assert held
    with page.expect_response(lambda response: "/dashboard?day=" + today.isoformat() in response.url):
        held[0].fulfill(json=old_data)
    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
    expect(page.locator("#dashboardDay")).to_have_value(yesterday)
    expect(page.get_by_test_id("branch-dashboard")).to_have_attribute("aria-busy", "false")
    expect(page.get_by_test_id("dashboard-received").locator("summary")).to_contain_text("0")
    expect(page.get_by_test_id("dashboard-received").locator("summary")).not_to_contain_text("9.999.999")
