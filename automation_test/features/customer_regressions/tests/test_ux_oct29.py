"""PO regressions: real isolated HTTP plus mobile browser evidence."""
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from playwright.sync_api import expect
from common_setup.config import config
from common_setup.api_helper import random_phone
from features.client_pwa_booking.pages.booking_wizard_page import BookingWizardPage
from features.customer_regressions.tests.test_manual_batch_recovery import prepare
from features.customer_regressions.tests.test_branch_work_guard import branch, open_admin, second_tab, blocked
from features.ui_quality.tests.test_dialog_workflows import manual

ARTIFACTS = Path(__file__).resolve().parents[4] / "artifacts" / "ux_oct29"

def screenshot(page,name):
    ARTIFACTS.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(ARTIFACTS/(name+"_"+uuid.uuid4().hex[:6]+".png")),full_page=True)

def test_mobile_service_delete_requires_confirmation_and_compact_layout(scenario):
    s=scenario
    page=s["page"](s["admin"],True)
    page.goto(config.frontend_url+"/admin/services")
    row=page.locator("tbody tr").filter(has_text="QA Treatment")
    expect(row).to_be_visible()
    duration=row.get_by_text("Thời lượng",exact=True).bounding_box()
    price=row.get_by_text("Đơn giá",exact=True).bounding_box()
    assert abs(duration["y"]-price["y"])<2
    deletes=[]
    page.on("request",lambda r:deletes.append(r.url) if r.method=="DELETE" else None)
    row.get_by_role("button",name="Xóa / Ngưng dịch vụ",exact=True).click()
    dialog=page.get_by_role("dialog",name="Xóa hoặc ngưng dịch vụ?",exact=True)
    expect(dialog).to_be_visible();assert not deletes
    dialog.get_by_role("button",name="Giữ dịch vụ",exact=True).click()
    expect(row).to_be_visible();assert not deletes
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
    screenshot(page,"services_mobile")

def test_definitive_phone_conflict_keeps_manual_form_editable(scenario):
    s=scenario
    page,modal,_=prepare(s)
    modal.get_by_placeholder("Số điện thoại (9-15 số) *",exact=True).fill(s["phone"])
    modal.get_by_role("button",name="Xác nhận tạo 3 buổi hẹn",exact=True).click()
    expect(modal.get_by_text("Khách đã có hồ sơ tại chi nhánh.",exact=False)).to_be_visible()
    modal.get_by_placeholder("Số điện thoại (9-15 số) *",exact=True).fill(random_phone())
    modal.locator("#modalNote").fill("Can edit after a definitive failure")
    expect(modal.get_by_role("button",name="Xác nhận tạo 3 buổi hẹn",exact=True)).to_be_enabled()
    expect(modal.get_by_role("button",name="Kiểm tra kết quả",exact=True)).to_have_count(0)

def test_deferred_request_allows_new_booking_and_restores_after_reload(scenario):
    s=scenario
    page,modal,phone=prepare(s)
    page.route("**/api/v1/bookings/manual-batches",lambda r:r.fulfill(status=503,json={"detail":"QA uncertain"}))
    modal.get_by_role("button",name="Xác nhận tạo 3 buổi hẹn",exact=True).click()
    expect(modal.get_by_role("button",name="Kiểm tra sau",exact=True)).to_be_visible()
    modal.get_by_role("button",name="Kiểm tra sau",exact=True).click()
    expect(modal).to_have_count(0)
    page.get_by_role("button",name="Tạo lịch hẹn",exact=True).click()
    expect(modal.get_by_placeholder("Số điện thoại (9-15 số) *",exact=True)).to_have_count(0)
    modal.get_by_role("button",name="Đóng",exact=True).click()
    page.reload()
    expect(page.get_by_text("Yêu cầu cần đối chiếu (1)",exact=True)).to_be_visible()
    page.get_by_role("button",name="Mở lại và kiểm tra",exact=True).click()
    expect(modal.get_by_placeholder("Số điện thoại (9-15 số) *",exact=True)).to_have_value(phone)
    modal.get_by_role("button",name="Kiểm tra kết quả",exact=True).click()
    expect(modal.get_by_text("Chưa có lịch nào được lưu.",exact=False)).to_be_visible()
    modal.locator("#modalNote").fill("Recovered complete draft")

def test_expired_manual_draft_does_not_reuse_another_customer_form(scenario):
    s=scenario
    page,modal,_=prepare(s)
    modal.locator("#modalNote").fill("Private draft from another request")
    modal.get_by_role("button",name="Đóng",exact=True).click()
    modal.get_by_role("button",name="Bỏ thay đổi",exact=True).click()
    page.evaluate("""() => {
      const entry=Object.entries(sessionStorage).find(([k])=>k.startsWith('spaos_manual_batch_')&&k.endsWith(':queue'));
      if (!entry) throw new Error('Missing scoped recovery queue');
      sessionStorage.setItem(entry[0],JSON.stringify([{id:crypto.randomUUID(),at:Date.now()-9*3600000}]));
    }""")
    page.reload()
    # Enter a separate draft first, then close it while keeping its in-memory state.
    page.get_by_role("button",name="Tạo lịch hẹn",exact=True).click()
    modal.locator("#modalNote").fill("Do not restore this for an expired request")
    modal.get_by_role("button",name="Đóng",exact=True).click()
    modal.get_by_role("button",name="Bỏ thay đổi",exact=True).click()
    page.get_by_role("button",name="Mở lại và kiểm tra",exact=True).click()
    modal.get_by_role("button",name="Kiểm tra kết quả",exact=True).click()
    expect(modal.get_by_text("Chưa có lịch nào được lưu.",exact=False)).to_be_visible()
    expect(modal.locator("#modalNote")).to_have_value("")
    expect(modal.get_by_role("button",name="Xác nhận tạo lịch",exact=True)).to_be_disabled()

def test_empty_payment_pagination_and_return_to_same_customer(scenario):
    s=scenario
    page=s["page"](s["admin"],True)
    page.goto(config.frontend_url+"/admin/customers?customer_id="+s["customer"]["id"])
    page.get_by_role("link",name="Xem khoản cần thu",exact=True).click()
    page.get_by_role("link",name="← Về hồ sơ khách hàng",exact=True).click()
    expect(page.get_by_role("link",name="Xem khoản cần thu",exact=True)).to_be_visible()
    page.goto(config.frontend_url+"/admin/payments")
    page.get_by_label("Tìm khách thu tiền",exact=True).fill("no-matching-customer-"+uuid.uuid4().hex)
    page.get_by_role("button",name="Tìm khách",exact=True).click()
    expect(page.get_by_role("button",name="Trang trước",exact=True)).to_have_count(0)
    expect(page.get_by_role("button",name="Trang sau",exact=True)).to_have_count(0)

def test_guest_can_request_without_account_and_spa_confirms(scenario):
    s=scenario
    page=s["page"]("",False)
    wizard=BookingWizardPage(page);wizard.open_wizard(s["slug"])
    wizard.step1_select_service_by_name("QA Treatment")
    day=(datetime.now(timezone(timedelta(hours=7))).date()+timedelta(days=9)).isoformat()
    wizard.step2_select_date_and_first_slot(day)
    page.locator("#guest-name").fill("Khách mới không mật khẩu")
    phone=random_phone();page.locator("#guest-phone").fill(phone)
    page.get_by_role("button",name="Gửi yêu cầu chờ spa xác nhận",exact=True).click()
    page.wait_for_url("**/request**")
    expect(page.get_by_text("Chờ spa gọi xác nhận",exact=True)).to_be_visible()
    assert not page.evaluate("location.hash")
    assert s["call"]("GET","/customers",params={"q":phone})==[]
    admin=s["page"](s["admin"],True);admin.goto(config.frontend_url+"/admin/bookings")
    admin.get_by_text("Khách chờ liên hệ xác nhận (1)",exact=True).click()
    admin.get_by_role("button",name="Gọi và xử lý",exact=True).click()
    dialog=admin.get_by_role("dialog",name="Liên hệ xác nhận yêu cầu",exact=True)
    expect(dialog.get_by_role("button",name="Xác nhận và tạo lịch",exact=True)).to_be_disabled()
    dialog.get_by_role("checkbox").check()
    dialog.get_by_role("button",name="Xác nhận và tạo lịch",exact=True).click()
    expect(dialog).to_have_count(0)
    page.get_by_role("button",name="Cập nhật trạng thái",exact=True).click()
    expect(page.get_by_text("Đã được spa xác nhận",exact=True)).to_be_visible()
    expect(page.get_by_text("Spa đã xác nhận lịch hẹn.",exact=True)).to_be_visible()
    screenshot(page,"guest_request_confirmed")
    customer=s["call"]("GET","/customers",params={"q":phone})[0]
    booking=s["call"]("GET","/bookings",params={"customer_id":customer["id"]})[0]
    assert booking["status"]=="CONFIRMED"
    s["call"]("PATCH","/bookings/"+booking["id"]+"/status",json={"status":"CANCELLED"})
    page.get_by_role("button",name="Cập nhật trạng thái",exact=True).click()
    expect(page.get_by_text("Lịch hẹn đã hủy",exact=True)).to_be_visible()
    # The same tab can submit a later request without being redirected to the old one.
    wizard.open_wizard(s["slug"])
    wizard.step1_select_service_by_name("QA Treatment")
    wizard.step2_select_date_and_first_slot(day)
    expect(page.get_by_role("button",name="Kiểm tra yêu cầu đã gửi",exact=True)).to_have_count(0)
    page.locator("#guest-name").fill("Lần đặt tiếp theo")
    page.locator("#guest-phone").fill(phone)
    page.get_by_role("button",name="Gửi yêu cầu chờ spa xác nhận",exact=True).click()
    page.wait_for_url("**/request**")
    expect(page.get_by_text("Chờ spa gọi xác nhận",exact=True)).to_be_visible()
    assert len(s["call"]("GET","/guest-requests")["items"])==1


def test_guides_cover_screens_and_can_restart_tour(scenario):
    s=scenario;page=s["page"](s["admin"],True)
    page.goto(config.frontend_url+"/admin/help")
    expect(page.get_by_role("button",name="Bắt đầu lại hướng dẫn qua các màn hình",exact=True)).to_be_visible()
    assert page.locator("details").count()>=12
    page.get_by_role("button",name="Bắt đầu lại hướng dẫn qua các màn hình",exact=True).click()
    dialog=page.get_by_role("dialog",name="Hướng dẫn: Tổng quan",exact=True)
    expect(dialog).to_be_visible()
    dialog.get_by_role("button",name="Đến màn hình tiếp theo",exact=True).click()
    expect(page.get_by_role("dialog",name="Hướng dẫn: Quản lý chi nhánh",exact=True)).to_be_visible()
    screenshot(page,"screen_tour")

def test_cross_tab_blocker_identifies_screen_and_keeps_draft(scenario):
    s=scenario;target=branch(s)
    first=open_admin(s);other=second_tab(s,first)
    first.locator("#spaName").fill("Draft retained in original tab")
    first.wait_for_function("async()=> (await navigator.locks.query()).held.some(l=>l.name==='spaos-admin-branch-work')")
    blocked(other,target,"Tab khác còn form")
    expect(other.get_by_role("button",name="Đến công việc đang dở",exact=True)).to_be_visible()
    other.get_by_role("button",name="Đến công việc đang dở",exact=True).click()
    expect(first.locator("#spaName")).to_have_value("Draft retained in original tab")

@pytest.mark.parametrize("matches",[True,False])
def test_saved_staff_skills_group_and_busy_staff_is_hidden(scenario,matches):
    s=scenario
    extra=s["call"]("POST","/services",json={"name":"Other skill","price":100000,"duration_minutes":30})
    skill=s["service"]["id"] if matches else extra["id"]
    s["call"]("PUT","/staff/"+s["staff"]["id"]+"/skills",json={"service_ids":[skill]})
    page,modal,_=manual(s)
    modal.locator("label").filter(has_text="QA Treatment").get_by_role("checkbox").check()
    select=modal.locator("#modalStaff")
    expect(select).to_be_enabled()
    label="Có đủ kỹ năng phù hợp" if matches else "Nhân viên khác — chưa đủ kỹ năng"
    expect(select.locator("optgroup[label='"+label+"'] option")).to_have_count(1)
    expect(select.locator("optgroup[label='Chưa khai báo kỹ năng']")).to_have_count(0)
    # Fill the whole assigned day with a single time-off override, then refresh suggestions.
    day=(datetime.now(timezone(timedelta(hours=7))).date()+timedelta(days=11)).isoformat()
    s["call"]("PUT","/staff/"+s["staff"]["id"]+"/date-overrides",json={"day":day,"is_day_off":True})
    modal.locator("input[type=date]").fill(day)
    expect(select.locator("option")).to_have_count(1)  # only Spa tự sắp xếp remains

def test_grant_staff_then_switch_to_new_branch_setup(scenario):
    s=scenario;page=s["page"](s["admin"],True)
    page.goto(config.frontend_url+"/admin/branches")
    page.locator("#branchName").fill("Chi nhánh mới QA")
    page.get_by_role("button",name="Tạo chi nhánh",exact=True).click()
    setup=page.get_by_role("button",name="Chuyển sang thiết lập chi nhánh mới",exact=True)
    expect(setup).to_be_visible()
    page.locator("#branchStaff").select_option(s["staff"]["id"])
    target=page.locator("#targetBranch option").nth(1).get_attribute("value")
    page.locator("#targetBranch").select_option(target)
    page.get_by_role("button",name="Thêm vào chi nhánh",exact=True).click()
    expect(page.get_by_role("status").filter(has_text="Đã thêm nhân viên")).to_be_visible()
    expect(setup).to_be_enabled();setup.click()
    expect(page.locator("#activeBranch")).to_have_value(target)

def test_push_configuration_message_names_server_setup(scenario):
    page=scenario["page"](scenario["admin"],True)
    page.goto(config.frontend_url+"/admin/dashboard")
    page.get_by_role("button",name="Thông báo",exact=True).click()
    dialog=page.get_by_role("dialog",name="Bảng thông báo",exact=True)
    dialog.get_by_role("button",name="Bật thông báo",exact=True).click()
    expect(dialog.get_by_text("Spa chưa bật dịch vụ thông báo thiết bị.",exact=False)).to_be_visible()
