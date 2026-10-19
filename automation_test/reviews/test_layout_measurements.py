"""Calibrate hidden-content handling without hiding real card overflows."""
import pytest
from common_setup.layout_evidence import assert_layout_contained, measure_layout


def test_closed_details_ignored_but_expanded_overflow_detected(unauthenticated_page):
    page = unauthenticated_page
    page.set_content('<div data-calendar-scroll style="width:300px;overflow-x:auto">'
                     '<section style="width:700px"><article data-layout-card="booking" style="width:150px">'
                     '<details><summary>Details</summary><p style="white-space:nowrap">'
                     + 'Unbroken' * 60 + '</p></details></article></section></div>')
    options = dict(intentional_scroll_selectors=('[data-calendar-scroll]',))
    closed = measure_layout(page, **options)
    assert len(closed["cards"]) == 1
    assert closed["cardViolationCount"] == 0
    page.locator("summary").click()
    expanded = measure_layout(page, **options)
    assert expanded["cardViolationCount"] > 0, "Scroll ancestor must not exclude overflow inside a card"


def test_overlapping_text_inside_card_is_detected(unauthenticated_page):
    page = unauthenticated_page
    page.set_content('<article data-layout-card="booking" style="position:relative;width:300px;height:80px">'
                     '<span style="position:absolute;left:0;top:0">10:00 - 10:30</span>'
                     '<span style="position:absolute;left:20px;top:0">Pending confirmation</span></article>')
    evidence = measure_layout(page)
    assert any(v["kind"] == "content-overlap-within-card"
               for card in evidence["cards"] for v in card["violations"])


def test_layout_gate_rejects_unapproved_offscreen_content(unauthenticated_page):
    page = unauthenticated_page
    page.set_content('<main><article data-layout-card="booking" style="width:220px;height:80px">'
                     'Contained booking</article><div style="position:fixed;left:-140px;top:120px;width:180px">'
                     '<button>Important action</button></div></main>')
    evidence = measure_layout(page)
    assert evidence["documentWidth"] <= evidence["viewport"]["width"] + 1
    assert evidence["viewportOutsideCount"] > 0
    assert evidence["cardViolationCount"] == 0
    with pytest.raises(AssertionError, match="outside viewport"):
        assert_layout_contained(evidence)


def test_intentional_scroll_is_allowed_but_escaping_container_is_not(unauthenticated_page):
    page = unauthenticated_page
    page.set_viewport_size({"width": 390, "height": 844})
    page.set_content('<main><div data-calendar-scroll style="width:300px;overflow-x:auto">'
                     '<section style="display:flex;width:900px">'
                     '<article data-layout-card="booking" style="width:200px;flex-shrink:0">A</article>'
                     '<article data-layout-card="booking" style="width:200px;flex-shrink:0;margin-left:400px">B</article>'
                     '</section></div></main>')
    options = dict(intentional_scroll_selectors=('[data-calendar-scroll]',))
    evidence = measure_layout(page, **options)
    assert evidence["intentionalViewportOutside"]
    assert_layout_contained(evidence)
    page.locator('[data-calendar-scroll]').evaluate("e => e.style.width = '500px'")
    with pytest.raises(AssertionError):
        assert_layout_contained(measure_layout(page, **options))


def test_empty_selector_is_not_zero_violations_pass(unauthenticated_page):
    page = unauthenticated_page
    page.set_content('<main><article data-layout-card="customer-package">A package</article></main>')
    missing = measure_layout(page)
    assert missing["measurementStatus"] == "no-targets"
    assert missing["cardCount"] == 0
    with pytest.raises(AssertionError, match="No layout target"):
        assert_layout_contained(missing)
    measured = measure_layout(page, card_selector='[data-layout-card="customer-package"]')
    assert measured["measurementStatus"] == "measured"
    assert measured["cardCount"] == 1
    assert_layout_contained(measured)


def test_vertical_scroll_exemption_does_not_hide_horizontal_or_nested_clipping(unauthenticated_page):
    page = unauthenticated_page
    page.set_content('<main><article data-layout-card="modal" style="width:250px;height:100px;overflow-y:auto">'
                     '<div style="height:200px">Top</div><p>Reachable by scrolling</p>'
                     '</article></main>')
    options = dict(card_selector='[data-layout-card="modal"]',
                   intentional_vertical_scroll_selectors=('[data-layout-card="modal"]',))
    assert_layout_contained(measure_layout(page, **options))
    page.locator("p").evaluate("e => {e.style.whiteSpace = 'nowrap'; e.textContent = 'X'.repeat(100);}")
    with pytest.raises(AssertionError):
        assert_layout_contained(measure_layout(page, **options))
    page.locator("p").evaluate("e => {e.style.width='30px';e.style.overflow='hidden';e.textContent='Clipped content';}")
    evidence = measure_layout(page, **options)
    assert any(v["kind"] == "text-clipped" for c in evidence["cards"] for v in c["violations"])
