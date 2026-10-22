"""Role workflows on the isolated QA deployment; console results only."""
import re
from datetime import datetime, timedelta, timezone
import pytest
from playwright.sync_api import expect
from common_setup.config import config
from features.client_pwa_booking.pages.booking_wizard_page import BookingWizardPage


def day():
    return (datetime.now(timezone(timedelta(hours=7))) + timedelta(days=7)).date().isoformat()


def test_contacts_and_setup_use_saved_branch_data(scenario):
    s = scenario
    s["call"]("PATCH", "/tenants/me", json={"address": "123 QA Street", "contact_phone": "0901234567"})
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/dashboard")
    guide = page.locator("details").filter(has_text="Thiết lập chi nhánh và chia sẻ đặt lịch")
    expect(guide).to_have_count(1)
    for selected_day in ("2026-10-22", "2026-10-23"):
        page.locator("#dashboardDay").fill(selected_day)
        expect(page.get_by_test_id("branch-dashboard")).to_be_visible()
        expect(guide).to_have_count(1)
    guide.locator("summary").click()
    expect(guide).to_contain_text("Đã có địa chỉ và số liên hệ")
    for width in (320, 390, 1366):
        page.set_viewport_size({"width": width, "height": 900})
        expect(guide.get_by_role("button", name="Sao chép đường dẫn cho khách", exact=True)).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    expect(guide.get_by_role("link", name=re.compile("3. Nhân viên"))).to_contain_text("1/1")
    page.goto(s["url"])
    expect(page.get_by_role("link", name="Gọi spa: 0901234567", exact=True)).to_have_attribute("href", "tel:0901234567")
    expect(page.get_by_role("link", name="123 QA Street · Đường đi", exact=True)).to_have_attribute("href", re.compile("https://www.google.com/maps/"))


def test_setup_error_has_retry_instead_of_empty_counts(scenario):
    s = scenario
    page = s["page"](s["admin"], True)
    pattern = "**/api/v1/tenants/me/setup"
    page.route(pattern, lambda route: route.fulfill(status=503, json={"detail": "QA unavailable"}))
    page.goto(config.frontend_url + "/admin/dashboard")
    guide = page.locator("details").filter(has_text="Thiết lập chi nhánh và chia sẻ đặt lịch")
    guide.locator("summary").click()
    expect(guide.get_by_role("alert")).to_contain_text("Chưa kiểm tra được")
    page.unroute(pattern)
    guide.get_by_role("button", name="Thử lại thiết lập", exact=True).click()
    expect(guide.get_by_role("link", name=re.compile("3. Nhân viên"))).to_contain_text("1/1")


def test_staff_reads_own_week_and_date_override(scenario, api_helper):
    s = scenario
    s["call"]("PUT", "/staff/" + s["staff"]["id"] + "/date-overrides", json={"day": day(), "is_day_off": True})
    token = api_helper.login(s["slug"], s["staff"]["phone_number"], "Staff@123")["access_token"]
    page = s["page"](token, True)
    page.goto(config.frontend_url + "/admin/work-hours")
    expect(page.get_by_role("heading", name="Ca làm của tôi", exact=True)).to_be_visible()
    expect(page.get_by_role("main")).to_contain_text(datetime.fromisoformat(day()).strftime("%d/%m/%Y") + " · Nghỉ")
    expect(page.get_by_role("main").locator("input,select,textarea")).to_have_count(0)
    expect(page.get_by_role("link", name="Thu tiền", exact=True)).to_have_count(0)


def test_owner_can_save_date_off_and_staff_keeps_week(scenario):
    s = scenario
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/staff")
    page.get_by_role("button").filter(has_text="QA Staff").first.click()
    region = page.get_by_role("region", name="Ca riêng theo ngày", exact=True)
    region.locator("#overrideDay").fill(day())
    with page.expect_response(lambda r: "/date-overrides" in r.url and r.request.method == "PUT") as saved:
        region.get_by_role("button", name="Lưu ca cho ngày này", exact=True).click()
    assert saved.value.status == 200
    expect(region).to_contain_text(datetime.fromisoformat(day()).strftime("%d/%m/%Y") + " · Nghỉ")
    assert len(s["call"]("GET", "/staff/" + s["staff"]["id"] + "/schedules")) == 7
    region.get_by_role("button", name="Trở về ca tuần", exact=True).click()
    expect(region.get_by_text(datetime.fromisoformat(day()).strftime("%d/%m/%Y") + " · Nghỉ", exact=True)).to_have_count(0)


def test_handover_is_saved_for_booking_and_assigned_staff_reads_only(scenario, api_helper):
    s = scenario
    from common_setup.api_helper import random_phone
    profile_owner = s["call"]("POST", "/staff", json={"full_name": "Profile Owner", "phone_number": random_phone(), "password": "Staff@123"})
    s["call"]("PATCH", "/customers/" + s["customer"]["id"] + "/assignment", json={"assigned_staff_id": profile_owner["id"]})
    booking = s["book"]()
    owner = s["page"](s["admin"], True)
    owner.goto(config.frontend_url + "/admin/bookings?booking_id=" + booking["id"])
    region = owner.get_by_role("region", name="Bàn giao buổi hẹn", exact=True)
    region.locator("#handoverNote").fill("Discussed instructions for this visit")
    region.get_by_role("button", name="Lưu bàn giao", exact=True).click()
    expect(region.get_by_role("status")).to_contain_text("Đã lưu")
    token = api_helper.login(s["slug"], s["staff"]["phone_number"], "Staff@123")["access_token"]
    staff = s["page"](token, True)
    staff.goto(config.frontend_url + "/admin/bookings?booking_id=" + booking["id"])
    read = staff.get_by_role("region", name="Bàn giao buổi hẹn", exact=True)
    expect(read).to_contain_text("Discussed instructions for this visit")
    expect(read.locator("textarea")).to_have_count(0)
    expect(read.get_by_role("button", name="Lưu bàn giao", exact=True)).to_have_count(0)


def test_verified_recovery_link_sets_customer_password_once(scenario, api_helper):
    s = scenario
    owner = s["page"](s["admin"], True)
    owner.goto(config.frontend_url + "/admin/customers")
    owner.get_by_role("button").filter(has_text="QA Customer").first.click()
    details = owner.locator("details").filter(has_text="Giúp khách đăng nhập hoặc đặt lại mật khẩu")
    details.locator("summary").click()
    expect(details.get_by_role("button", name="Cấp liên kết cho khách", exact=True)).to_be_disabled()
    details.get_by_role("checkbox").check()
    details.locator("#recoveryOwnerPassword").fill("Admin@123")
    details.get_by_role("button", name="Cấp liên kết cho khách", exact=True).click()
    link = details.locator("p").filter(has_text=re.compile("/activate#"))
    expect(link).to_be_visible()
    address = link.inner_text()
    customer = s["page"]("")
    customer.goto(address)
    expect(customer).to_have_url(s["url"] + "/activate")
    customer.locator("#activatePassword").fill("NewCustomer@123")
    with customer.expect_response(lambda r: r.url.endswith("/auth/recovery") and r.request.method == "POST") as claimed:
        customer.get_by_role("button", name="Đặt mật khẩu", exact=True).click()
    assert claimed.value.status == 200, "Recovery returned HTTP " + str(claimed.value.status)
    expect(customer).to_have_url(s["url"] + "/login?password_set=1")
    expect(customer.get_by_role("status")).to_contain_text("Đã đặt mật khẩu")
    assert api_helper.login(s["slug"], s["phone"], "NewCustomer@123")["user"]["id"] == s["customer"]["id"]
    customer.goto(address)
    customer.locator("#activatePassword").fill("AnotherSecret@123")
    customer.get_by_role("button", name="Đặt mật khẩu", exact=True).click()
    expect(customer.get_by_role("main").get_by_role("alert")).to_contain_text("Liên kết không còn hiệu lực")


def test_profile_edit_does_not_change_login_phone(scenario):
    s = scenario
    page = s["page"]()
    page.goto(s["url"] + "/profile")
    page.get_by_text("Sửa hồ sơ và mật khẩu", exact=True).click()
    page.locator("#profileName").fill("Updated QA Customer")
    with page.expect_response(lambda r: r.url.endswith("/account/profile") and r.request.method == "PATCH") as updated:
        page.get_by_role("button", name="Lưu họ tên", exact=True).click()
    assert updated.value.status == 200, "Profile returned HTTP " + str(updated.value.status)
    expect(page.get_by_role("main").get_by_text("Updated QA Customer", exact=True)).to_be_visible()
    customer = s["call"]("GET", "/customers/" + s["customer"]["id"])
    assert customer["phone_number"] == s["phone"]


def test_card_history_shows_actual_reserved_visit(scenario):
    s = scenario
    booking = s["book"]()
    page = s["page"]()
    page.goto(s["url"] + "/profile")
    page.get_by_role("button", name="Lịch sử các buổi", exact=True).click()
    expect(page.get_by_text("Chỉ buổi đã hoàn thành mới được tính là đã dùng.", exact=False)).to_be_visible()
    expect(page.get_by_text(re.compile(".*Chờ xác nhận$")).last).to_be_visible()
    assert s["call"]("GET", "/customer-packages/" + s["package"]["id"] + "/history")[0]["booking_id"] == booking["id"]


def test_crm_shortcut_keeps_selected_customer(scenario):
    s = scenario
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/customers")
    page.get_by_role("button").filter(has_text="QA Customer").first.click()
    page.get_by_role("link", name="Đặt lịch cho khách", exact=True).click()
    modal = page.get_by_role("dialog", name="Tạo lịch hẹn tại quầy", exact=True)
    expect(modal.get_by_role("button").filter(has_text="QA Customer")).to_have_attribute("aria-pressed", "true")
    expect(modal.get_by_role("button", name="Xác nhận tạo lịch", exact=True)).to_be_disabled()


def test_offline_banner_does_not_replay_writes(scenario):
    s = scenario
    page = s["page"]()
    page.goto(s["url"] + "/appointments")
    expect(page.get_by_role("heading", name="Lịch hẹn của tôi", exact=True)).to_be_visible()
    writes = []
    page.on("request", lambda r: writes.append(r.url) if r.method != "GET" else None)
    page.context.set_offline(True)
    expect(page.get_by_role("status").filter(has_text="mất kết nối")).to_be_visible()
    page.context.set_offline(False)
    expect(page.get_by_role("status").filter(has_text="mất kết nối")).to_have_count(0)
    assert writes == []


def test_lost_customer_commit_response_is_recovered_after_reload(scenario):
    s = scenario
    page = s["page"]()
    page.goto(s["url"] + "/book?package_id=" + s["package"]["id"] + "&service_id=" + s["service"]["id"])
    BookingWizardPage(page).step2_select_date_and_first_slot(day())
    sent = []
    def lose(route):
        response = route.fetch()
        assert response.status == 201
        sent.append(route.request.post_data_json["request_id"])
        route.abort("failed")
    pattern = "**/api/v1/booking-requests"
    page.route(pattern, lose)
    page.get_by_role("button", name="Xác nhận Đặt lịch", exact=True).click()
    expect(page.get_by_role("button", name="Kiểm tra lịch đã đặt", exact=True)).to_be_visible()
    page.reload()
    page.get_by_role("button", name="Kiểm tra lịch đã đặt", exact=True).click()
    page.wait_for_url("**/appointments?booking_id=*")
    rows = s["call"]("GET", "/bookings")
    assert len(rows) == 1 and len(sent) == 1
    packages = s["call"]("GET", "/customer-packages/me", headers={"Authorization": "Bearer " + s["token"]})
    assert packages[0]["reserved_sessions"] == 1


def test_calendar_download_does_not_write_booking(scenario):
    s = scenario
    booking = s["book"]()
    page = s["page"]()
    page.goto(s["url"] + "/appointments?booking_id=" + booking["id"])
    with page.expect_download() as download:
        page.get_by_role("button", name="Thêm vào lịch cá nhân", exact=True).click()
    assert download.value.suggested_filename == "lich-hen.ics"
    download.value.delete()
    assert s["call"]("GET", "/bookings/" + booking["id"])["status"] == "PENDING"


def test_late_password_response_cannot_restore_logged_out_customer(scenario):
    s = scenario
    page = s["page"]()
    page.goto(s["url"] + "/profile")
    page.get_by_text("Sửa hồ sơ và mật khẩu", exact=True).click()
    held = []
    def hold(route):
        held.append((route, route.fetch()))
        page.evaluate("window.qaCredentialHeld = true")
    page.route("**/api/v1/account/credentials", hold)
    page.locator("#credentialCurrent").fill("Customer@123")
    page.locator("#credentialNew").fill("ChangedCustomer@123")
    page.get_by_role("button", name="Cập nhật tài khoản", exact=True).click()
    page.wait_for_function("window.qaCredentialHeld === true")
    page.get_by_role("button", name="Thoát", exact=True).click()
    assert page.evaluate("slug => localStorage.getItem('spaos_customer_token_' + slug) === null", s["slug"])
    with page.expect_response(lambda r: r.url.endswith("/account/credentials")) as response:
        held[0][0].fulfill(response=held[0][1])
    assert response.value.status == 200
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    assert page.evaluate("slug => localStorage.getItem('spaos_customer_token_' + slug) === null", s["slug"])


def test_logo_preview_is_saved_with_branch_settings(scenario):
    import base64
    s = scenario
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/settings")
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
    page.locator("#logoFile").set_input_files({"name": "logo.png", "mimeType": "image/png", "buffer": png})
    expect(page.get_by_alt_text("Xem trước logo chi nhánh", exact=True)).to_have_attribute("src", re.compile("data:image/png;base64,"))
    assert s["call"]("GET", "/tenants/me")["logo_url"] is None
    with page.expect_response(lambda r: r.url.endswith("/tenants/me") and r.request.method == "PATCH") as response:
        page.get_by_role("button", name="Lưu thay đổi", exact=True).click()
    assert response.value.status == 200
    expect(page.get_by_alt_text("Xem trước logo chi nhánh", exact=True)).to_have_attribute("src", re.compile("/api/v1/public/tenants/" + s["slug"] + "/logo"))
    assert s["call"]("GET", "/tenants/me")["logo_url"].startswith("/api/v1/public/tenants/" + s["slug"] + "/logo")
    expect(page.locator("aside img")).to_have_attribute("src", re.compile("/logo"))
    page.set_viewport_size({"width": 320, "height": 844})
    expect(page.locator("header img")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    page.goto(config.frontend_url + "/" + s["slug"])
    expect(page.locator("header img")).to_be_visible()
    expect(page.locator("main img").first).to_be_visible()
    assert page.locator("main img").first.evaluate("el => getComputedStyle(el).objectFit") == "contain"
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    page.locator("header img").dispatch_event("error")
    expect(page.locator("header [role=img]")).to_be_visible()


def test_course_is_limited_by_the_card_with_fewest_available_sessions(scenario):
    s = scenario
    extra = s["call"]("POST", "/services", json={"name": "Three visit course", "price": "600000", "duration_minutes": 30, "is_package": True, "total_sessions": 3})
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/bookings?customer_id=" + s["customer"]["id"])
    modal = page.get_by_role("dialog", name="Tạo lịch hẹn tại quầy", exact=True)
    card = modal.locator("label").filter(has_text="QA One Session").get_by_role("checkbox")
    card.check()
    modal.locator("label").filter(has_text="Three visit course").get_by_role("checkbox").check()
    expect(modal.get_by_role("button", name="Tùy chọn đặt nhiều buổi", exact=True)).to_have_count(0)
    expect(modal.locator("input[type=date]")).to_have_count(1)
    card.uncheck()
    modal.get_by_role("button", name="Tùy chọn đặt nhiều buổi", exact=True).click()
    expect(modal.get_by_role("button", name="⚡ Lên lịch đủ 3 buổi", exact=True)).to_be_visible()
    modal.get_by_role("button", name="⚡ Lên lịch đủ 3 buổi", exact=True).click()
    expect(modal).to_contain_text("600.000")
    expect(modal).not_to_contain_text("1.800.000")
    assert s["call"]("GET", "/bookings") == []
