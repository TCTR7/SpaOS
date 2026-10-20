import os
from urllib.parse import urlsplit
from typing import Generator
import pytest
from playwright.sync_api import Browser, Page, sync_playwright

from common_setup.api_helper import ApiHelper
from common_setup.auth_setup import (
    create_admin_authenticated_context,
    create_customer_pwa_authenticated_context,
)
from common_setup.config import config
from common_setup.frontend_preflight import FrontendPreflightError, verify_frontend


@pytest.fixture(scope="session", autouse=True)
def ensure_frontend_server() -> None:
    """Verify a runner-owned frontend; never start, stop or reuse another server."""
    try:
        verify_frontend(config.frontend_url, config.frontend_run_id)
    except FrontendPreflightError as error:
        pytest.fail(str(error), pytrace=False)


@pytest.fixture(scope="session")
def isolated_backend(ensure_frontend_server):
    # Explicit QA identities, independent of credentials in the user's .env.test.
    values = dict(backend_url=None, tenant_slug="spa-demo", admin_phone="0900000001",
                  admin_password="Admin@123", staff_phone="0900000011", staff_password="Staff@123",
                  customer_phone="0900000101", customer_password="Customer@123")
    if os.environ.get("SPAOS_QA_MANAGED") != "1":
        pytest.fail("Run E2E through python -m automation_test.run_ui_qa; no fallback backend.", pytrace=False)
    url = os.environ.get("SPAOS_QA_BACKEND_URL", "")
    try:
        origin = urlsplit(url)
        valid_origin = (origin.scheme == "http" and origin.hostname == "127.0.0.1"
                        and origin.port and origin.port not in (8000, 8001, 3000)
                        and not (origin.path or origin.query or origin.fragment
                                 or origin.username or origin.password))
    except ValueError:
        valid_origin = False
    if not valid_origin:
        pytest.fail("Runner backend must be a disposable loopback origin.", pytrace=False)
    values["backend_url"] = url
    previous = {key: getattr(config, key) for key in values}
    try:
        for key, value in values.items():
            object.__setattr__(config, key, value)
        yield url
    finally:
        for key, value in previous.items():
            object.__setattr__(config, key, value)


@pytest.fixture(scope="session")
def api_helper(isolated_backend) -> Generator[ApiHelper, None, None]:
    helper = ApiHelper()
    try:
        yield helper
    finally:
        helper.close()


@pytest.fixture(scope="session")
def browser_instance(pytestconfig: pytest.Config, isolated_backend) -> Generator[Browser, None, None]:
    headed_flag = bool(pytestconfig.getoption("--headed", default=False))
    slowmo_opt = pytestconfig.getoption("--slowmo", default=0)
    is_headless = False if headed_flag else config.headless
    slow_mo_ms = int(slowmo_opt) if slowmo_opt else config.slow_mo

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=is_headless, slow_mo=slow_mo_ms)
        try:
            yield browser
        finally:
            browser.close()


@pytest.fixture()
def unauthenticated_page(browser_instance: Browser) -> Generator[Page, None, None]:
    context = browser_instance.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    try:
        yield page
    finally:
        context.close()


@pytest.fixture()
def admin_page(
    browser_instance: Browser, api_helper: ApiHelper
) -> Generator[Page, None, None]:
    context, page = create_admin_authenticated_context(browser_instance, api_helper)
    try:
        yield page
    finally:
        context.close()


@pytest.fixture()
def customer_pwa_page(
    browser_instance: Browser, api_helper: ApiHelper
) -> Generator[Page, None, None]:
    context, page = create_customer_pwa_authenticated_context(
        browser_instance, api_helper
    )
    try:
        yield page
    finally:
        context.close()
