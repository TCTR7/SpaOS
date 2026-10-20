"""Manual UI audit: pytest reviews/layout_probe.py -s. Collects evidence, not a release PASS gate."""
import json
from datetime import datetime, timedelta, timezone
from playwright.sync_api import expect
from common_setup.config import config
from features.customer_regressions.conftest import scenario
from common_setup.layout_evidence import VIEWPORT_WIDTHS, capture_layout


def test_collect_layout_evidence(scenario):
    s = scenario
    booking = s["book"]()
    day = datetime.fromisoformat(booking["start_time"].replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=7))).date().isoformat()
    results = []
    def capture(page, label, width):
        selector = ('[data-layout-card="modal"]' if label.startswith("booking-modal") else
                    '[data-testid^="collection-"]' if label == "payments" else
                    '[data-layout-card="notifications"]' if label == "notifications" else
                    '[data-layout-card="customer-package"]' if label == "customer-package" else
                    '[data-layout-card="booking"]')
        evidence = capture_layout(page, task="T00c-collector", label=label,
                                  role="CUSTOMER" if "customer" in label else "ADMIN",
                                  dataset={"bookings": 1, "longNoteLength": 280 if "long-note" in label else 0},
                                  card_selector=selector,
                                  intentional_vertical_scroll_selectors=('[data-modal-scroll]',) if label.startswith("booking-modal") else (),
                                  intentional_scroll_selectors=('[data-calendar-scroll]',))
        # Collection completion proves coverage, not that every screen is fixed.
        # Preserve any measured violations for the tasks owning those screens.
        assert evidence["cardCount"] > 0, f"No target measured for {label}: {selector}"
        results.append({"screen": label, "viewport": evidence["viewport"],
                        "documentWidth": evidence["documentWidth"],
                        "measuredTargets": evidence["cardCount"],
                        "viewportOutside": evidence["viewportOutsideCount"],
                        "cardViolations": evidence["cardViolationCount"]})
    admin = s["page"](s["admin"], True)
    customer = s["page"]()
    for width in VIEWPORT_WIDTHS:
        admin.set_viewport_size({"width":width,"height":844})
        with admin.expect_response(lambda r: "/bookings?" in r.url and r.request.method=="GET"):
            admin.goto(config.frontend_url+"/admin/bookings")
        with admin.expect_response(lambda r: "/bookings?" in r.url and "date_from="+day in r.url):
            admin.locator("input[type=date]").first.fill(day)
        expect(admin.get_by_text("Khách: QA Customer",exact=False)).to_be_visible()
        capture(admin,"calendar-day",width)
        with admin.expect_response(lambda r: "/bookings?" in r.url):
            admin.get_by_role("button",name="Theo Tuần",exact=True).click()
        expect(admin.get_by_text("Khách: QA Customer",exact=False)).to_be_visible()
        capture(admin,"calendar-week",width)
        admin.get_by_role("button",name="Tạo lịch hẹn thủ công",exact=True).click()
        expect(admin.get_by_role("dialog")).to_be_visible()
        capture(admin,"booking-modal",width)
        if width == 360:
            admin.set_viewport_size({"width":360,"height":480})
            capture(admin,"booking-modal-short",width)
            admin.set_viewport_size({"width":width,"height":844})
        admin.get_by_role("button",name="Đóng",exact=True).click()
        admin.goto(config.frontend_url+"/admin/payments")
        expect(admin.get_by_test_id("collection-"+s["package"]["id"])).to_be_visible()
        capture(admin,"payments",width)
        admin.get_by_role("button",name="Thông báo",exact=True).click()
        expect(admin.get_by_role("button",name="Đọc tất cả")).to_be_visible()
        capture(admin,"notifications",width)
        customer.set_viewport_size({"width":width,"height":844})
        customer.goto(s["url"]+"/profile")
        expect(customer.get_by_text("QA One Session",exact=True)).to_be_visible()
        capture(customer,"customer-package",width)
    # Stress content uses only this disposable QA database.
    s["call"]("PATCH","/bookings/"+booking["id"],json={"start_time":booking["start_time"],"staff_id":booking["staff_id"],"note":"LongNote"*35})
    admin.set_viewport_size({"width":390,"height":844})
    with admin.expect_response(lambda r: "/bookings?" in r.url):
        admin.goto(config.frontend_url+"/admin/bookings")
    with admin.expect_response(lambda r: "/bookings?" in r.url and "date_from="+day in r.url):
        admin.locator("input[type=date]").first.fill(day)
    expect(admin.get_by_text("Ghi chú: "+"LongNote"*35,exact=True)).to_be_visible()
    capture(admin,"calendar-long-note",390)
    print(json.dumps(results,ensure_ascii=False))
