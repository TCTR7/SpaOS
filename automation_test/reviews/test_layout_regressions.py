"""Calendar layout gates, including the three former UX-01/02 strict xfails."""
from datetime import datetime, timedelta, timezone

import pytest
from playwright.sync_api import expect

from common_setup.config import config
from common_setup.layout_evidence import assert_layout_contained, measure_layout
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
    check_layout(page, "UX-02-regression", "long-note")


def check_layout(page, task, label):
    options = dict(intentional_scroll_selectors=('[data-calendar-scroll]',))
    # The assertion includes measured bounds; preserve it without file capture.
    assert_layout_contained(measure_layout(page, **options))


def test_layout_failure_preserves_original_assertion_without_capture(monkeypatch):
    import sys
    module = sys.modules[__name__]
    monkeypatch.setattr(module, "measure_layout", lambda *args, **kwargs: {})
    def failed_assertion(evidence):
        raise AssertionError("QA intentional clipping failure")
    monkeypatch.setattr(module, "assert_layout_contained", failed_assertion)
    with pytest.raises(AssertionError, match="QA intentional clipping failure"):
        check_layout(None, "no-artifact", "no-artifact")


@pytest.mark.parametrize("width", [768, 1366])
def test_week_cards_contained(scenario, width):
    page = load_calendar(scenario, width, week=True)
    check_layout(page, "UX-01-regression", "week")
    summary = page.locator('[data-layout-card="booking"] summary').first
    summary.click()
    expect(summary.locator("..")).to_have_attribute("open", "")
    check_layout(page, "UX-01-regression", "week-expanded")
