from common_setup.base_page import BasePage


class AdminStaffPage(BasePage):
    """Page Object for /admin/staff."""

    NAME_INPUT = "#stName"
    PHONE_INPUT = "#stPhone"
    PWD_INPUT = "#stPwd"
    NOTES_INPUT = "#stNotes"

    def open(self) -> None:
        self.navigate("/admin/staff")
        self.wait_for_text("Nhân viên và lịch làm việc")

    def add_staff(
        self, full_name: str, phone: str, password: str = "Staff@123", notes: str = ""
    ) -> None:
        self.click_by_text("Thêm Kỹ thuật viên mới")
        self.fill_field(self.NAME_INPUT, full_name)
        self.fill_field(self.PHONE_INPUT, phone)
        self.fill_field(self.PWD_INPUT, password)
        if notes:
            self.fill_field(self.NOTES_INPUT, notes)
        self.click_by_text("Lưu Kỹ thuật viên")

    def save_week_schedule(self) -> None:
        self.click_by_text("Lưu phân công tuần")
