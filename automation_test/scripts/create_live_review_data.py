"""Opt-in persistent review data on the local app; independent of isolated QA tests.

Creates new accounts through public business APIs, then verifies real UI logins.
Never resets credentials, deletes business rows, or touches QA harness guards.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys
import traceback
import uuid
from datetime import datetime, date, time, timedelta, timezone
from urllib.parse import urlsplit

import httpx
from dotenv import dotenv_values
from playwright.sync_api import sync_playwright, expect

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
TZ = timezone(timedelta(hours=7), "Asia/Ho_Chi_Minh")


class ProvisionError(Exception):
    pass


def check(condition, message):
    if not condition:
        raise ProvisionError(message)


def local_url(value):
    parsed = urlsplit(value)
    check(parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}
          and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment,
          "This command only targets explicitly selected local HTTP applications.")
    return value.rstrip("/")


def make_manifest(frontend, api, staff_count):
    tag = uuid.uuid4().hex[:8]
    phones = set()
    def account(name):
        while True:
            phone = "099" + "".join(str(secrets.randbelow(10)) for _ in range(7))
            if phone not in phones:
                phones.add(phone)
                return dict(full_name=name, phone_number=phone, password="Spa!" + secrets.token_urlsafe(12))
    locations = ["Quận 1", "Quận 3", "Thủ Đức"]
    staff_names = ["Nguyễn Mai Anh", "Trần Thu Hà", "Lê Ngọc Lan", "Phạm Thanh Thảo", "Hoàng Bảo Ngọc",
                   "Đặng Minh Châu", "Bùi Khánh Linh", "Võ Thùy Dương", "Đỗ Diệu Hương", "Phan Tú Uyên"]
    customers = ["Nguyễn Hoài An", "Trần Minh Tâm", "Lê Thanh Trúc", "Phạm Thảo Vy", "Hoàng Gia Hân",
                 "Đặng Ngọc Ánh", "Bùi Hà My", "Võ Phương Nhi", "Đỗ Quỳnh Chi", "Phan Hồng Nhung"]
    today = datetime.now(TZ).date()
    branches = []
    for n, location in enumerate(locations):
        branch = dict(name=f"An Nhiên Spa - {location} [{tag}]", staff=[], customers=[], services=[], bookings=[])
        for i in range(staff_count):
            branch["staff"].append(account(staff_names[i]))
        branch["customers"] = [account(name) for name in customers]
        branch["services"] = [
            dict(name="Massage thư giãn", duration_minutes=60, price="350000", is_package=False, total_sessions=1),
            dict(name="Chăm sóc da cơ bản", duration_minutes=45, price="450000", is_package=False, total_sessions=1),
            dict(name="Liệu trình chăm sóc da 5 buổi", duration_minutes=60, price="1800000", is_package=True, total_sessions=5)]
        for i in range(10):
            day = today - timedelta(days=1) if i < 2 else today + timedelta(days=1 + (i % 3))
            hour = 9 if i < 2 else 10 + (i % 5)
            branch["bookings"].append(dict(request_id=str(uuid.uuid4()), customer_index=i,
                staff_index=i % staff_count, service_index=2 if i == 1 else i % 2,
                start_time=datetime.combine(day, time(hour, 0), tzinfo=TZ).isoformat(),
                target_status="COMPLETED" if i < 2 else "CONFIRMED" if i < 4 else "CANCELLED" if i == 9 else "PENDING",
                created_by="customer" if i == 2 else "staff" if i == 3 else "owner"))
        branches.append(branch)
    return dict(schema_version=1, dataset_id=tag, purpose="Dữ liệu trải nghiệm được giữ lại trên ứng dụng local",
        created_at=datetime.now(TZ).isoformat(), frontend_url=frontend, api_url=api,
        admin_login_url=frontend + "/admin/login", owner_request_id=str(uuid.uuid4()),
        owner=account("Nguyễn Minh Anh - Chủ An Nhiên Spa"), branches=branches,
        instructions=["Chủ spa và nhân viên đăng nhập tại admin_login_url bằng SĐT và mật khẩu.",
                      "Chủ spa dùng dropdown để chuyển giữa ba chi nhánh.",
                      "Khách đăng nhập tại customer_login_url của chi nhánh tương ứng.",
                      "Dữ liệu là hồ sơ trải nghiệm hư cấu được lưu thật trong database local; không tự xóa sau test.",
                      "Không lưu hoặc chia sẻ file chứa mật khẩu này lên Git."],
        verification=dict(status="planned"))


class Runner:
    def __init__(self, manifest, path):
        self.data, self.path = manifest, path
        self.client = httpx.Client(base_url=manifest["api_url"], timeout=30, follow_redirects=False)
        self.checks = 0
        self.ui_checks = 0
        self.phase = "preflight"
    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, self.path)
    def call(self, method, path, token=None, *, expected=200, headers=None, **kwargs):
        request_headers = dict(headers or {})
        if token:
            request_headers["Authorization"] = "Bearer " + token
        r = self.client.request(method, path, headers=request_headers, **kwargs)
        check(r.status_code == expected, f"{method} {path}: expected {expected}, got {r.status_code}; stopped without resetting existing data.")
        self.checks += 1
        return r.json()
    def login(self, user, slug=None):
        return self.call("POST", "/auth/login", headers={"X-Tenant-Slug": slug} if slug else {},
            json={"phone_number": user["phone_number"], "password": user["password"]})
    def switch(self, owner_token, branch):
        return self.call("POST", "/branches/" + branch["id"] + "/switch", owner_token)["access_token"]
    def preflight(self):
        with httpx.Client(timeout=30) as client:
            r = client.get(self.data["frontend_url"] + "/admin/login")
            check(r.status_code == 200, "Existing local frontend is not available; no server was started/stopped.")
        r = self.client.get("/branches/public")
        check(r.status_code == 200, "Local API is not available.")
    def provision(self, operator):
        self.data["verification"] = dict(status="provisioning")
        self.save()
        auth = self.call("POST", "/operator/login", json={"phone_number": operator["OPERATOR_PHONE"], "password": operator["OPERATOR_PASSWORD"]})
        owner = self.data["owner"]
        first = self.data["branches"][0]
        provision = self.call("POST", "/operator/owners", auth["access_token"], expected=201,
            json={"request_id": self.data["owner_request_id"], "branch_name": first["name"],
                  "owner_full_name": owner["full_name"], "phone_number": owner["phone_number"], "password": owner["password"]})
        check(not first.get("id") or first["id"] == provision["tenant_id"], "Owner provision did not match saved manifest.")
        first["id"] = provision["tenant_id"]
        owner["first_branch_user_id"] = provision["owner_user_id"]
        self.save()
        owner_auth = self.login(owner)
        token = owner_auth["access_token"]
        for branch in self.data["branches"]:
            available = self.call("GET", "/branches", token)
            matches = [b for b in available if b["tenant"]["name"] == branch["name"]]
            check(len(matches) <= 1, "Ambiguous branch name; refusing to merge branches.")
            found = matches[0] if matches else self.call("POST", "/branches", token, expected=201, json={"name": branch["name"]})
            check(not branch.get("id") or branch["id"] == found["tenant"]["id"], "Saved branch identity changed.")
            branch.update(id=found["tenant"]["id"], slug=found["tenant"]["slug"])
            branch["customer_login_url"] = self.data["frontend_url"] + "/" + branch["slug"] + "/login"
            self.save()
            scoped = self.switch(token, branch)
            self.call("PATCH", "/tenants/me", scoped, json={"open_time": "08:00:00", "close_time": "20:00:00", "buffer_minutes": 10})
            existing = self.call("GET", "/staff", scoped)
            for staff in branch["staff"]:
                found = next((s for s in existing if s["phone_number"] == staff["phone_number"]), None)
                if not found:
                    found = self.call("POST", "/staff", scoped, expected=201,
                        json={k: staff[k] for k in ("full_name", "phone_number", "password")})
                check(found["full_name"] == staff["full_name"], "Staff identity mismatch; credentials were not reset.")
                staff["id"] = found["id"]
                self.save()
                self.call("PUT", "/staff/" + staff["id"] + "/schedules", scoped,
                    json={"schedules": [{"day_of_week": d, "start_time": "08:00:00", "end_time": "20:00:00"} for d in range(7)]})
            existing = self.call("GET", "/services", scoped)
            for service in branch["services"]:
                found = next((s for s in existing if s["name"] == service["name"]), None)
                if not found:
                    found = self.call("POST", "/services", scoped, expected=201,
                        json={k: v for k, v in service.items() if k != "id"})
                service["id"] = found["id"]
                self.save()
            for i, customer in enumerate(branch["customers"]):
                rows = self.call("GET", "/customers", scoped, params={"q": customer["phone_number"]})
                found = next((c for c in rows if c["phone_number"] == customer["phone_number"]), None)
                if not found:
                    found = self.call("POST", "/customers", scoped, expected=201,
                        json={**{k: customer[k] for k in ("full_name", "phone_number", "password")},
                              "notes": "Hồ sơ trải nghiệm " + self.data["dataset_id"]})
                check(found["full_name"] == customer["full_name"], "Customer identity mismatch.")
                customer["id"] = found["id"]
                self.save()
                sid = branch["staff"][i % len(branch["staff"])]["id"]
                self.call("PATCH", "/customers/" + customer["id"] + "/assignment", scoped, json={"assigned_staff_id": sid})
                rows = self.call("GET", "/customers/" + customer["id"] + "/packages", scoped)
                found = next((p for p in rows if p["service_id"] == branch["services"][2]["id"]), None)
                if not found:
                    found = self.call("POST", "/customer-packages", scoped, expected=201,
                        json={"customer_id": customer["id"], "service_id": branch["services"][2]["id"]})
                customer["package_id"] = found["id"]
                self.save()
            for entry in branch["bookings"]:
                customer = branch["customers"][entry["customer_index"]]
                staff = branch["staff"][entry["staff_index"]]
                line = {"service_id": branch["services"][entry["service_index"]]["id"]}
                if entry["service_index"] == 2:
                    line["customer_package_id"] = customer["package_id"]
                marker = "Trải nghiệm " + self.data["dataset_id"] + " / " + entry["request_id"]
                rows = self.call("GET", "/bookings", scoped, params={"customer_id": customer["id"], "limit": 200})
                found = next((r for r in rows if r["note"] == marker), None)
                if not found:
                    if entry["created_by"] == "customer":
                        customer_auth = self.login(customer, branch["slug"])
                        found = self.call("POST", "/bookings", customer_auth["access_token"], expected=201,
                            json={"start_time": entry["start_time"], "staff_id": staff["id"], "items": [line], "note": marker})
                    else:
                        actor = self.login(staff)["access_token"] if entry["created_by"] == "staff" else scoped
                        result = self.call("POST", "/bookings/manual-batches", actor, expected=201,
                            json={"request_id": entry["request_id"], "customer_id": customer["id"], "staff_id": staff["id"],
                                  "start_times": [entry["start_time"]], "items": [line], "note": marker})
                        found = self.call("GET", "/bookings/" + result["booking_ids"][0], scoped)
                entry["id"] = found["id"]
                self.save()
                target = entry["target_status"]
                if found["status"] != target:
                    transitions = ["CONFIRMED", "COMPLETED"] if target == "COMPLETED" else [target]
                    for state in transitions:
                        if found["status"] == state:
                            continue
                        if found["status"] == "COMPLETED" or (found["status"] == "IN_PROGRESS" and state == "CONFIRMED"):
                            continue
                        found = self.call("PATCH", "/bookings/" + entry["id"] + "/status", scoped, json={"status": state})
                check(found["status"] == target, "Booking did not reach planned state.")
            print("Created/verified branch: " + branch["name"] + " (" + str(len(branch["staff"])) + " staff, 10 customers, 10 bookings)", flush=True)
        return token
    def verify_api(self, token):
        actual = self.call("GET", "/branches", token)
        check({b["tenant"]["id"] for b in actual} == {b["id"] for b in self.data["branches"]}, "Owner branch scope mismatch.")
        for branch in self.data["branches"]:
            scoped = self.switch(token, branch)
            check(len(self.call("GET", "/staff", scoped)) == len(branch["staff"]), "Unexpected staff count.")
            check(len(self.call("GET", "/customers", scoped)) == 10, "Unexpected customer count.")
            check(len(self.call("GET", "/bookings", scoped)) == 10, "Unexpected booking count.")
            for staff in branch["staff"]:
                auth = self.login(staff)
                branches = self.call("GET", "/branches", auth["access_token"])
                check([b["tenant"]["id"] for b in branches] == [branch["id"]], "Staff saw another branch.")
                visible = self.call("GET", "/bookings", auth["access_token"])
                check(all(b["staff_id"] == staff["id"] for b in visible), "Unexpected staff booking scope.")
            for customer in branch["customers"]:
                auth = self.login(customer, branch["slug"])
                check(auth["user"]["id"] == customer["id"], "Customer login mismatch.")
                packages = self.call("GET", "/customer-packages/me", auth["access_token"])
                check(any(p["id"] == customer["package_id"] for p in packages), "Customer package missing.")
            consumed = self.call("GET", "/customers/" + branch["customers"][1]["id"] + "/packages", scoped)
            check(next(p for p in consumed if p["id"] == branch["customers"][1]["package_id"])["used_sessions"] == 1,
                  "Completed appointment did not consume exactly one package session.")
            second_customer = branch["customers"][3]
            auth = self.login(second_customer, branch["slug"])
            notices = self.call("GET", "/notifications", auth["access_token"])
            check(any(n["type"] == "BOOKING_CREATED" for n in notices["items"]), "Counter-created notification missing.")
        self.call("GET", "/dashboard", token, params={"all_branches": "true", "day": datetime.now(TZ).date().isoformat()})
    def verify_ui(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(viewport={"width": 1440, "height": 900})
                page = context.new_page()
                self.phase = "owner_ui_login"
                page.goto(self.data["admin_login_url"])
                page.locator("#phone").fill(self.data["owner"]["phone_number"])
                page.locator("#password").fill(self.data["owner"]["password"])
                page.get_by_role("button", name="Đăng nhập", exact=True).click()
                expect(page).to_have_url(self.data["frontend_url"] + "/admin/dashboard")
                expect(page.get_by_test_id("branch-dashboard")).to_be_visible()
                self.ui_checks += 1
                for branch in self.data["branches"]:
                    page.locator("#activeBranch").select_option(branch["id"])
                    expect(page.get_by_role("heading", name="Tổng quan " + branch["name"], exact=True)).to_be_visible()
                    page.goto(self.data["frontend_url"] + "/admin/staff")
                    expect(page.get_by_role("heading", name="Nhân viên và lịch làm việc", exact=True)).to_be_visible()
                    for staff in branch["staff"]:
                        expect(page.get_by_text(staff["full_name"], exact=True).first).to_be_visible()
                    self.ui_checks += 1
                    page.goto(self.data["frontend_url"] + "/admin/dashboard")
                page.goto(self.data["frontend_url"] + "/admin/dashboard?scope=all")
                expect(page.get_by_role("heading", name="Tổng quan tất cả chi nhánh", exact=True)).to_be_visible()
                expect(page.get_by_test_id("branch-dashboard")).to_be_visible()
                self.ui_checks += 1
                context.close()
                for branch in self.data["branches"]:
                    self.phase = "staff_ui_login_" + branch["slug"]
                    staff = branch["staff"][0]
                    context = browser.new_context(viewport={"width": 390, "height": 844})
                    page = context.new_page()
                    page_errors = []
                    page.on("pageerror", lambda error: page_errors.append(str(error)[:500]))
                    request_statuses = []
                    page.on("response", lambda response: request_statuses.append({"path": urlsplit(response.url).path, "status": response.status}) if "/api/" in response.url else None)
                    page.goto(self.data["admin_login_url"])
                    page.locator("#phone").fill(staff["phone_number"])
                    page.locator("#password").fill(staff["password"])
                    page.get_by_role("button", name="Đăng nhập", exact=True).click()
                    expect(page).to_have_url(self.data["frontend_url"] + "/admin/bookings")
                    try:
                        expect(page.locator("#activeBranch")).to_have_value(branch["id"])
                    except AssertionError:
                        selector = page.locator("#activeBranch")
                        print("Staff UI diagnostic: " + json.dumps({"url": page.url, "selector_count": selector.count(),
                            "actual_branch": selector.input_value() if selector.count() else None,
                            "expected_branch": branch["id"], "api_responses": request_statuses,
                            "chunk_load_error": any("Loading chunk" in error for error in page_errors)}, ensure_ascii=False), flush=True)
                        raise
                    self.ui_checks += 1
                    context.close()
                    self.phase = "customer_ui_login_" + branch["slug"]
                    customer = branch["customers"][3]
                    context = browser.new_context(viewport={"width": 390, "height": 844})
                    page = context.new_page()
                    page.goto(branch["customer_login_url"])
                    page.locator("#custPhone").fill(customer["phone_number"])
                    page.locator("#custPassword").fill(customer["password"])
                    page.get_by_role("button", name="Đăng nhập", exact=True).click()
                    expect(page.get_by_role("button", name="Thông báo lịch hẹn", exact=True)).to_be_visible()
                    page.get_by_role("button", name="Thông báo lịch hẹn", exact=True).click()
                    expect(page.get_by_role("dialog", name="Bảng thông báo", exact=True).get_by_text("Bạn có lịch hẹn mới", exact=True)).to_be_visible()
                    self.ui_checks += 1
                    context.close()
            finally:
                browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ui-only", action="store_true", help="Verify only browser flows for an already-provisioned manifest")
    parser.add_argument("--verify-only", action="store_true", help="Read existing data and verify logins/UI without provisioning")
    parser.add_argument("--apply", action="store_true", help="Explicitly write persistent sample records to the local app")
    parser.add_argument("--frontend-url", default="http://localhost:3000")
    parser.add_argument("--api-url", default="http://localhost:8001/api/v1")
    parser.add_argument("--staff-per-branch", type=int, choices=range(1, 11), default=10)
    args = parser.parse_args()
    args.verify_only = args.verify_only or args.ui_only
    check(args.apply or args.verify_only, "Specify --apply to create persistent local review data.")
    frontend, api = local_url(args.frontend_url), local_url(args.api_url)
    path = ROOT / "local-data" / "spaos-review-accounts.json"
    check(not args.verify_only or path.exists(), "No saved manifest to verify.")
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        check(data["frontend_url"] == frontend and data["api_url"] == api, "Manifest belongs to another application.")
        check(all(len(b["staff"]) == args.staff_per_branch for b in data["branches"]), "Existing manifest staff count differs; no accounts were deleted.")
    else:
        data = make_manifest(frontend, api, args.staff_per_branch)
    runner = Runner(data, path)
    try:
        runner.preflight()
        runner.save()
        if args.verify_only or data.get("provisioned") or data["verification"].get("status") == "passed":
            check(all(b.get("id") and all(row.get("id") for row in b["bookings"]) for b in data["branches"]), "Provisioning is incomplete.")
            token = runner.login(data["owner"])["access_token"]
        else:
            operator = dotenv_values(ROOT / ".env")
            check(operator.get("OPERATOR_PHONE") and operator.get("OPERATOR_PASSWORD"), "Operator credentials are not configured in the root .env.")
            token = runner.provision(operator)
        data["provisioned"] = True
        runner.save()
        runner.phase = "verify_api"
        if not args.ui_only:
            runner.verify_api(token)
            data["api_verification"] = dict(status="passed", verified_at=datetime.now(TZ).isoformat(),
                                            api_requests_checked=runner.checks)
            runner.save()
        runner.verify_ui()
        data["verification"] = dict(status="passed", scope="browser_only" if args.ui_only else "api_and_browser", verified_at=datetime.now(TZ).isoformat(),
            api_requests_checked=runner.checks, browser_checks_passed=runner.ui_checks,
            counts=dict(owners=1, branches=3, staff=sum(len(b["staff"]) for b in data["branches"]),
                        customers=30, services=9, customer_packages=30, bookings=30),
            retained=True, push_on_real_device_verified=False)
        runner.save()
        print("PASS: persistent review data retained; credentials: " + str(path), flush=True)
        print("API checks: " + str(runner.checks) + "; UI checks: " + str(runner.ui_checks), flush=True)
    except Exception as error:
        data["verification"] = dict(status="incomplete", api_requests_checked=runner.checks,
                                    browser_checks_passed=runner.ui_checks)
        runner.save()
        print("INCOMPLETE: " + type(error).__name__ + ". Records already created are retained; rerun the same manifest to resume.", file=sys.stderr)
        frames = [frame for frame in traceback.extract_tb(error.__traceback__) if frame.filename == __file__]
        print("Verification phase: " + runner.phase + "; script line: " + str(frames[-1].lineno if frames else 0), file=sys.stderr)
        if isinstance(error, ProvisionError):
            print(str(error), file=sys.stderr)
        else:
            # Playwright diagnostics can contain filled input values; never print raw exception details.
            print("A verification failed; account secrets were not printed.", file=sys.stderr)
        return 1
    finally:
        runner.client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
