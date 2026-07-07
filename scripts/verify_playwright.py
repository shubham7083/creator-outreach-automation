from __future__ import annotations

import asyncio

from playwright.async_api import async_playwright


async def main() -> None:
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    await browser.close()
    await playwright.stop()
    print("playwright chromium ok")


if __name__ == "__main__":
    asyncio.run(main())
