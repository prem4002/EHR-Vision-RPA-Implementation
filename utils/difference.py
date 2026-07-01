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

ROOT = Path(__file__).parent.parent


def _difference_calc(before_path, after_path, diff_path):
    before = Image.open(before_path).convert("RGB")
    after = Image.open(after_path).convert("RGB")

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
    amplified.save(diff_path)
    print(f"Diff image saved to {diff_path}")

def run(form="v1"):
    before_path = ROOT / "output" / f"screenshot_{form}.png"
    after_path = ROOT / "output" / f"screenshot_filled_{form}.png"
    diff_path = ROOT / "output" / f"screenshot_difference_{form}.png"
    _difference_calc(before_path, after_path, diff_path)

if __name__ == "__main__":
    run()