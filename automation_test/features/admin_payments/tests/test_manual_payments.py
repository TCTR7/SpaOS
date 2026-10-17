from decimal import Decimal

from playwright.sync_api import expect
from common_setup.config import config
from features.admin_payments.pages.payments_page import PaymentsPage


def test_admin_partial_full_and_void_receipt_ui(scenario):
    s = scenario
    page = s["page"](s["admin"], True)
    payments = PaymentsPage(page, config.frontend_url)
    invoice = payments.select_package(s["customer"]["id"], s["package"]["id"])
    assert Decimal(invoice["amount_due"]) == 250000
    payments.receive("100000")
    expect(page.get_by_test_id("invoice-status")).to_have_text("Đã thu một phần")
    payments.receive(method="BANK_TRANSFER")
    expect(page.get_by_test_id("invoice-status")).to_have_text("Đã thu đủ")
    page.locator("summary").filter(has_text="Lịch sử thu tiền và hoàn tác").click()
    page.get_by_test_id("payment-entry").filter(has_text="Tiền mặt").get_by_role("button", name="Hoàn tác ghi nhận", exact=True).click()
    page.locator("#voidReason").fill("Nhập nhầm khoản tiền mặt, đã đối chiếu")
    with page.expect_response(lambda r: r.url.endswith("/void") and r.request.method == "POST") as reversal:
        page.get_by_role("button", name="Xác nhận hoàn tác", exact=True).click()
    assert reversal.value.status == 201
    expect(page.get_by_test_id("invoice-status")).to_have_text("Đã thu một phần")
    expect(page.get_by_test_id("payment-entry")).to_have_count(3)
    expect(page.get_by_test_id("payment-summary")).to_contain_text("150.000")
    page.get_by_role("button", name="Lịch sử thao tác", exact=True).click()
    events = page.get_by_test_id("audit-event").filter(has_text="Hoàn tác ghi nhận")
    expect(events).to_have_count(1)
    page.reload()
    with page.expect_response(lambda r: "/payments/invoices/" + invoice["id"] + "/entries" in r.url) as loaded:
        page.get_by_test_id("collection-" + s["package"]["id"]).get_by_role("button", name="Xác nhận đã thu", exact=True).click()
    assert loaded.value.status == 200
    expect(page.get_by_test_id("payment-entry")).to_have_count(3)


def test_retry_after_lost_response_does_not_duplicate_payment(scenario):
    s = scenario
    page = s["page"](s["admin"], True)
    payments = PaymentsPage(page, config.frontend_url)
    invoice = payments.select_package(s["customer"]["id"], s["package"]["id"])
    calls = []
    path = "**/api/v1/payments/invoices/" + invoice["id"] + "/receipts"
    def lose_first_response(route):
        calls.append(route.request.post_data_json)
        if len(calls) == 1:
            result = route.fetch()
            assert result.status == 201
            route.abort("failed")
        else:
            route.continue_()
    page.route(path, lose_first_response)
    page.get_by_role("checkbox", name="Nhập số tiền khác").check()
    page.locator("#receiptAmount").fill("12345.67")
    page.get_by_role("region", name="Xác nhận thu tiền", exact=True).get_by_role("button", name="Xác nhận đã thu", exact=True).click()
    expect(page.get_by_role("button", name="Thử lại xác nhận", exact=True)).to_be_enabled()
    expect(page.locator("#receiptAmount")).to_be_disabled()
    with page.expect_response(lambda r: r.url.endswith("/receipts")) as result:
        page.get_by_role("button", name="Thử lại xác nhận", exact=True).click()
    assert result.value.status == 201
    assert len(calls) == 2 and calls[0] == calls[1]
    expect(page.get_by_test_id("payment-entry")).to_have_count(1)
    expect(page.get_by_test_id("invoice-paid")).to_contain_text("12.345,67")
    assert Decimal(s["call"]("GET", "/payments/invoices/" + invoice["id"])["amount_paid"]) == Decimal("12345.67")


def test_staff_cannot_open_payment_ui_or_read_audit(scenario, api_helper):
    s = scenario
    token = api_helper.login(s["slug"], s["staff"]["phone_number"], "Staff@123")["access_token"]
    page = s["page"](token, True)
    page.goto(config.frontend_url + "/admin/payments")
    expect(page.get_by_role("alert").filter(has_text="Chỉ Admin")).to_be_visible()
    expect(page.locator("#receiptAmount")).to_have_count(0)
    response = page.request.get(config.api_v1_url + "/payments/invoices", headers={"Authorization": "Bearer " + token})
    assert response.status == 403
    response = page.request.get(config.api_v1_url + "/audit-logs", headers={"Authorization": "Bearer " + token})
    assert response.status == 403


def test_default_full_collection_search_and_paid_filter(scenario):
    s = scenario
    page = s["page"](s["admin"], True)
    payments = PaymentsPage(page, config.frontend_url)
    invoice = payments.select_package(s["customer"]["id"], s["package"]["id"])
    expect(page.locator("#receiptAmount")).to_have_count(0)
    result = payments.receive()
    assert Decimal(result["amount"]) == 250000
    expect(page.get_by_test_id("invoice-status")).to_have_text("Đã thu đủ")
    expect(page.get_by_test_id("collection-" + s["package"]["id"])).to_have_count(0)
    expect(page.get_by_test_id("payment-summary")).to_contain_text("250.000")
    page.get_by_role("button", name="Đóng", exact=True).click()
    page.get_by_label("Lọc trạng thái thu tiền").select_option("all")
    row = page.get_by_test_id("collection-" + s["package"]["id"])
    expect(row).to_contain_text("Đã thu")
    page.get_by_label("Tìm khách thu tiền").fill(s["phone"])
    page.get_by_role("button", name="Tìm khách", exact=True).click()
    expect(row).to_be_visible()
    page.get_by_label("Tìm khách thu tiền").fill("Khách không tồn tại")
    page.get_by_role("button", name="Tìm khách", exact=True).click()
    expect(row).to_have_count(0)
    assert Decimal(s["call"]("GET", "/payments/invoices/" + invoice["id"])["amount_paid"]) == 250000


def test_package_booking_is_shown_without_additional_collection(scenario):
    s = scenario
    booking = s["book"]()
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/payments")
    page.get_by_label("Lọc trạng thái thu tiền").select_option("all")
    row = page.get_by_test_id("collection-" + booking["id"])
    expect(row).to_contain_text("Dùng thẻ — không thu thêm")
    expect(row.get_by_role("button")).to_have_count(0)
    expect(page.get_by_test_id("collection-" + s["package"]["id"])).to_contain_text("250.000")
    assert s["call"]("GET", "/payments/invoices") == []


def test_refresh_failure_after_receipt_requires_reload_not_second_collection(scenario):
    s = scenario
    page = s["page"](s["admin"], True)
    payments = PaymentsPage(page, config.frontend_url)
    invoice = payments.select_package(s["customer"]["id"], s["package"]["id"])
    path = "**/api/v1/payments/collections?*"
    page.route(path, lambda route: route.abort("failed"))
    payments.receive("100000")
    expect(page.get_by_role("button", name="Tải lại số tiền", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Xác nhận đã thu", exact=True).first).to_be_disabled()
    page.unroute(path)
    page.get_by_role("button", name="Tải lại số tiền", exact=True).click()
    expect(page.get_by_test_id("invoice-status")).to_have_text("Đã thu một phần")
    expect(page.get_by_role("button", name="Tải lại số tiền", exact=True)).to_have_count(0)
    assert Decimal(s["call"]("GET", "/payments/invoices/" + invoice["id"])["amount_paid"]) == 100000
