from pathlib import Path
from typing import Optional
from playwright.sync_api import Locator, Page, expect

from common_setup.config import BASE_DIR, config


class BasePage:
    """Base Page Object wrapping Playwright sync Page."""

    def __init__(self, page: Page, base_url: Optional[str] = None) -> None:
        self.page = page
        self.base_url = (base_url or config.frontend_url).rstrip("/")

    def navigate(self, path: str) -> None:
        url = path if path.startswith("http") else f"{self.base_url}/{path.lstrip('/')}"
        self.page.goto(url, wait_until="domcontentloaded")

    def fill_field(self, selector: str, value: str) -> None:
        locator = self.page.locator(selector).first
        locator.wait_for(state="visible", timeout=10000)
        locator.fill(value)

    def safe_click(self, selector: str) -> None:
        locator = self.page.locator(selector).first
        locator.wait_for(state="visible", timeout=10000)
        locator.click()

    def click_by_text(self, text: str, exact: bool = False) -> None:
        locator = self.page.get_by_text(text, exact=exact).first
        locator.wait_for(state="visible", timeout=10000)
        locator.click()

    def wait_for_text(self, text: str, timeout: int = 10000) -> Locator:
        locator = self.page.get_by_text(text).first
        expect(locator).to_be_visible(timeout=timeout)
        return locator

    def wait_for_url_contains(self, fragment: str, timeout: int = 10000) -> None:
        self.page.wait_for_url(f"**{fragment}**", timeout=timeout)

    def capture_screenshot(self, name: str) -> Path:
        screenshots_dir = BASE_DIR / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        target = screenshots_dir / f"{name}.png"
        self.page.screenshot(path=str(target), full_page=True)
        return target
