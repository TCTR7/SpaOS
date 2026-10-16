import subprocess
import time
from pathlib import Path
from typing import Generator
import httpx
import pytest
from playwright.sync_api import Browser, Page, sync_playwright

from common_setup.api_helper import ApiHelper
from common_setup.auth_setup import (
    create_admin_authenticated_context,
    create_customer_pwa_authenticated_context,
)
from common_setup.config import BASE_DIR, config


def _is_frontend_up(url: str) -> bool:
    try:
        resp = httpx.get(url, timeout=10.0, follow_redirects=False)
        return resp.status_code < 500
    except Exception:
        return False


@pytest.fixture(scope="session", autouse=True)
def ensure_frontend_server() -> Generator[None, None, None]:
    """Automatically start Next.js server on port 3000 if not already running."""
    if _is_frontend_up(config.frontend_url):
        yield
        return

    frontend_dir = BASE_DIR.parent / "frontend"
    npm_cmd = "npm.cmd" if Path("C:/Windows").exists() else "npm"
    proc = subprocess.Popen(
        [npm_cmd, "run", "start"],
        cwd=str(frontend_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            if _is_frontend_up(config.frontend_url):
                break
            time.sleep(0.5)
        else:
            raise RuntimeError(
                f"Frontend did not start at {config.frontend_url} within 30s"
            )
        yield
    finally:
        if Path("C:/Windows").exists():
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()


@pytest.fixture(scope="session")
def api_helper() -> Generator[ApiHelper, None, None]:
    helper = ApiHelper()
    try:
        yield helper
    finally:
        helper.close()


@pytest.fixture(scope="session")
def browser_instance(pytestconfig: pytest.Config) -> Generator[Browser, None, None]:
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
