from common_setup.config import config
from common_setup.api_helper import random_phone
from playwright.sync_api import expect

class OperatorPage:
    def __init__(self, page):
        self.page = page

    def login(self):
        self.page.goto(config.frontend_url + "/operator/login")
        self.page.locator("#operatorPhone").fill("0998888777")
        self.page.locator("#operatorPassword").fill("OperatorOnlyForQa@2026")
        self.page.get_by_role("button", name="Đăng nhập quản trị", exact=True).click()
        self.page.wait_for_url(config.frontend_url + "/operator")
        expect(self.page.locator("#ownerName")).to_be_visible(timeout=15000)

    def fill_owner(self):
        phone = random_phone()
        self.page.locator("#ownerName").fill("Trần Cao Trung")
        self.page.locator("#ownerPhone").fill(phone)
        self.page.locator("#firstBranch").fill("Chi nhánh Đà Nẵng")
        self.page.locator("#ownerPassword").fill("OwnerQa@123")
        self.page.locator("#ownerConfirm").fill("OwnerQa@123")
        return phone

    def submit(self):
        self.page.get_by_role("button", name="Tạo tài khoản chủ spa", exact=True).click()
