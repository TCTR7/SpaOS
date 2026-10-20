"""Keyboard, small-screen and transaction lifecycle acceptance; no success images."""
from datetime import datetime, timedelta, timezone
import pytest
from playwright.sync_api import expect
from common_setup.config import config
from features.customer_regressions.conftest import scenario


def manual(s, width=390, height=844):
    page = s["page"](s["admin"], True)
    page.set_viewport_size({"width": width, "height": height})
    page.goto(config.frontend_url + "/admin/bookings")
    opener = page.get_by_role("button", name="Tạo lịch hẹn thủ công", exact=True)
    expect(opener).to_be_enabled()
    opener.click()
    modal = page.get_by_role("dialog", name="Tạo lịch hẹn thủ công tại quầy", exact=True)
    expect(modal).to_be_visible()
    return page, modal, opener


@pytest.mark.parametrize("width,height", [(320, 480), (390, 844), (1366, 768)])
def test_manual_header_footer_fit_short_screen(scenario, width, height):
    page, modal, _ = manual(scenario, width, height)
    for control in (modal.get_by_role("button", name="Đóng", exact=True), modal.get_by_role("button", name="Xác nhận tạo lịch", exact=True)):
        bounds = control.bounding_box()
        assert 0 <= bounds["y"] and bounds["y"] + bounds["height"] <= height + 1
    modal.locator("#modalNote").fill("Last field remains reachable")
    expect(modal.locator("#modalNote")).to_be_in_viewport()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")


def test_keyboard_trap_background_and_restore(scenario):
    page, modal, opener = manual(scenario)
    close = modal.get_by_role("button", name="Đóng", exact=True)
    expect(close).to_be_focused()
    page.keyboard.press("Shift+Tab")
    expect(modal.locator("#modalNote")).to_be_focused()
    page.keyboard.press("Tab")
    expect(close).to_be_focused()
    opener.evaluate("e => e.focus()")
    assert modal.evaluate("e => e.contains(document.activeElement)")
    assert page.evaluate("document.body.style.overflow") == "hidden"
    page.keyboard.press("Escape")
    expect(modal).to_have_count(0)
    expect(opener).to_be_focused()
    assert page.evaluate("document.body.style.overflow") != "hidden"


@pytest.mark.parametrize("dismiss", ["escape", "back"])
def test_dirty_manual_retains_fields_until_explicit_discard(scenario, dismiss):
    page, modal, _ = manual(scenario)
    modal.locator("#modalNote").fill("Keep this draft")
    if dismiss == "back":
        page.evaluate("history.back()")
    else:
        page.keyboard.press("Escape")
    prompt = modal.get_by_role("region", name="Bỏ thay đổi đang nhập")
    expect(prompt).to_be_visible()
    prompt.get_by_role("button", name="Tiếp tục chỉnh sửa", exact=True).click()
    expect(modal.locator("#modalNote")).to_have_value("Keep this draft")
    page.keyboard.press("Escape")
    modal.get_by_role("button", name="Bỏ thay đổi", exact=True).click()
    expect(modal).to_have_count(0)
    assert page.url.endswith("/admin/bookings")


def test_backdrop_closes_clean_dialog(scenario):
    page, modal, opener = manual(scenario, 1366, 768)
    modal.click(position={"x": 2, "y": 2})
    expect(modal).to_have_count(0)
    expect(opener).to_be_focused()


def test_reload_does_not_replay_or_claim_to_restore_unsaved_manual_draft(scenario):
    page, modal, _ = manual(scenario)
    writes = []
    page.on("request", lambda request: writes.append(request.url)
            if request.method == "POST" and request.url.endswith("/bookings") else None)
    modal.locator("#modalNote").fill("Unsaved before reload")
    page.reload()
    expect(page.get_by_role("dialog")).to_have_count(0)
    opener = page.get_by_role("button", name="Tạo lịch hẹn thủ công", exact=True)
    expect(opener).to_be_enabled()
    opener.click()
    expect(page.locator("#modalNote")).to_have_value("")
    assert writes == []
    page.evaluate("history.back()")
    expect(page.get_by_role("dialog")).to_have_count(0)
    assert page.url.endswith("/admin/bookings")


def test_dialog_keeps_branch_theme_when_portaled(scenario):
    s = scenario
    s["call"]("PATCH", "/tenants/me", json={"theme_color": "#000080"})
    page = s["page"](s["admin"], True)
    page.route("**/api/v1/branding", lambda route: route.fulfill(json={"theme_color": "#be185d", "configured": False}))
    page.goto(config.frontend_url + "/admin/bookings")
    opener = page.get_by_role("button", name="Tạo lịch hẹn thủ công", exact=True)
    expect(opener).to_be_enabled()
    expect(opener).to_have_css("background-color", "rgb(0, 0, 128)")
    opener.click()
    modal = page.get_by_role("dialog")
    expect(modal.get_by_role("button", name="Xác nhận tạo lịch", exact=True)).to_have_css("background-color", "rgb(0, 0, 128)")


@pytest.mark.parametrize("status", [409, 503])
def test_manual_pending_cannot_dismiss_and_conflict_keeps_fields(scenario, status):
    s = scenario
    page, modal, _ = manual(s)
    modal.locator("label").filter(has_text="QA One Session").get_by_role("checkbox").check()
    day = (datetime.now(timezone(timedelta(hours=7))) + timedelta(days=6)).date().isoformat()
    modal.locator("#modalDate").fill(day)
    modal.locator("button").filter(has_text="KTV rảnh").first.click()
    held = []
    page.route("**/api/v1/bookings/manual-batches", lambda route: held.append(route) if route.request.method == "POST" else route.continue_())
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/bookings/manual-batches")):
        modal.get_by_role("button", name="Xác nhận tạo lịch", exact=True).click()
    page.keyboard.press("Escape")
    expect(modal.get_by_role("status")).to_contain_text("Đang xử lý")
    page.evaluate("history.back()")
    expect(modal).to_be_visible()
    held.pop().fulfill(status=status, json={"detail": "QA slot conflict"})
    expect(modal.get_by_text("QA slot conflict", exact=True)).to_be_visible()
    expect(modal.locator("#modalDate")).to_have_value(day)
    if status == 409:
        expect(modal.locator("label").filter(has_text="QA One Session").get_by_role("checkbox")).to_be_checked()
    else:
        page.keyboard.press("Escape")
        expect(modal).to_be_visible()
        expect(modal.get_by_role("button", name="Xác nhận tạo lịch", exact=True)).to_have_count(0)
        modal.get_by_role("button", name="Kiểm tra kết quả", exact=True).click()
        expect(modal.get_by_text("Chưa có lịch nào được lưu", exact=False)).to_be_visible()
        expect(modal.locator("#modalDate")).to_have_value(day)


def test_completion_requires_confirmation_and_uses_one_session(scenario):
    s = scenario
    booking = s["book"]()
    s["call"]("PATCH", "/bookings/" + booking["id"] + "/status", json={"status": "CONFIRMED"})
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/bookings")
    day = datetime.fromisoformat(booking["start_time"].replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=7))).date().isoformat()
    page.locator("input[type=date]").first.fill(day)
    page.get_by_test_id("booking-card-" + booking["id"]).get_by_role("button", name="Chi tiết lịch hẹn", exact=True).click()
    modal = page.get_by_role("dialog", name="Chi tiết lịch hẹn", exact=True)
    modal.get_by_role("button", name="→ Hoàn thành", exact=True).click()
    expect(modal.get_by_role("region", name="Xác nhận đổi trạng thái")).to_contain_text("QA Customer")
    assert s["call"]("GET", "/customer-packages/me", headers={"Authorization": "Bearer " + s["token"]})[0]["used_sessions"] == 0
    modal.get_by_role("button", name="Giữ trạng thái hiện tại", exact=True).click()
    assert s["call"]("GET", "/bookings/" + booking["id"])["status"] == "CONFIRMED"
    modal.get_by_role("button", name="→ Hoàn thành", exact=True).click()
    with page.expect_response(lambda r: r.request.method == "PATCH" and r.url.endswith("/status")):
        modal.get_by_role("button", name="Xác nhận đổi trạng thái", exact=True).click()
    expect(modal.get_by_text("Hoàn thành", exact=True)).to_be_visible()
    assert s["call"]("GET", "/customer-packages/me", headers={"Authorization": "Bearer " + s["token"]})[0]["used_sessions"] == 1


def test_calendar_status_refresh_restores_scroll_position(scenario):
    s = scenario
    booking = s["book"]()
    zone = timezone(timedelta(hours=7))
    day = datetime.fromisoformat(booking["start_time"].replace("Z", "+00:00")).astimezone(zone).date()
    start = datetime.combine(day, datetime.min.time(), tzinfo=zone)
    # Real bookings, respecting 30-minute service + 15-minute buffer; leave
    # room for the package booking at 10:00. No mocked booking IDs or writes.
    for index in range(31):
        if index in (13, 14):
            continue
        s["call"]("POST", "/bookings", json={"customer_id": s["customer"]["id"],
                  "staff_id": s["staff"]["id"], "start_time": (start + timedelta(minutes=45*index)).isoformat(),
                  "items": [{"service_id": s["service"]["id"]}]})
    s["call"]("PATCH", "/bookings/" + booking["id"] + "/status", json={"status": "CONFIRMED"})
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/bookings")
    page.locator("input[type=date]").first.fill(day.isoformat())
    target = page.get_by_test_id("booking-card-" + booking["id"])
    expect(page.locator('[data-layout-card="booking"]')).to_have_count(30)
    target.scroll_into_view_if_needed()
    before = page.evaluate("scrollY")
    assert before > 500
    with page.expect_response(lambda r: r.request.method == "PATCH" and r.url.endswith("/status")):
        target.get_by_role("button", name="→ Đang thực hiện", exact=True).click()
    expect(target.get_by_text("Đang thực hiện", exact=True)).to_be_visible()
    assert abs(page.evaluate("scrollY") - before) <= 3
    assert s["call"]("GET", "/bookings/" + booking["id"])["status"] == "IN_PROGRESS"
