from datetime import datetime, timedelta
import pytest
from playwright.sync_api import expect
from common_setup.api_helper import random_phone
from common_setup.config import config
from features.customer_regressions.pages.appointments_page import CustomerAppointmentsPage


def test_admin_transfers_customer_and_old_staff_loses_ui_and_api_access(scenario, api_helper):
    s = scenario
    booking = s["book"]()
    second = s["call"]("POST", "/staff", json={"full_name": "QA Second Staff",
                        "phone_number": random_phone(), "password": "Staff@123"})
    first_token = api_helper.login(s["slug"], s["staff"]["phone_number"], "Staff@123")["access_token"]
    second_token = api_helper.login(s["slug"], second["phone_number"], "Staff@123")["access_token"]
    first, second_page = s["page"](first_token, True), s["page"](second_token, True)
    first.goto(config.frontend_url + "/admin/customers")
    expect(first.get_by_text("QA Customer", exact=True).first).to_be_visible()
    second_page.goto(config.frontend_url + "/admin/customers")
    expect(second_page.get_by_text("Không tìm thấy khách hàng nào.", exact=True)).to_be_visible()
    expect(second_page.get_by_text("QA Customer", exact=True)).to_have_count(0)
    admin = s["page"](s["admin"], True)
    admin.goto(config.frontend_url + "/admin/customers")
    admin.locator("#customerOwner").select_option(second["id"])
    with admin.expect_response(lambda r: r.url.endswith("/assignment")) as response:
        admin.get_by_role("button", name="Chuyển người phụ trách", exact=True).click()
    assert response.value.status == 200
    assert response.value.json()["assigned_staff_id"] == second["id"]
    first.reload()
    expect(first.get_by_text("Không tìm thấy khách hàng nào.", exact=True)).to_be_visible()
    response = first.request.patch(config.api_v1_url + "/customers/" + s["customer"]["id"],
                                   headers={"Authorization": "Bearer " + first_token},
                                   data={"notes": "forbidden"})
    assert response.status == 404
    response = first.request.get(config.api_v1_url + "/bookings/" + booking["id"],
                                 headers={"Authorization": "Bearer " + first_token})
    assert response.status == 404
    second_page.reload()
    expect(second_page.get_by_text("QA Customer", exact=True).first).to_be_visible()
    second_page.get_by_role("button", name="Sửa hồ sơ", exact=True).click()
    second_page.locator("#custNotes").fill("New owner note")
    with second_page.expect_response(lambda r: r.request.method == "PATCH" and "/customers/" in r.url) as changed:
        second_page.get_by_role("button", name="Lưu thông tin", exact=True).click()
    assert changed.value.status == 200


@pytest.mark.parametrize("conflict", [False, True], ids=["success-preserves-booking", "conflict-preserves-old-slot"])
def test_customer_reschedule_is_atomic(scenario, api_helper, conflict):
    s = scenario
    booking = s["book"]()
    page = s["page"]()
    appointments = CustomerAppointmentsPage(page, s["url"])
    appointments.open()
    day = (datetime.now() + timedelta(days=7)).date().isoformat()
    chosen = appointments.choose_new_date(day)
    modal = page.get_by_role("dialog")
    rival = None
    if conflict:
        rival = api_helper.create_booking(s["token"], chosen, [{"service_id": s["service"]["id"]}])
    mutations = []
    page.on("request", lambda r: mutations.append((r.method, r.url)) if "/bookings" in r.url and r.method in ("POST", "PATCH") else None)
    try:
        result = appointments.confirm(booking["id"])
        assert result.status == (409 if conflict else 200)
        assert len(mutations) == 1 and mutations[0][0] == "PATCH"
        current = s["call"]("GET", "/bookings/" + booking["id"])
        assert current["id"] == booking["id"] and current["items"] == booking["items"]
        assert current["status"] == booking["status"]
        if conflict:
            assert current["start_time"] == booking["start_time"]
            expect(modal.get_by_text(result.json()["detail"], exact=True)).to_be_visible()
        else:
            assert datetime.fromisoformat(current["start_time"].replace("Z", "+00:00")) == datetime.fromisoformat(chosen.replace("Z", "+00:00"))
            expect(modal).to_have_count(0)
        cards = s["call"]("GET", "/customer-packages/me", headers={"Authorization": "Bearer " + s["token"]})
        assert (cards[0]["used_sessions"], cards[0]["reserved_sessions"]) == (0, 1)
    finally:
        if rival:
            s["call"]("POST", "/bookings/" + rival["id"] + "/cancel")


def test_admin_can_handover_customer_during_reschedule_ui(scenario, api_helper):
    s = scenario
    booking = s["book"]()
    other = s["call"]("POST", "/staff", json={"full_name": "Replacement", "phone_number": random_phone(), "password": "Staff@123"})
    s["call"]("PUT", "/staff/" + other["id"] + "/schedules", json={"schedules": [
        {"day_of_week": d, "start_time": "00:00:00", "end_time": "23:59:00"} for d in range(7)]})
    page = s["page"](s["admin"], True)
    page.goto(config.frontend_url + "/admin/bookings")
    day = datetime.fromisoformat(booking["start_time"].replace("Z", "+00:00")).date().isoformat()
    page.locator('input[type="date"]').first.fill(day)
    page.get_by_role("button", name="Đổi ngày / giờ / KTV", exact=True).click()
    modal = page.get_by_role("dialog")
    modal.locator("#rescheduleStaffAdmin").select_option(other["id"])
    modal.locator("#transferCustomer").check()
    new_day = (datetime.now() + timedelta(days=8)).date().isoformat()
    with page.expect_response(lambda r: "/bookings/available-slots?" in r.url and "date=" + new_day in r.url) as slots:
        modal.locator("#rescheduleDateAdmin").fill(new_day)
    assert slots.value.status == 200
    modal.locator("button:has-text('KTV rảnh')").first.click()
    with page.expect_response(lambda r: r.url.endswith("/bookings/" + booking["id"]) and r.request.method == "PATCH") as changed:
        modal.get_by_role("button", name="Xác nhận đổi lịch", exact=True).click()
    assert changed.value.status == 200
    assert changed.value.json()["staff_id"] == other["id"]
    rows = s["call"]("GET", "/customers")
    assert rows[0]["assigned_staff_id"] == other["id"]
    first_token = api_helper.login(s["slug"], s["staff"]["phone_number"], "Staff@123")["access_token"]
    forbidden = page.request.get(config.api_v1_url + "/bookings/" + booking["id"],
                                 headers={"Authorization": "Bearer " + first_token})
    assert forbidden.status == 404
