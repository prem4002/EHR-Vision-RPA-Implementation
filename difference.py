"""
Day 4 (part 2) — before/after screenshot diff. The DOM re-read in
day3_fill.py confirms field VALUES are correct; this confirms something
actually visually changed on screen at all, which is a different failure
mode (e.g. a fill that "succeeded" against a detached/hidden element and
never rendered).

Run with: uv run python difference.py
"""

from pathlib import Path

from PIL import Image, ImageChops

BEFORE_PATH = Path(__file__).parent / "output" / "screenshot.png"
AFTER_PATH = Path(__file__).parent / "output" / "screenshot_filled.png"
DIFF_PATH = Path(__file__).parent / "output" / "screenshot_difference.png"


def main():
    before = Image.open(BEFORE_PATH).convert("RGB")
    after = Image.open(AFTER_PATH).convert("RGB")

    if before.size != after.size:
        raise RuntimeError(f"Size mismatch: before={before.size} after={after.size}")

    diff = ImageChops.difference(before, after)
    bbox = diff.getbbox()  # bounding box of all non-zero (changed) pixels, or None if identical

    if bbox is None:
        print("No visual difference detected between before and after — fill likely did not render")
        return

    changed_pixels = sum(1 for px in diff.getdata() if px != (0, 0, 0))
    print(f"Changed region: {bbox}")
    print(f"Changed pixels: {changed_pixels}")

    # Save an amplified diff image — small pixel differences (e.g. text)
    # are easy to miss at normal brightness, so we boost it for visibility.
    amplified = diff.point(lambda p: min(255, p * 4))
    amplified.save(DIFF_PATH)
    print(f"Diff image saved to {DIFF_PATH}")


if __name__ == "__main__":
    main()