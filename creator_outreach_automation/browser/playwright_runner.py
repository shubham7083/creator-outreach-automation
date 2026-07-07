from __future__ import annotations

import logging
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from playwright.async_api import Browser, async_playwright

from creator_outreach_automation.config import PlaywrightSettings

logger = logging.getLogger(__name__)


class PlaywrightBrowserRunner:
    def __init__(self, settings: PlaywrightSettings) -> None:
        self._settings = settings

    @asynccontextmanager
    async def browser(self) -> AsyncIterator[Browser]:
        logger.info("Launching Playwright browser headless=%s", self._settings.headless)
        async with async_playwright() as playwright:
            launch_options: dict[str, object] = {
                "headless": self._settings.headless,
                "args": ["--no-sandbox", "--disable-dev-shm-usage"],
            }
            executable = self._chromium_executable()
            if executable:
                launch_options["executable_path"] = str(executable)
            browser = await playwright.chromium.launch(**launch_options)
            try:
                yield browser
            finally:
                await browser.close()

    def _chromium_executable(self) -> Path | None:
        if self._settings.chromium_executable and self._settings.chromium_executable.exists():
            return self._settings.chromium_executable
        for candidate in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
            resolved = shutil.which(candidate)
            if resolved:
                return Path(resolved)
        return None
