"""Scoped UI acceptance/calibration in the normal features test run.

Large artifact collectors remain explicit; completion is not a UI pass.
"""
from features.customer_regressions.conftest import scenario
from reviews.test_mobile_controls import (
    test_calendar_toolbar_fits_320px,
    test_login_controls_remain_readable,
    test_package_copy_preserves_extra_charge,
    test_selected_slot_secondary_text_uses_brand_foreground,
)
from reviews.test_layout_measurements import (
    test_closed_details_ignored_but_expanded_overflow_detected,
    test_empty_selector_is_not_zero_violations_pass,
    test_intentional_scroll_is_allowed_but_escaping_container_is_not,
    test_layout_gate_rejects_unapproved_offscreen_content,
    test_overlapping_text_inside_card_is_detected,
    test_vertical_scroll_exemption_does_not_hide_horizontal_or_nested_clipping,
)
from reviews.test_layout_regressions import (
    test_long_note_contained_in_mobile_calendar,
    test_week_cards_contained,
)
