from common_setup.base_page import BasePage


class AdminLoginPage(BasePage):
    """Page Object for /admin/login."""

    PHONE_INPUT = "#phone"
    PASSWORD_INPUT = "#password"
    SUBMIT_BUTTON = "button[type='submit']"

    def open(self) -> None:
        self.navigate("/admin/login")

    def login(self, tenant_slug: str, phone: str, password: str) -> None:
        self.fill_field(self.PHONE_INPUT, phone)
        self.fill_field(self.PASSWORD_INPUT, password)
        with self.page.expect_response(
            lambda response: response.url.endswith("/api/v1/auth/login")
            and response.request.method == "POST"
        ) as pending:
            self.safe_click(self.SUBMIT_BUTTON)
        self.last_login_status = pending.value.status
