"""
confirm the pipeline can open the dummy form and capture screenshot
No vision model, Groq, field mapping rn. Just open page and take screenshot

uv run python screenshot
"""

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).parent.parent
FORMS = {
    "v1": ROOT / "site" / "intake_form_v1.html",
    "v2": ROOT / "site" / "intake_form_v2.html",
}

async def _capture(form_path, output_path):
    form_url = f"file://{form_path.resolve()}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        await page.goto(form_url)
        await page.wait_for_load_state("networkidle")

        await page.screenshot(path=str(output_path))
        print(f"Screenshot saved to: {output_path}")

        await browser.close()

def run(form="v1"):
    form_path = FORMS[form]
    output_path = ROOT / "output" / f"screenshot_{form}.png"
    asyncio.run(_capture(form_path, output_path))

if __name__ == "__main__":
    run()