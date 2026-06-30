"""
v2 of day1_screenshot.py — ONLY the FORM_PATH and OUTPUT_PATH constants
differ from the original. No logic changes. That's the demo: the same
screenshotting code works on a form it has never seen before.

Run with: uv run python screenshot_v2.py
"""

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

FORM_PATH = Path(__file__).parent / "site" / "intake_form_v2.html"   # <-- only change
OUTPUT_PATH = Path(__file__).parent / "output" / "screenshot_v2.png"  # <-- only change


async def main():
    form_url = f"file://{FORM_PATH.resolve()}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        await page.goto(form_url)
        await page.wait_for_load_state("networkidle")

        await page.screenshot(path=str(OUTPUT_PATH))
        print(f"Screenshot saved to: {OUTPUT_PATH}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())