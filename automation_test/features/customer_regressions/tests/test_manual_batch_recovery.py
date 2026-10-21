from datetime import datetime, timedelta, timezone
import pytest
from playwright.sync_api import expect
from common_setup.api_helper import random_phone
from features.ui_quality.tests.test_dialog_workflows import manual


def prepare(s):
    s["call"]("PATCH", "/services/" + s["service"]["id"], json={"total_sessions": 3})
    page, modal, _ = manual(s)
    modal.get_by_role("button", name="+ Tạo nhanh khách mới", exact=True).click()
    phone = random_phone()
    modal.get_by_placeholder("Họ và tên khách hàng *", exact=True).fill("QA Batch Recovery")
    modal.get_by_placeholder("Số điện thoại (9-15 số) *", exact=True).fill(phone)
    modal.locator("label").filter(has_text="QA Treatment").get_by_role("checkbox").check()
    modal.get_by_role("button", name="⚡ Lên lịch đủ 3 buổi", exact=True).click()
    dates = modal.locator("input[type=date]")
    expect(dates).to_have_count(3)
    base = datetime.now(timezone(timedelta(hours=7))).date() + timedelta(days=7)
    for i in range(3):
        day = (base + timedelta(days=i)).isoformat()
        with page.expect_response(lambda r: "/available-slots?" in r.url and "date=" + day in r.url):
            dates.nth(i).fill(day)
    expect(modal.get_by_role("button", name="Xác nhận tạo 3 buổi hẹn", exact=True)).to_be_enabled()
    return page, modal, phone


@pytest.mark.parametrize("mode", ["retry", "check", "reload"])
def test_lost_committed_response_never_duplicates_customer_package_or_sessions(scenario, mode):
    s = scenario
    page, modal, phone = prepare(s)
    sent, saved = [], []
    def lose(route):
        sent.append(route.request.post_data_json)
        response = route.fetch()
        assert response.status == 201, response.text()
        saved.append(response.json())
        route.fulfill(status=503, json={"detail": "QA response lost after commit"})
    page.route("**/api/v1/bookings/manual-batches", lose)
    modal.get_by_role("button", name="Xác nhận tạo 3 buổi hẹn", exact=True).click()
    expect(modal.get_by_text("QA response lost after commit", exact=True)).to_be_visible()
    assert len(sent) == 1
    page.unroute("**/api/v1/bookings/manual-batches", lose)
    posted = []
    page.on("request", lambda r: posted.append(r.post_data_json) if r.method == "POST" and r.url.endswith("/manual-batches") else None)
    key = "spaos_manual_batch_" + s["customer"]["tenant_id"] + "_"
    stored = page.evaluate("prefix => Object.entries(sessionStorage).filter(([k]) => k.startsWith(prefix))", key)
    assert len(stored) == 1 and stored[0][1] == sent[0]["request_id"]
    assert phone not in str(stored) and "QA Batch Recovery" not in str(stored)
    if mode == "reload":
        page.reload()
        expect(modal).to_be_visible()
        expect(modal.get_by_role("button", name="Thử lại", exact=True)).to_have_count(0)
    elif mode == "check":
        modal.get_by_role("button", name="Kiểm tra sau", exact=True).click()
        expect(modal).to_have_count(0)
        page.get_by_role("button", name="Tạo lịch hẹn thủ công", exact=True).click()
        expect(modal.get_by_placeholder("Số điện thoại (9-15 số) *", exact=True)).to_have_value(phone)
    modal.get_by_role("button", name="Thử lại" if mode == "retry" else "Kiểm tra kết quả", exact=True).click()
    expect(modal).to_have_count(0)
    expect(page.get_by_role("status").filter(has_text="Đã lưu 3 buổi hẹn")).to_be_visible()
    assert posted == ([sent[0]] if mode == "retry" else [])
    customers = s["call"]("GET", "/customers", params={"q": phone})
    assert len(customers) == 1 and customers[0]["id"] == saved[0]["customer_id"]
    packages = s["call"]("GET", "/customers/" + customers[0]["id"] + "/packages")
    assert len(packages) == 1 and packages[0]["id"] == saved[0]["package_ids"][0]
    rows = s["call"]("GET", "/bookings", params={"customer_id": customers[0]["id"]})
    assert {r["id"] for r in rows} == set(saved[0]["booking_ids"]) and len(rows) == 3
    assert all(r["items"][0]["customer_package_id"] == packages[0]["id"] for r in rows)
    assert packages[0]["used_sessions"] == 0


def test_uncommitted_failure_keeps_request_id_when_editing(scenario):
    s = scenario
    page, modal, phone = prepare(s)
    sent = []
    def fail(route):
        sent.append(route.request.post_data_json)
        route.fulfill(status=503, json={"detail": "QA request not committed"})
    page.route("**/api/v1/bookings/manual-batches", fail)
    modal.get_by_role("button", name="Xác nhận tạo 3 buổi hẹn", exact=True).click()
    expect(modal.get_by_text("QA request not committed", exact=True)).to_be_visible()
    modal.get_by_role("button", name="Kiểm tra kết quả", exact=True).click()
    expect(modal.get_by_text("Chưa có lịch nào được lưu", exact=False)).to_be_visible()
    modal.locator("#modalNote").fill("Edited after checking")
    modal.get_by_role("button", name="Xác nhận tạo 3 buổi hẹn", exact=True).click()
    expect(modal.get_by_text("QA request not committed", exact=True)).to_be_visible()
    assert len(sent) == 2 and sent[0]["request_id"] == sent[1]["request_id"]
    assert sent[0]["note"] != sent[1]["note"]
    assert s["call"]("GET", "/customers", params={"q": phone}) == []
