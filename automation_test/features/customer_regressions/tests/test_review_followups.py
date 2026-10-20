"""R29 regressions: no collectors, credentials from the disposable QA fixture only."""
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import expect
from common_setup.config import config


def test_collection_query_failure_hides_old_customer_and_retry_uses_current_query(scenario):
    s = scenario
    page = s["page"](s["admin"], True)
    row = dict(source_id=s["package"]["id"], source_type="package", customer_name="QA Filter A",
               phone_number=s["phone"], description="QA Treatment", occurred_at="2026-10-20T09:00:00Z",
               source_status="ACTIVE", status="UNPAID", amount_due="100000", amount_paid="0", balance_due="100000")
    failed = [True]
    queries = []
    def collections(route):
        query = parse_qs(urlsplit(route.request.url).query).get("q", [""])[0]
        queries.append(query)
        if query == "B" and failed[0]:
            route.fulfill(status=503, json={"detail": "QA query B failed"})
        else:
            route.fulfill(json=[{**row, "customer_name": "QA Filter B" if query == "B" else "QA Filter A"}])
    page.route("**/api/v1/payments/collections?*", collections)
    page.goto(config.frontend_url + "/admin/payments")
    expect(page.get_by_text("QA Filter A", exact=True)).to_be_visible()
    page.get_by_role("textbox", name="Tìm khách thu tiền", exact=True).fill("B")
    page.get_by_role("button", name="Tìm khách", exact=True).click()
    expect(page.get_by_role("main").get_by_role("alert")).to_contain_text("QA query B failed")
    expect(page.get_by_text("QA Filter A", exact=True)).to_have_count(0)
    expect(page.get_by_text("Không có khoản thu phù hợp.", exact=True)).to_have_count(0)
    expect(page.get_by_role("button", name="Xác nhận đã thu", exact=True)).to_have_count(0)
    failed[0] = False
    page.get_by_role("button", name="Thử tải lại danh sách thu tiền", exact=True).click()
    expect(page.get_by_text("QA Filter B", exact=True)).to_be_visible()
    assert queries[-2:] == ["B", "B"]
    assert all(query == "" for query in queries[:-2])  # Strict Mode may repeat initial reads.


@pytest.mark.parametrize("admin", [False, True])
@pytest.mark.parametrize("all_read", [False, True])
def test_notification_double_read_and_late_get_cannot_restore_old_counter(scenario, admin, all_read):
    s = scenario
    page = s["page"](s["admin"] if admin else s["token"], admin)
    items = [dict(id=str(i), title=f"QA Note {i}", body="QA", is_read=False,
                  created_at="2026-10-20T09:00:00Z", type="BOOKING_CREATED") for i in range(3)]
    stale, writes = [], []
    hold_reads = [False]
    def notifications(route):
        if hold_reads[0]: stale.append(route)
        else: route.fulfill(json={"unread_count": sum(not n["is_read"] for n in items), "items": items})
    page.route("**/api/v1/notifications?*", notifications)
    read_path = "/notifications/read-all" if all_read else "/notifications/0/read"
    page.route("**/api/v1" + read_path, lambda route: writes.append(route))
    page.goto(config.frontend_url + "/admin/dashboard" if admin else s["url"] + "/profile")
    opener = page.get_by_role("button", name="Thông báo" if admin else "Thông báo lịch hẹn", exact=True)
    opener.click()
    modal = page.get_by_role("dialog", name="Bảng thông báo", exact=True)
    suffix = "chưa đọc" if admin else "mới"
    expect(modal.get_by_text(f"Thông báo (3 {suffix})", exact=True)).to_be_visible()
    hold_reads[0] = True
    with page.expect_request(lambda r: "/notifications?" in r.url):
        modal.get_by_role("button", name="Làm mới thông báo", exact=True).click()
    button = modal.get_by_role("button", name="Đọc tất cả" if admin else "Đọc hết", exact=True) if all_read else modal.locator('button[title="Đánh dấu đã đọc"]').first
    with page.expect_request(lambda r: r.url.endswith(read_path)):
        button.evaluate("b => { b.click(); b.click(); }")
    expect(button).to_be_disabled()
    assert len(writes) == 1
    hold_reads[0] = False
    for item in (items if all_read else items[:1]): item["is_read"] = True
    writes[0].fulfill(json={"updated": 3} if all_read else items[0])
    remaining = 0 if all_read else 2
    expect(modal.get_by_text(f"Thông báo ({remaining} {suffix})", exact=True)).to_be_visible()
    assert stale
    for route in stale:
        with page.expect_response(lambda r: "/notifications?" in r.url) as response:
            route.fulfill(json={"unread_count": 3, "items": [{**n, "is_read": False} for n in items]})
        response.value.finished()
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    expect(modal.get_by_text(f"Thông báo ({remaining} {suffix})", exact=True)).to_be_visible()
    expect(modal.locator('button[title="Đánh dấu đã đọc"]')).to_have_count(remaining)


def test_missing_tenant_returns_to_branch_selection(scenario):
    s = scenario
    page = s["page"]()
    page.route("**/api/v1/public/tenants/" + s["slug"], lambda r: r.fulfill(status=404, json={"detail": "QA absent"}))
    page.goto(s["url"])
    link = page.get_by_role("link", name="Chọn chi nhánh", exact=True)
    expect(link).to_have_attribute("href", "/")
    expect(page.locator('a[href="/spa-demo"]')).to_have_count(0)
    link.click()
    expect(page).to_have_url(config.frontend_url + "/")


@pytest.mark.parametrize("admin", [False, True])
@pytest.mark.parametrize("stage", ["permission", "registration", "subscribe"])
def test_pending_push_enable_cannot_attach_to_replacement_session(scenario, admin, stage):
    s = scenario
    page = s["page"](s["admin"] if admin else s["token"], admin)
    page.add_init_script("""stage => {
      const sub = {toJSON:()=>({endpoint:'https://example.invalid/qa',keys:{p256dh:'qa',auth:'qa'}})};
      const pause = (name,value) => name===stage ? new Promise(resolve=>{
        window.qaReleasePush=()=>resolve(value); window.qaPushStage=name;
      }) : Promise.resolve(value);
      const reg={pushManager:{getSubscription:async()=>null,subscribe:()=>pause('subscribe',sub)}};
      Object.defineProperty(Notification,'requestPermission',{value:()=>pause('permission','granted')});
      Object.defineProperty(navigator.serviceWorker,'register',{value:()=>pause('registration',reg)});
      Object.defineProperty(navigator.serviceWorker,'ready',{get:()=>Promise.resolve(reg)});
    }""".replace("stage => {", "(() => { const stage=" + repr(stage) + ";", 1) + ")();")
    # 65 bytes is a valid uncompressed VAPID public key for the mocked push manager.
    page.route("**/api/v1/notifications/vapid-public-key", lambda r: r.fulfill(json={"enabled": True, "public_key": "BA" + "A" * 85}))
    subscriptions = []
    page.route("**/api/v1/notifications/subscribe", lambda r: (subscriptions.append(r.request), r.fulfill(status=201, json={})))
    page.goto(config.frontend_url + "/admin/dashboard" if admin else s["url"] + "/profile")
    if stage == "registration":
        # Initial automatic reattachment can also wait on registration. Wait until it completes first.
        page.wait_for_function("typeof window.qaReleasePush === 'function'")
        page.evaluate("async () => { window.qaReleasePush(); await new Promise(r => requestAnimationFrame(r)); delete window.qaPushStage; }")
    page.get_by_role("button", name="Thông báo" if admin else "Thông báo lịch hẹn", exact=True).click()
    modal = page.get_by_role("dialog", name="Bảng thông báo", exact=True)
    modal.get_by_role("button", name="Bật Push", exact=True).click()
    page.wait_for_function("window.qaPushStage === " + repr(stage))
    key = "spaos_admin_session_version" if admin else "spaos_customer_session_version_" + s["slug"]
    # Same token, new login generation: even identical JWTs must cancel the old continuation.
    page.evaluate("key => { localStorage.setItem(key, crypto.randomUUID()); window.qaReleasePush(); }", key)
    expect(modal.get_by_text("Phiên đã thay đổi.", exact=False)).to_be_visible()
    assert subscriptions == []


@pytest.mark.parametrize("admin", [False, True])
@pytest.mark.parametrize("mode", ["sync", "disable"])
def test_existing_push_lookup_cannot_change_subscription_after_session_replaced(scenario, admin, mode):
    s = scenario
    page = s["page"](s["admin"] if admin else s["token"], admin)
    page.add_init_script("""(() => {
      window.qaHoldExisting = HOLD;
      const sub={toJSON:()=>({endpoint:'https://example.invalid/qa',keys:{p256dh:'qa',auth:'qa'}}),
        unsubscribe:async()=>{window.qaBrowserUnsubscribed=true;return true;}};
      const reg={pushManager:{getSubscription:()=>window.qaHoldExisting ? new Promise(r=>{
        window.qaReleaseExisting=()=>r(sub);
      }) : Promise.resolve(sub)}};
      Object.defineProperty(navigator.serviceWorker,'register',{value:async()=>reg});
    })();""".replace("HOLD", "true" if mode == "sync" else "false"))
    subscriptions, removals = [], []
    def subscribe(route):
        subscriptions.append(route.request)
        route.fulfill(status=201, json={})
    def unsubscribe(route):
        removals.append(route.request)
        route.fulfill(json={"deleted": 1})
    page.route("**/api/v1/notifications/subscribe", subscribe)
    page.route("**/api/v1/notifications/unsubscribe", unsubscribe)
    page.goto(config.frontend_url + "/admin/dashboard" if admin else s["url"] + "/profile")
    if mode == "disable":
        page.get_by_role("button", name="Thông báo" if admin else "Thông báo lịch hẹn", exact=True).click()
        modal = page.get_by_role("dialog", name="Bảng thông báo", exact=True)
        button = modal.get_by_role("button", name="Tắt Push" if admin else "Tắt", exact=True)
        expect(button).to_be_visible()
        assert len(subscriptions) == 1
        subscriptions.clear()
        page.evaluate("window.qaHoldExisting = true")
        button.click()
    page.wait_for_function("typeof window.qaReleaseExisting === 'function'")
    key = "spaos_admin_session_version" if admin else "spaos_customer_session_version_" + s["slug"]
    page.evaluate("key => { localStorage.setItem(key, crypto.randomUUID()); window.qaReleaseExisting(); }", key)
    if mode == "disable":
        expect(modal.get_by_text("Phiên đã thay đổi.", exact=False)).to_be_visible()
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    assert subscriptions == [] and removals == []
    assert page.evaluate("window.qaBrowserUnsubscribed === true") is False


@pytest.mark.parametrize("admin", [False, True])
def test_unchanged_session_can_enable_and_disable_push(scenario, admin):
    s = scenario
    page = s["page"](s["admin"] if admin else s["token"], admin)
    page.add_init_script("""(() => {
      let subscribed=false;
      const sub={toJSON:()=>({endpoint:'https://example.invalid/qa',keys:{p256dh:'qa',auth:'qa'}}),
        unsubscribe:async()=>{subscribed=false;window.qaBrowserUnsubscribed=true;return true;}};
      const reg={pushManager:{getSubscription:async()=>subscribed?sub:null,
        subscribe:async()=>{subscribed=true;return sub;}}};
      Object.defineProperty(Notification,'requestPermission',{value:async()=>'granted'});
      Object.defineProperty(navigator.serviceWorker,'register',{value:async()=>reg});
      Object.defineProperty(navigator.serviceWorker,'ready',{get:()=>Promise.resolve(reg)});
    })();""")
    page.route("**/api/v1/notifications/vapid-public-key", lambda r: r.fulfill(json={"enabled": True, "public_key": "BA" + "A" * 85}))
    calls = []
    def record(route):
        calls.append(route.request.method)
        route.fulfill(status=201 if route.request.method == "POST" else 200, json={})
    page.route("**/api/v1/notifications/subscribe", record)
    page.route("**/api/v1/notifications/unsubscribe", record)
    page.goto(config.frontend_url + "/admin/dashboard" if admin else s["url"] + "/profile")
    page.get_by_role("button", name="Thông báo" if admin else "Thông báo lịch hẹn", exact=True).click()
    modal = page.get_by_role("dialog", name="Bảng thông báo", exact=True)
    modal.get_by_role("button", name="Bật Push", exact=True).click()
    disable = modal.get_by_role("button", name="Tắt Push" if admin else "Tắt", exact=True)
    expect(disable).to_be_enabled()
    disable.click()
    expect(modal.get_by_role("button", name="Bật Push", exact=True)).to_be_enabled()
    assert calls == ["POST", "DELETE"]
    assert page.evaluate("window.qaBrowserUnsubscribed === true") is True
