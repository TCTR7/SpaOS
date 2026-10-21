import uuid
import pytest
from playwright.sync_api import expect
from common_setup.config import config
from features.customer_regressions.tests.test_manual_batch_recovery import prepare
from features.admin_payments.pages.payments_page import PaymentsPage


def branch(s):
    return s["call"]("POST", "/branches", json={"name": "Guard Branch"})["tenant"]["id"]


def open_admin(s, path="settings", page=None):
    page = page or s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/" + path)
    expect(page.locator("#activeBranch")).to_be_visible()
    if path == "settings":
        expect(page.locator("#spaName")).to_have_value("QA Spa")
    return page


def second_tab(s, first):
    return open_admin(s, "dashboard", first.context.new_page())


def blocked(page, target, text):
    before = page.locator("#activeBranch").input_value()
    page.locator("#activeBranch").select_option(target)
    expect(page.get_by_role("alert").filter(has_text=text)).to_be_visible()
    expect(page.locator("#activeBranch")).to_have_value(before)


@pytest.mark.parametrize("target_scope", ["branch", "all"])
def test_dirty_branch_confirmation_cancel_and_discard(scenario, target_scope):
    s = scenario
    target = branch(s) if target_scope == "branch" else "all"
    page = open_admin(s)
    writes = []
    page.on("request", lambda r: writes.append(r.url) if r.method == "PATCH" else None)
    page.locator("#spaName").fill("Unsaved private draft")
    page.locator("#activeBranch").select_option(target)
    modal = page.get_by_role("dialog", name="Bỏ thay đổi chưa lưu?", exact=True)
    expect(modal).to_be_visible()
    modal.get_by_role("button", name="Tiếp tục chỉnh sửa", exact=True).click()
    expect(page.locator("#spaName")).to_have_value("Unsaved private draft")
    page.locator("#activeBranch").select_option(target)
    modal.get_by_role("button", name="Bỏ thay đổi và chuyển", exact=True).click()
    expect(page).to_have_url(config.frontend_url + "/admin/dashboard" + ("?scope=all" if target == "all" else ""))
    if target != "all":
        expect(page.locator("#activeBranch")).to_have_value(target)
    assert not writes


def test_other_tab_dirty_blocks_switch_then_session_clears_old_ui(scenario):
    s = scenario
    target = branch(s)
    first = open_admin(s)
    other = second_tab(s, first)
    first.locator("#spaName").fill("Do not leak this draft")
    # Synchronize with actual browser lock, no sleeps or retrying the switch.
    first.wait_for_function("async()=> (await navigator.locks.query()).held.some(l=>l.name==='spaos-admin-branch-work')")
    blocked(other, target, "Tab khác còn form")
    first.locator("#spaName").fill("QA Spa")
    first.wait_for_function("async()=> !(await navigator.locks.query()).held.some(l=>l.name==='spaos-admin-branch-work')")
    other.locator("#activeBranch").select_option(target)
    expect(other.locator("#activeBranch")).to_have_value(target)
    expect(first.locator("#activeBranch")).to_have_value(target)
    expect(first.locator("#spaName")).to_have_count(0)
    expect(first.get_by_text("Do not leak this draft", exact=True)).to_have_count(0)


def test_other_tab_pending_write_blocks_branch_until_response(scenario):
    s = scenario
    target = branch(s)
    first = open_admin(s)
    other = second_tab(s, first)
    held = []
    def hold(route):
        if route.request.method == "PATCH":
            held.append((route, route.fetch()))
            first.evaluate("window.qaHeldSetting = true")
        else:
            route.continue_()
    first.route("**/api/v1/tenants/me", hold)
    first.locator("#spaName").fill("Saved after response")
    first.get_by_role("button", name="Lưu thay đổi", exact=True).click()
    first.wait_for_function("window.qaHeldSetting === true")
    blocked(other, target, "Tab khác còn form")
    held[0][0].fulfill(response=held[0][1])
    expect(first.locator("#spaName")).to_have_value("Saved after response")
    first.wait_for_function("async()=> !(await navigator.locks.query()).held.some(l=>l.name==='spaos-admin-branch-work')")
    other.locator("#activeBranch").select_option(target)
    expect(other.locator("#activeBranch")).to_have_value(target)


def test_unknown_manual_batch_stays_protected_when_dialog_closed(scenario):
    s = scenario
    target = branch(s)
    first, modal, _ = prepare(s)
    first.route("**/api/v1/bookings/manual-batches", lambda r: r.fulfill(status=503, json={"detail": "QA uncertain batch"}))
    modal.get_by_role("button", name="Xác nhận tạo 3 buổi hẹn", exact=True).click()
    expect(modal.get_by_text("QA uncertain batch", exact=True)).to_be_visible()
    modal.get_by_role("button", name="Kiểm tra sau", exact=True).click()
    expect(modal).to_have_count(0)
    blocked(first, target, "Còn thao tác đang xử lý")
    other = second_tab(s, first)
    blocked(other, target, "Tab khác còn form")
    # Recovery UUID survives navigating away; no customer payload in storage.
    first.goto(config.frontend_url + "/admin/dashboard")
    expect(first.locator("#activeBranch")).to_be_visible()
    blocked(first, target, "Còn thao tác đang xử lý")


def test_switch_in_flight_does_not_replay_other_tab_write(scenario):
    s = scenario
    target = branch(s)
    first = open_admin(s, "dashboard")
    other = open_admin(s, page=first.context.new_page())
    held, writes = [], []
    def hold(route):
        held.append((route, route.fetch()))
        first.evaluate("window.qaHeldSwitch = true")
    first.route("**/api/v1/branches/" + target + "/switch", hold)
    first.locator("#activeBranch").select_option(target)
    first.wait_for_function("window.qaHeldSwitch === true")
    other.on("request", lambda r: writes.append(r.url) if r.method == "PATCH" else None)
    other.locator("#spaName").fill("Never save this into new branch")
    other.get_by_role("button", name="Lưu thay đổi", exact=True).click()
    expect(other.get_by_role("alert").filter(has_text="Đang chuyển chi nhánh ở tab khác")).to_be_visible()
    assert not writes
    held[0][0].fulfill(response=held[0][1])
    expect(other.locator("#activeBranch")).to_have_value(target)
    assert not writes


def test_no_web_locks_fails_closed_for_branch_change(scenario):
    s = scenario
    target = branch(s)
    page = open_admin(s, "dashboard")
    page.evaluate("Object.defineProperty(navigator,'locks',{value:undefined})")
    blocked(page, target, "Trình duyệt chưa hỗ trợ")


def test_unknown_receipt_in_other_tab_must_be_reconciled_before_switch(scenario):
    s = scenario
    target = branch(s)
    page = s["page"](s["admin"], True)
    payments = PaymentsPage(page, config.frontend_url)
    invoice = payments.select_package(s["customer"]["id"], s["package"]["id"])
    other = second_tab(s, page)
    sent = []
    def lose_first(route):
        sent.append(route.request.post_data_json)
        response = route.fetch()
        assert response.status == 201
        if len(sent) == 1:
            route.abort("failed")
        else:
            route.fulfill(response=response)
    page.route("**/api/v1/payments/invoices/" + invoice["id"] + "/receipts", lose_first)
    page.get_by_role("region", name="Xác nhận thu tiền", exact=True).get_by_role("button", name="Xác nhận đã thu", exact=False).click()
    expect(page.get_by_role("button", name="Thử lại xác nhận", exact=True)).to_be_enabled()
    blocked(other, target, "Tab khác còn form")
    page.get_by_role("button", name="Thử lại xác nhận", exact=True).click()
    expect(page.get_by_test_id("invoice-status")).to_have_text("Đã thu đủ")
    assert len(sent) == 2 and sent[0] == sent[1]
    page.get_by_role("dialog").get_by_role("button", name="Đóng", exact=True).click()
    other.locator("#activeBranch").select_option(target)
    expect(other.locator("#activeBranch")).to_have_value(target)


def test_customer_owner_selection_is_a_dirty_branch_draft(scenario):
    s = scenario
    target = branch(s)
    page = open_admin(s, "customers")
    page.get_by_role("button", name="QA Customer SĐT:", exact=False).click()
    owner = page.locator("#customerOwner")
    expect(owner).to_be_visible()
    owner.select_option(s["staff"]["id"])
    page.locator("#activeBranch").select_option(target)
    modal = page.get_by_role("dialog", name="Bỏ thay đổi chưa lưu?", exact=True)
    expect(modal).to_be_visible()
    modal.get_by_role("button", name="Tiếp tục chỉnh sửa", exact=True).click()
    expect(owner).to_have_value(s["staff"]["id"])
    saved = s["call"]("GET", "/customers", params={"q": s["phone"]})
    assert len(saved) == 1 and saved[0]["id"] == s["customer"]["id"]
    assert saved[0]["assigned_staff_id"] is None


def test_pending_push_permission_blocks_branch_in_other_tab(scenario):
    s = scenario
    target = branch(s)
    page = s["page"](s["admin"], True)
    page.add_init_script("Object.defineProperty(Notification,'requestPermission',{value:()=>new Promise(r=>{window.qaResolvePermission=r;})})")
    page.route("**/api/v1/notifications/vapid-public-key", lambda r: r.fulfill(json={"enabled": True, "public_key": "QA-Public-Key"}))
    open_admin(s, "dashboard", page)
    other = second_tab(s, page)
    page.get_by_role("button", name="Thông báo", exact=True).click()
    modal = page.get_by_role("dialog", name="Bảng thông báo", exact=True)
    modal.get_by_role("button", name="Bật thông báo", exact=True).click()
    page.wait_for_function("typeof window.qaResolvePermission === 'function'")
    page.keyboard.press("Escape")
    expect(modal).to_be_visible()
    blocked(other, target, "Tab khác còn form")
    page.evaluate("window.qaResolvePermission('denied')")
    expect(modal.get_by_text("Trình duyệt đã từ chối quyền thông báo.", exact=True)).to_be_visible()
    page.keyboard.press("Escape")
    expect(modal).to_have_count(0)
    other.locator("#activeBranch").select_option(target)
    expect(other.locator("#activeBranch")).to_have_value(target)
