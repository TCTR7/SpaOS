from playwright.sync_api import Page

from common_setup.api_helper import random_phone, unique_suffix
from features.admin_catalog.pages.staff_page import AdminStaffPage


def test_admin_create_staff_and_save_7day_schedules(admin_page: Page) -> None:
    staff_page = AdminStaffPage(admin_page)
    staff_page.open()

    staff_name = f"KTV E2E {unique_suffix()}"
    phone = random_phone("097")
    staff_page.add_staff(staff_name, phone, notes="KTV kiểm thử E2E")
    staff_page.wait_for_text(staff_name)

    staff_page.save_week_schedule()
    staff_page.wait_for_text(f"Đã lưu lịch làm việc 7 ngày trong tuần cho KTV {staff_name}")
