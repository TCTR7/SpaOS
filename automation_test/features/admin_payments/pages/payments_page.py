from playwright.sync_api import expect


class PaymentsPage:
    def __init__(self, page, frontend_url):
        self.page = page
        self.frontend_url = frontend_url

    def select_package(self, customer_id, package_id):
        self.page.goto(self.frontend_url + "/admin/payments")
        row = self.page.get_by_test_id("collection-" + package_id)
        expect(row).to_be_visible()
        expect(row).to_contain_text("Chưa thu")
        with self.page.expect_response(lambda r: r.url.endswith("/payments/invoices") and r.request.method == "POST") as result:
            row.get_by_role("button", name="Xác nhận đã thu", exact=True).click()
        assert result.value.status == 201, result.value.text()
        expect(self.page.get_by_test_id("invoice-status")).to_be_visible()
        return result.value.json()

    def receive(self, amount=None, method="CASH"):
        if amount is not None:
            self.page.get_by_role("checkbox", name="Nhập số tiền khác").check()
            self.page.locator("#receiptAmount").fill(amount)
        self.page.locator("#receiptMethod").select_option(method)
        with self.page.expect_response(lambda r: r.url.endswith("/receipts") and r.request.method == "POST") as result:
            self.page.get_by_role("region", name="Xác nhận thu tiền", exact=True).get_by_role("button", name="Xác nhận đã thu", exact=False).click()
        assert result.value.status == 201, result.value.text()
        expect(self.page.get_by_role("status").filter(has_text="Đã ghi nhận")).to_be_visible()
        return result.value.json()
