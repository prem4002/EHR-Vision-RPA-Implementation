"""
confirm the pipeline can open the dummy form and capture screenshot
No vision model, Groq, field mapping rn. Just open page and take screenshot

uv run python screenshot
"""

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

FORM_PATH = Path(__file__).parent / "site" / "intake_form.html"
OUTPUT_PATH = Path(__file__).parent / "output" / "screenshot.png"

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