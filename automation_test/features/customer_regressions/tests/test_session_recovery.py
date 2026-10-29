"""Fault injection only at browser HTTP boundary; the QA database stays isolated."""
import pytest
from playwright.sync_api import expect
from common_setup.config import config


def session_page(s, admin):
    page = s["page"](s["admin"] if admin else s["token"], admin)
    key = "spaos_admin_token" if admin else "spaos_customer_token_" + s["slug"]
    url = config.frontend_url + "/admin/customers" if admin else s["url"] + "/profile"
    return page, key, url


def verified(page, admin):
    if admin:
        expect(page.get_by_role("banner").get_by_role("button",name="Thông báo",exact=True)).to_be_visible()
        # Mobile CRM now opens details explicitly; validate its loaded list first.
        expect(page.get_by_role("button", name="QA Customer SĐT:", exact=False)).to_be_visible()
    else:
        expect(page.get_by_text("QA One Session", exact=True)).to_be_visible()


@pytest.mark.parametrize("admin", [False, True], ids=["customer", "admin"])
@pytest.mark.parametrize("fault", ["503", "network"])
def test_me_outage_retains_token_hides_data_and_retries(scenario, admin, fault):
    s = scenario
    page, key, url = session_page(s, admin)
    pattern = "**/api/v1/auth/me"
    page.route(pattern, lambda route: route.abort("internetdisconnected") if fault == "network"
               else route.fulfill(status=503, json={"detail": "QA unavailable"}))
    page.goto(url)
    expect(page.get_by_role("alert").filter(has_text="Chưa tải được tài khoản")).to_be_visible()
    expect(page.get_by_text("QA One Session", exact=True)).not_to_be_visible()
    expect(page.locator("#activeBranch")).to_have_count(0)
    assert page.evaluate("key => localStorage.getItem(key)", key) == (s["admin"] if admin else s["token"])
    page.unroute(pattern)
    page.get_by_role("button", name="Thử lại", exact=True).click()
    verified(page, admin)


@pytest.mark.parametrize("admin", [False, True], ids=["customer", "admin"])
def test_current_401_only_clears_its_own_session(scenario, admin):
    s = scenario
    page, key, url = session_page(s, admin)
    page.add_init_script("localStorage.setItem('spaos_customer_token_other-spa', 'keep-other');")
    other = "spaos_customer_token_" + s["slug"] if admin else "spaos_admin_token"
    page.add_init_script("localStorage.setItem(" + repr(other) + ", 'keep-other-role');")
    page.route("**/api/v1/auth/me", lambda route: route.fulfill(status=401, json={"detail": "QA expired"}))
    if admin:
        page.route("**/api/v1/auth/resolve",lambda route:route.fulfill(status=401,json={"detail":"QA expired credentials"}))
    page.goto(url)
    if admin:
        expect(page).to_have_url(config.frontend_url + "/admin/login")
    else:
        expect(page.get_by_role("main").get_by_role("link", name="Đăng nhập", exact=True)).to_be_visible()
    assert page.evaluate("key => localStorage.getItem(key)", key) is None
    assert page.evaluate("key => localStorage.getItem(key)", other) == "keep-other-role"
    assert page.evaluate("localStorage.getItem('spaos_customer_token_other-spa')") == "keep-other"


def test_branch_list_failure_has_retry_instead_of_false_empty_permissions(scenario):
    s = scenario
    page, key, url = session_page(s, True)
    page.route("**/api/v1/branches", lambda route: route.fulfill(status=503, json={"detail": "QA branches unavailable"}))
    page.goto(url)
    expect(page.get_by_role("alert").filter(has_text="Chưa tải được tài khoản và chi nhánh")).to_be_visible()
    expect(page.locator("#activeBranch")).to_have_count(0)
    assert page.evaluate("key => localStorage.getItem(key)", key) == s["admin"]
    page.unroute("**/api/v1/branches")
    page.get_by_role("button", name="Thử lại", exact=True).click()
    verified(page, True)


@pytest.mark.parametrize("old_status", [200, 401])
@pytest.mark.parametrize("admin", [False, True], ids=["customer", "admin"])
def test_late_me_cannot_restore_old_user_or_erase_new_token(scenario, admin, old_status):
    s = scenario
    page, key, url = session_page(s, admin)
    held = []
    holding = [True]
    def hold(route):
        if not holding[0]:
            route.fulfill(status=503, json={"detail": "QA new validation unavailable"})
            return
        held.append((route, route.fetch() if old_status == 200 else None))
        page.evaluate("window.qaHeldMe = true")
    page.route("**/api/v1/auth/me", hold)
    page.goto(url)
    expect(page.get_by_text("Đang tải..." if admin else "Đang kiểm tra đăng nhập...", exact=True)).to_be_visible()
    # Synchronize with the actual request, not a timeout or arbitrary sleep.
    page.wait_for_function("window.qaHeldMe === true")
    assert held
    holding[0] = False
    page.evaluate("""({key}) => {
      localStorage.setItem(key, 'replacement-token');
      window.dispatchEvent(new CustomEvent(key === 'spaos_admin_token' ? 'spaos:admin-session-changed' : 'spaos:customer-session-changed',
        {detail: key.replace('spaos_customer_token_', '')}));
    }""", {"key": key})
    # New validation fails transiently, so its token must remain and no old data may return.
    while held:
        route, response = held.pop()
        if old_status == 200:
            route.fulfill(response=response)
        else:
            route.fulfill(status=401, json={"detail": "QA old expired"})
    expect(page.get_by_role("alert").filter(has_text="Chưa tải được tài khoản")).to_be_visible()
    assert page.evaluate("key => localStorage.getItem(key)", key) == "replacement-token"
    expect(page.get_by_text("QA One Session", exact=True)).not_to_be_visible()
    expect(page.locator("#activeBranch")).to_have_count(0)


@pytest.mark.parametrize("admin", [False, True], ids=["customer", "admin"])
def test_late_resource_401_does_not_clear_replacement_session(scenario, admin):
    s = scenario
    page, key, url = session_page(s, admin)
    pattern = "**/api/v1/customers?*" if admin else "**/api/v1/customer-packages/me"
    held = []
    def hold_resource(route):
        held.append(route)
        page.evaluate("window.qaHeldResource = true")
    page.route(pattern, hold_resource)
    page.goto(url)
    if admin:
        expect(page.get_by_role("banner").get_by_role("button",name="Thông báo",exact=True)).to_be_visible()
    else:
        expect(page.get_by_role("button", name="Thoát", exact=True)).to_be_visible()
    page.wait_for_function("window.qaHeldResource === true")
    assert held
    page.evaluate("({key}) => localStorage.setItem(key, 'replacement-token')", {"key": key})
    for route in held:
        route.fulfill(status=401, json={"detail": "QA old expired"})
    expect(page.get_by_text("Thông tin đăng nhập không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại.", exact=True)).to_be_visible()
    assert page.evaluate("key => localStorage.getItem(key)", key) == "replacement-token"
    assert "/admin/login" not in page.url


@pytest.mark.parametrize("admin", [False, True], ids=["customer", "admin"])
def test_logout_in_another_tab_removes_verified_ui(scenario, admin):
    s = scenario
    page, key, url = session_page(s, admin)
    page.goto(url)
    verified(page, admin)
    other = page.context.new_page()
    other.goto(config.frontend_url + "/admin/login")
    other.evaluate("key => localStorage.removeItem(key)", key)
    if admin:
        expect(page).to_have_url(config.frontend_url + "/admin/login")
    else:
        expect(page.get_by_role("main").get_by_role("link", name="Đăng nhập", exact=True)).to_be_visible()
    expect(page.get_by_text("QA One Session", exact=True)).not_to_be_visible()


@pytest.mark.parametrize("old_status", [200, 503])
def test_late_branch_switch_cannot_replace_a_new_verified_branch(scenario, old_status):
    s = scenario
    b = s["call"]("POST", "/branches", json={"name": "QA Branch B"})["tenant"]
    c = s["call"]("GET", "/auth/me")["tenant"]
    replacement = s["call"]("POST", "/branches/" + c["id"] + "/switch")["access_token"]
    page, key, url = session_page(s, True)
    page.goto(url)
    verified(page, True)
    held = []
    page.route("**/api/v1/branches/" + b["id"] + "/switch", lambda route: held.append((route, route.fetch() if old_status == 200 else None)))
    with page.expect_request(lambda r: r.url.endswith("/" + b["id"] + "/switch")):
        page.locator("#activeBranch").select_option(b["id"])
    page.evaluate("""({key, token}) => {
      localStorage.setItem(key, token);
      window.dispatchEvent(new Event('spaos:admin-session-changed'));
    }""", {"key": key, "token": replacement})
    expect(page.locator("#activeBranch")).to_have_value(c["id"])
    assert held
    for route, response in held:
        with page.expect_response(lambda r: r.url.endswith("/" + b["id"] + "/switch")) as old:
            if response:
                route.fulfill(response=response)
            else:
                route.fulfill(status=503, json={"detail": "QA old branch error"})
        old.value.finished()
    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
    expect(page.locator("#activeBranch")).to_have_value(c["id"])
    assert page.evaluate("key => localStorage.getItem(key)", key) == replacement
    expect(page.locator("#activeBranch")).to_be_enabled()
    expect(page.get_by_text("QA old branch error", exact=True)).to_have_count(0)


def test_logout_removes_portaled_private_dialog_before_new_validation(scenario):
    s = scenario
    s["book"]()
    page = s["page"]()
    page.goto(s["url"] + "/appointments")
    page.get_by_role("button", name="Đổi ngày/giờ", exact=True).click()
    expect(page.get_by_role("dialog")).to_be_visible()
    page.route("**/api/v1/auth/me", lambda route: route.fulfill(status=503, json={"detail": "QA verify unavailable"}))
    page.evaluate("""slug => {
      localStorage.setItem('spaos_customer_token_' + slug, 'replacement-token');
      window.dispatchEvent(new CustomEvent('spaos:customer-session-changed', {detail: slug}));
    }""", s["slug"])
    expect(page.get_by_role("dialog")).to_have_count(0)
    expect(page.get_by_role("alert").filter(has_text="Chưa tải được tài khoản")).to_be_visible()


def test_slow_push_cleanup_cannot_logout_a_new_customer_session(scenario):
    s = scenario
    page = s["page"]()
    page.add_init_script("""Object.defineProperty(navigator.serviceWorker, 'getRegistration', {
      value: () => new Promise(resolve => { window.qaResolvePushCleanup = resolve; })
    });""")
    page.goto(s["url"] + "/profile")
    page.get_by_role("button", name="Thoát", exact=True).click()
    page.wait_for_function("typeof window.qaResolvePushCleanup === 'function'")
    # Use the in-app link to retain the pending cleanup promise.
    page.get_by_role("main").get_by_role("link", name="Đăng nhập", exact=True).click()
    page.locator("#custPhone").fill(s["phone"])
    page.locator("#custPassword").fill("Customer@123")
    page.get_by_role("button", name="Đăng nhập", exact=True).click()
    expect(page).to_have_url(s["url"] + "/profile")
    page.evaluate("""() => window.qaResolvePushCleanup({pushManager: {getSubscription: async () => ({
      endpoint: 'https://example.invalid/old-subscription', unsubscribe: async () => {window.qaWrongUnsubscribe = true;}
    })}})""")
    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
    assert page.evaluate("slug => Boolean(localStorage.getItem('spaos_customer_token_' + slug))", s["slug"])
    assert page.evaluate("window.qaWrongUnsubscribe === true") is False
    expect(page.get_by_role("link", name="QA Customer", exact=True)).to_be_visible()


def test_relogin_in_another_tab_is_new_session_even_if_jwt_is_identical(scenario):
    s = scenario
    page = s["page"]()
    held = []
    holding = [True]
    def intercept(route):
        if holding[0]:
            held.append(route)
            page.evaluate("window.qaHeldSameSessionPackages = true")
        else:
            route.continue_()
    page.route("**/api/v1/customer-packages/me", intercept)
    page.goto(s["url"] + "/profile")
    expect(page.get_by_role("button", name="Thoát", exact=True)).to_be_visible()
    page.wait_for_function("window.qaHeldSameSessionPackages === true")
    assert held
    holding[0] = False
    other = page.context.new_page()
    other.goto(s["url"] + "/login")
    # Identical JWTs can occur for the same account within the same second.
    other.route("**/api/v1/auth/login", lambda route: route.fulfill(json={
        "access_token": s["token"], "token_type": "bearer", "expires_in": 3600,
        "user": s["customer"],
    }))
    other.locator("#custPhone").fill(s["phone"])
    other.locator("#custPassword").fill("Customer@123")
    other.get_by_role("button", name="Đăng nhập", exact=True).click()
    expect(other).to_have_url(s["url"] + "/book")
    expect(page.get_by_text("QA One Session", exact=True)).to_be_visible()
    for route in held:
        with page.expect_response(lambda r: r.url.endswith("/customer-packages/me")) as old:
            route.fulfill(status=401, json={"detail": "QA old session expired"})
        old.value.finished()
    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
    assert page.evaluate("slug => localStorage.getItem('spaos_customer_token_' + slug)", s["slug"]) == s["token"]
    expect(page.get_by_text("QA One Session", exact=True)).to_be_visible()
