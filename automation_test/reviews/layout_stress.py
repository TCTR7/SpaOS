"""Explicit large-data evidence collector, never part of default E2E discovery."""
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from playwright.sync_api import expect

from common_setup.api_helper import random_phone
from common_setup.config import config
from common_setup.layout_evidence import VIEWPORT_WIDTHS, assert_layout_contained, capture_layout


@pytest.fixture
def stress_data(api_helper, browser_instance):
    slug = "qa-layout-" + uuid4().hex
    auth = api_helper.register_tenant("QA Layout Stress", slug, "QA Admin", random_phone())
    token = auth["access_token"]
    headers = {"Authorization": "Bearer " + token}
    def call(method, path, **kwargs):
        response = api_helper.client.request(method, path, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()
    call("PATCH", "/tenants/me", json={"open_time": "00:00:00", "close_time": "23:59:00"})
    staff = []
    for index in range(10):
        item = call("POST", "/staff", json={"full_name": "QA Staff " + str(index) + " " + "S" * 64,
                    "phone_number": random_phone(), "password": "Staff@123"})
        call("PUT", "/staff/" + item["id"] + "/schedules", json={"schedules": [
            {"day_of_week": day, "start_time": "00:00:00", "end_time": "23:59:00"}
            for day in range(7)]})
        staff.append(item)
    customers = [api_helper.create_customer(token, ("QA Customer " + str(i) + " " + "C" * 80)[:80],
                                            random_phone()) for i in range(210)]
    service = api_helper.create_service(token, "QA Long Treatment " + "Service " * 12,
                                       duration_minutes=10, price=999999999)
    first_day = (datetime.now(timezone(timedelta(hours=7))) + timedelta(days=8)).date()
    # Put four complete dates in one week even when run on Sunday.
    first_day -= timedelta(days=first_day.weekday())
    start = datetime.combine(first_day, datetime.min.time(), tzinfo=timezone(timedelta(hours=7)))
    for index in range(240):
        day, within_day = divmod(index, 60)
        hour_group, staff_index = divmod(within_day, 10)
        when = start + timedelta(days=day, hours=9, minutes=hour_group * 45)
        call("POST", "/bookings", json={"customer_id": customers[index % 210]["id"],
             "staff_id": staff[staff_index]["id"], "start_time": when.isoformat(),
             "items": [{"service_id": service["id"]}],
             "note": "LongNote" * 35 if index == 0 else "QA layout stress"})
    context = browser_instance.new_context(viewport={"width": 390, "height": 844})
    context.add_init_script("localStorage.setItem('spaos_admin_token'," + json.dumps(token) + ");")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        yield dict(page=page, first_day=first_day.isoformat(), call=call,
                   dataset={"staff": 10, "customers": 210, "bookings": 240,
                            "bookingsPerDay": 60, "nameLength": 80, "noteLength": 280})
    finally:
        context.close()
        # The enclosing runner drops the whole generated DB, including these records.
    assert not errors, errors


def test_collect_large_layout_evidence(stress_data):
    s = stress_data
    page = s["page"]
    rows = s["call"]("GET", "/bookings", params={"date_from": s["first_day"],
                      "date_to": s["first_day"], "limit": 200})
    assert len(rows) == 60, "Stress fixture did not create all daily bookings"
    summaries = []
    for width in VIEWPORT_WIDTHS:
        page.set_viewport_size({"width": width, "height": 844})
        page.goto(config.frontend_url + "/admin/bookings")
        with page.expect_response(lambda r: "/bookings?" in r.url and "date_from=" + s["first_day"] in r.url):
            page.locator("input[type=date]").first.fill(s["first_day"])
        expect(page.locator('[data-layout-card="booking"]')).to_have_count(60)
        evidence = capture_layout(page, task="T00c-stress", label="calendar-day", role="ADMIN",
                                  dataset=s["dataset"], full_page=False)
        assert_layout_contained(evidence)
        summaries.append({"width": width, "view": "day", "cards": len(evidence["cards"]),
                          "violations": evidence["cardViolationCount"]})
        with page.expect_response(lambda r: "/bookings?" in r.url and r.request.method == "GET"):
            page.get_by_role("button", name="Theo Tuần", exact=True).click()
        # Existing endpoint/UI caps a range at 200. Record it explicitly for T08,
        # rather than asserting that this means all 240 fixtures were displayed.
        expect(page.locator('[data-layout-card="booking"]')).to_have_count(200)
        evidence = capture_layout(page, task="T00c-stress", label="calendar-week", role="ADMIN",
                                  dataset={**s["dataset"], "expectedInRange": 240, "renderedCap": 200},
                                  intentional_scroll_selectors=('[data-calendar-scroll]',),
                                  full_page=False)
        assert_layout_contained(evidence)
        summaries.append({"width": width, "view": "week", "cards": len(evidence["cards"]),
                          "violations": evidence["cardViolationCount"]})
    print(json.dumps(summaries))
