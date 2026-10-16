from playwright.sync_api import Page, expect

from common_setup.api_helper import ApiHelper, random_phone, unique_suffix
from common_setup.config import config
from features.client_pwa_booking.pages.tenant_home_page import TenantHomePage


def test_multi_tenant_ui_isolation_between_spas(
    unauthenticated_page: Page, api_helper: ApiHelper
) -> None:
    # Get a known service name from spa-demo
    demo_token = api_helper.get_admin_token(config.tenant_slug)
    demo_services = api_helper.list_services(demo_token)
    assert len(demo_services) > 0
    spa_demo_service_name = demo_services[0]["name"]

    # Create a second independent tenant via API
    suffix = unique_suffix().replace("_", "-")
    spa2_slug = f"spa-lotus-{suffix}"
    spa2_name = f"Lotus Luxury Spa {suffix}"
    spa2_service_name = f"Gội Đầu Dưỡng Sinh Lotus {suffix}"

    reg_res = api_helper.register_tenant(
        tenant_name=spa2_name,
        tenant_slug=spa2_slug,
        admin_full_name="Chủ Spa Lotus",
        phone_number=random_phone("093"),
    )
    spa2_token = reg_res["access_token"]
    api_helper.create_service(
        spa2_token,
        name=spa2_service_name,
        duration_minutes=50,
        price=280000,
    )

    # Open /[spa2_slug] and verify only Spa 2 branding & service are shown, never spa-demo's
    home = TenantHomePage(unauthenticated_page)
    home.open_tenant(spa2_slug)
    home.wait_for_text(spa2_name)
    home.wait_for_text(spa2_service_name)

    expect(
        unauthenticated_page.get_by_text(spa_demo_service_name)
    ).to_have_count(0)
