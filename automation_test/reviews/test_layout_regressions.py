"""Calendar layout gates, including the three former UX-01/02 strict xfails."""
from datetime import datetime, timedelta, timezone

import pytest
from playwright.sync_api import expect

from common_setup.config import config
from common_setup.layout_evidence import assert_layout_contained, capture_layout
from features.customer_regressions.conftest import scenario


def load_calendar(s, width, *, week=False, note=None):
    booking = s["book"]()
    if note:
        s["call"]("PATCH", "/bookings/" + booking["id"], json={
            "start_time": booking["start_time"], "staff_id": booking["staff_id"], "note": note,
        })
    day = datetime.fromisoformat(booking["start_time"].replace("Z", "+00:00")).astimezone(
        timezone(timedelta(hours=7))).date().isoformat()
    page = s["page"](s["admin"], True)
    page.set_viewport_size({"width": width, "height": 844})
    try:
        page.goto(config.frontend_url + "/admin/bookings")
        with page.expect_response(lambda r: "/bookings?" in r.url and "date_from=" + day in r.url):
            page.locator("input[type=date]").first.fill(day)
        card = page.get_by_test_id("booking-card-" + booking["id"])
        expect(card).to_be_visible()
        if week:
            with page.expect_response(lambda r: "/bookings?" in r.url and r.request.method == "GET"):
                page.get_by_role("button", name="Theo Tuần", exact=True).click()
            expect(page.get_by_test_id("calendar-container")).to_be_visible()
            expect(card).to_be_visible()
    except AssertionError as error:
        raise RuntimeError("Layout setup did not render the requested QA booking") from error
    return page


def test_long_note_contained_in_mobile_calendar(scenario):
    page = load_calendar(scenario, 390, note="LongNote" * 35)
    evidence = capture_layout(page, task="UX-02-regression", label="long-note", role="ADMIN",
                              dataset={"bookings": 1, "noteLength": 280})
    assert_layout_contained(evidence)


@pytest.mark.parametrize("width", [768, 1366])
def test_week_cards_contained(scenario, width):
    page = load_calendar(scenario, width, week=True)
    evidence = capture_layout(page, task="UX-01-regression", label="week", role="ADMIN",
                              dataset={"bookings": 1}, intentional_scroll_selectors=('[data-calendar-scroll]',))
    assert_layout_contained(evidence)
    summary = page.locator('[data-layout-card="booking"] summary').first
    summary.click()
    expect(summary.locator("..")).to_have_attribute("open", "")
    expanded = capture_layout(page, task="UX-01-regression", label="week-expanded", role="ADMIN",
                             dataset={"bookings": 1, "expanded": True},
                             intentional_scroll_selectors=('[data-calendar-scroll]',))
    assert_layout_contained(expanded)
