from playwright.sync_api import expect


class BranchesPage:
    def __init__(self, page, frontend_url):
        self.page, self.frontend_url = page, frontend_url

    def open(self):
        self.page.goto(self.frontend_url + "/admin/branches")

    def create(self, name):
        self.page.locator("#branchName").fill(name)
        with self.page.expect_response(lambda r: r.url.endswith("/branches") and r.request.method == "POST") as response:
            self.page.get_by_role("button", name="Tạo chi nhánh", exact=True).click()
        assert response.value.status == 201, response.value.text()
        branch = response.value.json()["tenant"]
        expect(self.page.locator("#activeBranch option[value='" + branch["id"] + "']")).to_have_count(1)
        return branch

    def grant_staff(self, staff_id, branch_id):
        self.page.locator("#branchStaff").select_option(staff_id)
        self.page.locator("#targetBranch").select_option(branch_id)
        with self.page.expect_response(lambda r: r.url.endswith("/staff-access") and r.request.method == "POST") as response:
            self.page.get_by_role("button", name="Cấp quyền chi nhánh", exact=True).click()
        assert response.value.status == 201, response.value.text()
