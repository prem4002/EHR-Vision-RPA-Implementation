"""
Renders an HTML string in a headless Chromium browser, takes a screenshot,
and extracts ground-truth bounding boxes from every element that carries a
data-widget-class attribute.

This replaces manual annotation entirely for the synthetic data slice —
the browser knows exactly where it rendered every element, so we just ask it.
"""

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

VIEWPORT_W = 1280
VIEWPORT_H = 800


async def _render(html_content: str, output_image_path: Path) -> list[dict]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": VIEWPORT_W, "height": VIEWPORT_H})

        # set_content is faster than goto for inline HTML — no network round trip
        await page.set_content(html_content, wait_until="networkidle")
        await page.screenshot(path=str(output_image_path))

        # query every element with a data-widget-class attribute and read
        # its rendered position directly from the browser's layout engine —
        # this is pixel-perfect ground truth, no human annotation needed
        annotations = await page.evaluate("""() => {
            const els = document.querySelectorAll('[data-widget-class]');
            const results = [];

            for (const el of els) {
                const rect = el.getBoundingClientRect();

                // skip elements with no rendered size (e.g. hidden tab content)
                if (rect.width === 0 || rect.height === 0) continue;

                // skip elements entirely outside the viewport
                if (rect.right <= 0 || rect.bottom <= 0) continue;
                if (rect.left >= 1280 || rect.top >= 800) continue;

                // clip to viewport so no annotation extends past the image edge
                const x = Math.max(0, Math.round(rect.left));
                const y = Math.max(0, Math.round(rect.top));
                const w = Math.min(Math.round(rect.width),  1280 - x);
                const h = Math.min(Math.round(rect.height), 800  - y);

                results.push({
                    widget_class: el.getAttribute('data-widget-class'),
                    bbox: { x, y, w, h }
                });
            }
            return results;
        }""")

        await browser.close()
        return annotations


def render(html_content: str, output_image_path: Path) -> list[dict]:
    """
    Synchronous wrapper — renders html_content, saves screenshot to
    output_image_path, returns list of {widget_class, bbox} dicts.
    """
    return asyncio.run(_render(html_content, output_image_path))
