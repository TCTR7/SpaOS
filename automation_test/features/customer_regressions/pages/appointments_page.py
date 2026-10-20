class CustomerAppointmentsPage:
    def __init__(self, page, tenant_url):
        self.page = page
        self.tenant_url = tenant_url

    def open(self):
        self.page.goto(self.tenant_url + "/appointments")

    def choose_new_date(self, day):
        self.page.get_by_role("button", name="Đổi ngày/giờ", exact=True).click()
        with self.page.expect_response(
            lambda r: "/available-slots?" in r.url and "date=" + day in r.url
        ) as pending:
            self.page.locator("#rescheduleDate").fill(day)
        response = pending.value
        assert response.status == 200, response.text()
        self.page.get_by_role("dialog").locator("button:has-text('KTV trống')").first.click()
        return response.json()["slots"][0]["start_time"]

    def confirm(self, booking_id):
        with self.page.expect_response(
            lambda r: r.url.endswith("/bookings/" + booking_id) and r.request.method == "PATCH"
        ) as pending:
            self.page.get_by_role("dialog").get_by_role("button", name="Xác nhận đổi lịch", exact=True).click()
        return pending.value
