from typing import Optional
from playwright.sync_api import Browser, BrowserContext, Page

from common_setup.api_helper import ApiHelper
from common_setup.config import config


def create_admin_authenticated_context(
    browser: Browser, api_helper: ApiHelper
) -> tuple[BrowserContext, Page]:
    """Create a Desktop (1440x900) BrowserContext pre-authenticated as Spa Admin."""
    token = api_helper.get_admin_token(config.tenant_slug)
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    context.add_init_script(
        f"""
        window.localStorage.setItem('spaos_admin_token', '{token}');
        window.localStorage.setItem('spaos_admin_slug', '{config.tenant_slug}');
        """
    )
    page = context.new_page()
    return context, page


def create_customer_pwa_authenticated_context(
    browser: Browser, api_helper: ApiHelper, tenant_slug: Optional[str] = None
) -> tuple[BrowserContext, Page]:
    """Create a Mobile-first (390x844) BrowserContext pre-authenticated as Customer on /[tenant_slug]."""
    slug = (tenant_slug or config.tenant_slug).lower()
    token = api_helper.get_customer_token(slug)
    context = browser.new_context(
        viewport={"width": 390, "height": 844},
        is_mobile=True,
        has_touch=True,
    )
    context.add_init_script(
        f"""
        window.localStorage.setItem('spaos_customer_token_{slug}', '{token}');
        """
    )
    page = context.new_page()
    return context, page
