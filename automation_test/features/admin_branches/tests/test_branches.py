import uuid
from playwright.sync_api import expect
from common_setup.config import config
from features.admin_branches.pages.branches_page import BranchesPage

def test_owner_creates_switches_and_sees_combined_dashboard(scenario):
    s = scenario
    invoice = s["call"]("POST", "/payments/invoices", json={"customer_package_id": s["package"]["id"]})
    s["call"]("POST", "/payments/invoices/" + invoice["id"] + "/receipts", json={
        "amount": "100000", "method": "CASH", "idempotency_key": str(uuid.uuid4())})
    page = s["page"](s["admin"], True)
    branches = BranchesPage(page, config.frontend_url)
    branches.open()
    branch = branches.create("QA Chi nhánh mới")
    page.locator("#activeBranch").select_option(branch["id"])
    expect(page).to_have_url(config.frontend_url + "/admin/dashboard")
    expect(page.locator("#activeBranch")).to_have_value(branch["id"])
    expect(page.get_by_role("heading", name="Tổng quan QA Chi nhánh mới")).to_be_visible()
    page.goto(config.frontend_url + "/admin/customers")
    expect(page.get_by_text("QA Customer", exact=True)).to_have_count(0)
    page.locator("#activeBranch").select_option("all")
    expect(page.get_by_role("heading", name="Tổng quan tất cả chi nhánh", exact=True)).to_be_visible()
    expect(page.get_by_test_id("branch-dashboard")).to_contain_text("100.000")
    expect(page.get_by_test_id("branch-dashboard")).to_contain_text("150.000")
    expect(page.get_by_test_id("dashboard-" + branch["id"])).to_be_visible()
    assert not s["errors"]

def test_owner_grants_staff_and_staff_logs_in_without_slug(scenario):
    s = scenario
    branch = s["call"]("POST", "/branches", json={"name": "QA Chi nhánh nhân viên"})["tenant"]
    page = s["page"](s["admin"], True)
    branches = BranchesPage(page, config.frontend_url)
    branches.open()
    branches.grant_staff(s["staff"]["id"], branch["id"])
    staff_page = s["page"]("", True)
    staff_page.goto(config.frontend_url + "/admin/login")
    expect(staff_page.locator("#tenantSlug")).to_have_count(0)
    staff_page.locator("#phone").fill(s["staff"]["phone_number"])
    staff_page.locator("#password").fill("Staff@123")
    with staff_page.expect_response(lambda r: r.url.endswith("/auth/login")) as login:
        staff_page.get_by_role("button", name="Đăng nhập").click()
    assert login.value.status == 200
    expect(staff_page).to_have_url(config.frontend_url + "/admin/bookings")
    expect(staff_page.locator("#activeBranch option")).to_have_count(2)
    expect(staff_page.locator("#activeBranch option[value='all']")).to_have_count(0)
    staff_page.locator("#activeBranch").select_option(branch["id"])
    expect(staff_page.locator("#activeBranch")).to_have_value(branch["id"])
    staff_page.goto(config.frontend_url + "/admin/branches")
    expect(staff_page.get_by_role("alert").filter(has_text="Chỉ chủ hệ thống")).to_be_visible()

def test_public_home_selects_branch_by_name_and_preserves_customer_route(scenario):
    s = scenario
    page = s["page"]("", True)
    page.goto(config.frontend_url + "/")
    choice = page.locator('a[href="/' + s["slug"] + '"]')
    expect(choice).to_be_visible()
    choice.click()
    expect(page).to_have_url(s["url"])
    expect(page.get_by_text("QA Treatment", exact=True)).to_be_visible()
