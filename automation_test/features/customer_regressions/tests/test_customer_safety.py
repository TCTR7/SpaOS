import re
from datetime import datetime, timedelta
from playwright.sync_api import expect


def test_cancel_releases_reserved_session(scenario):
    s = scenario
    booking = s["book"]()
    page = s["page"]()
    page.goto(s["url"] + "/profile")
    expect(page.get_by_text("Khả dụng: 0 buổi", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name="Đặt lịch dùng thẻ này (0₫)")).to_have_count(0)
    page.goto(s["url"] + "/appointments")
    with page.expect_response(lambda r: r.url.endswith("/" + booking["id"] + "/cancel")) as response:
        page.get_by_role("button", name="Hủy lịch", exact=True).click()
    assert response.value.status == 200
    expect(page.get_by_text("Bạn chưa có lịch hẹn nào sắp diễn ra.", exact=True)).to_be_visible()
    page.get_by_role("button", name="Lịch sử", exact=True).click()
    expect(page.get_by_text("QA Treatment (30p)", exact=True)).to_be_visible()
    page.goto(s["url"] + "/profile")
    expect(page.get_by_text("Khả dụng: 1 buổi", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name="Đặt lịch dùng thẻ này (0₫)")).to_be_visible()


def test_cannot_cancel_within_two_hours(scenario):
    s = scenario
    booking = s["book"]()
    page = s["page"]()
    target_dt = datetime.fromisoformat(booking["start_time"].replace("Z", "+00:00")) - timedelta(minutes=30)
    page.clock.set_fixed_time(target_dt)
    page.goto(s["url"] + "/appointments")
    expect(page.get_by_role("button", name="Sát giờ (<2h)", exact=True)).to_be_disabled()


def test_last_session_completed_is_not_bookable(scenario):
    s = scenario
    booking = s["book"]()
    for status in ("CONFIRMED", "COMPLETED", "COMPLETED"):
        s["call"]("PATCH", "/bookings/" + booking["id"] + "/status", json={"status": status})
    page = s["page"]()
    page.goto(s["url"] + "/profile")
    expect(page.get_by_text("1/1 buổi", exact=True)).to_be_visible()
    expect(page.get_by_text("COMPLETED", exact=True)).to_be_visible()
    expect(page.get_by_text("Khả dụng: 0 buổi", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name="Đặt lịch dùng thẻ này (0₫)")).to_have_count(0)


def test_package_load_error_is_visible_and_recovers(scenario):
    s = scenario
    page = s["page"]()
    pattern = "**/api/v1/customer-packages/me"
    page.route(pattern, lambda route: route.fulfill(status=503, json={"detail": "QA temporarily unavailable"}))
    page.goto(s["url"] + "/profile")
    expect(page.get_by_role("main").get_by_role("alert")).to_have_text("QA temporarily unavailable")
    expect(page.get_by_text("QA One Session", exact=True)).to_have_count(0)
    page.unroute(pattern)
    page.reload()
    expect(page.get_by_text("QA One Session", exact=True)).to_be_visible()
    expect(page.get_by_role("main").get_by_role("alert")).to_have_count(0)


def test_customer_token_cannot_open_admin(scenario):
    s = scenario
    page = s["page"](admin_slot=True)
    page.goto(s["url"].split("/" + s["slug"])[0] + "/admin/reports")
    expect(page).to_have_url(re.compile(r"/admin/login$"))
    assert page.evaluate("localStorage.getItem('spaos_admin_token')") is None
    response = page.request.get(s["url"].split("/" + s["slug"])[0] + "/api/v1/customers",
                                headers={"Authorization": "Bearer " + s["token"]})
    assert response.status == 403


def test_invalid_customer_token_is_cleared(scenario):
    s = scenario
    page = s["page"]("invalid-token")
    page.goto(s["url"] + "/profile")
    expect(page.get_by_role("main").get_by_role("link", name="Đăng nhập", exact=True)).to_be_visible()
    assert page.evaluate("(key) => localStorage.getItem(key)", "spaos_customer_token_" + s["slug"]) is None


def test_customer_login_failure_success_and_logout(scenario):
    s = scenario
    page = s["page"]("")
    page.goto(s["url"] + "/login")
    page.locator("#custPhone").fill(s["phone"])
    page.locator("#custPassword").fill("wrong-password")
    with page.expect_response(lambda r: r.url.endswith("/auth/login")) as response:
        page.get_by_role("button", name="Đăng nhập", exact=True).click()
    assert response.value.status == 401
    expect(page.get_by_text("Sai số điện thoại hoặc mật khẩu", exact=True)).to_be_visible()
    page.locator("#custPassword").fill("Customer@123")
    with page.expect_response(lambda r: r.url.endswith("/auth/login")) as response:
        page.get_by_role("button", name="Đăng nhập", exact=True).click()
    assert response.value.status == 200
    expect(page).to_have_url(s["url"] + "/book")
    page.goto(s["url"] + "/profile")
    page.get_by_role("button", name="Thoát", exact=True).click()
    expect(page.get_by_role("main").get_by_role("link", name="Đăng nhập", exact=True)).to_be_visible()
    assert page.evaluate("(key) => localStorage.getItem(key)", "spaos_customer_token_" + s["slug"]) is None


def test_customer_notifications_can_be_marked_read(scenario):
    s = scenario
    booking = s["book"]()
    s["call"]("PATCH", "/bookings/" + booking["id"] + "/status", json={"status": "CONFIRMED"})
    page = s["page"]()
    page.goto(s["url"] + "/profile")
    page.get_by_role("button", name="Thông báo lịch hẹn", exact=True).click()
    expect(page.get_by_text("Lịch hẹn đã được xác nhận", exact=True)).to_be_visible()
    with page.expect_response(lambda r: r.url.endswith("/notifications/read-all")) as response:
        page.get_by_role("button", name="Đọc hết", exact=True).click()
    assert response.value.status == 200
    assert response.value.json()["updated"] == 1
    expect(page.get_by_text("Thông báo (0 mới)", exact=True)).to_be_visible()
    page.reload()
    page.get_by_role("button", name="Thông báo lịch hẹn", exact=True).click()
    expect(page.get_by_text("Thông báo (0 mới)", exact=True)).to_be_visible()


def test_other_spa_does_not_reuse_customer_token(scenario, api_helper):
    from common_setup.api_helper import random_phone, unique_suffix
    from common_setup.config import config
    s = scenario
    other_slug = "qa-other-" + unique_suffix().replace("_", "-")
    api_helper.register_tenant("Other Spa", other_slug, "Other Admin", random_phone())
    page = s["page"]()
    page.goto(s["url"] + "/profile")
    expect(page.get_by_text("QA One Session", exact=True)).to_be_visible()
    requests = []
    page.on("request", lambda r: requests.append(r) if "/api/v1/" in r.url else None)
    page.goto(config.frontend_url + "/" + other_slug + "/profile")
    expect(page.get_by_role("main").get_by_role("link", name="Đăng nhập", exact=True)).to_be_visible()
    expect(page.get_by_text("QA One Session", exact=True)).to_have_count(0)
    tenant_request = next(r for r in requests if "/public/tenants/" + other_slug in r.url)
    assert tenant_request.headers["x-tenant-slug"] == other_slug
    assert "authorization" not in tenant_request.headers
    page.goto(s["url"] + "/profile")
    expect(page.get_by_text("QA One Session", exact=True)).to_be_visible()


def test_slot_taken_before_confirmation_shows_conflict(scenario, api_helper):
    from features.client_pwa_booking.pages.booking_wizard_page import BookingWizardPage
    s = scenario
    page = s["page"]()
    wizard = BookingWizardPage(page)
    wizard.open_wizard(s["slug"])
    wizard.step1_select_service_by_name("QA Treatment")
    wizard.step2_choose_auto_assign_staff()
    day = (datetime.now() + timedelta(days=6)).date().isoformat()
    with page.expect_response(lambda r: "/bookings/available-slots?" in r.url and "date=" + day in r.url) as slots:
        page.locator("#wizDate").fill(day)
    assert slots.value.status == 200
    start = slots.value.json()["slots"][0]["start_time"]
    page.locator("button:has-text('KTV trống')").first.click()
    page.get_by_role("button", name="Tiếp tục", exact=True).click()
    rival = api_helper.create_booking(s["token"], start, [{"service_id": s["service"]["id"]}])
    try:
        with page.expect_response(lambda r: r.url.endswith("/bookings") and r.request.method == "POST") as response:
            wizard.step4_confirm_booking("QA stale slot")
        assert response.value.status == 409
        expect(page.get_by_text(response.value.json()["detail"], exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="Xác nhận Đặt lịch", exact=True)).to_be_enabled()
        records = s["call"]("GET", "/bookings")
        assert [b["id"] for b in records] == [rival["id"]]
    finally:
        s["call"]("POST", "/bookings/" + rival["id"] + "/cancel")
