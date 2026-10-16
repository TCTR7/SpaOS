from common_setup.base_page import BasePage


class AdminLoginPage(BasePage):
    """Page Object for /admin/login."""

    SLUG_INPUT = "#tenantSlug"
    PHONE_INPUT = "#phone"
    PASSWORD_INPUT = "#password"
    SUBMIT_BUTTON = "button[type='submit']"

    def open(self) -> None:
        self.navigate("/admin/login")

    def login(self, tenant_slug: str, phone: str, password: str) -> None:
        self.fill_field(self.SLUG_INPUT, tenant_slug)
        self.fill_field(self.PHONE_INPUT, phone)
        self.fill_field(self.PASSWORD_INPUT, password)
        self.safe_click(self.SUBMIT_BUTTON)
