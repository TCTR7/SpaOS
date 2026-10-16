from playwright.sync_api import Page, expect

from common_setup.config import config


def test_report_renders_backend_response_without_runtime_error(admin_page: Page) -> None:
    errors = []
    admin_page.on("pageerror", lambda error: errors.append(str(error)))
    with admin_page.expect_response(lambda response: "/reports/staff-performance?" in response.url and response.request.method == "GET") as pending:
        admin_page.goto(f"{config.frontend_url}/admin/reports", wait_until="domcontentloaded")
    response = pending.value
    assert response.status == 200
    data = response.json()
    expect(admin_page.get_by_text("Đang tổng hợp dữ liệu...")).to_have_count(0)
    expect(admin_page.get_by_role("heading", name="Báo cáo Hiệu suất & Hoa hồng Kỹ thuật viên")).to_be_visible()
    if data["staff"]:
        expect(admin_page.locator("tbody tr")).to_have_count(len(data["staff"]))
    else:
        expect(admin_page.get_by_text("Không có dữ liệu Kỹ thuật viên trong khoảng thời gian này.")).to_be_visible()
    assert not errors, errors
