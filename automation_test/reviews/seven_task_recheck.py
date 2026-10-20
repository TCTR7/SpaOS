"""Compatibility entry point; regressions also run in the normal features suite."""
from features.customer_regressions.conftest import scenario
from features.admin_bookings.tests.test_calendar_loading import test_mutation_refreshes_current_scope
from reviews.test_mobile_controls import (
    test_selected_slot_secondary_text_uses_brand_foreground,
    test_package_copy_preserves_extra_charge,
)
from reviews.test_layout_measurements import test_layout_gate_rejects_unapproved_offscreen_content
