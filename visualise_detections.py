"""
this code is like a debug helper — this draws the detections as boxes on top of the
screenshot so you can eyeball whether the model's bounding boxes
actually line up with the real fields. This matters more than it sounds:
vision-LLM bbox coordinates can look plausible in the JSON and still be
visually wrong, and the JSON alone won't tell you that.

run with: uv run python visualize_detections.py
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw

SCREENSHOT_PATH = Path(__file__).parent / "output" / "screenshot_v2.png"
DETECTIONS_PATH = Path(__file__).parent / "output" / "detections_v2.json"
OUTPUT_PATH = Path(__file__).parent / "output" / "annotated_detections_v2.png"


def main():
    detections = json.loads(DETECTIONS_PATH.read_text())
    img = Image.open(SCREENSHOT_PATH).convert("RGB")
    draw = ImageDraw.Draw(img)

    for d in detections:
        box = d.get("bbox") or {}
        x, y, w, h = box.get("x", 0), box.get("y", 0), box.get("w", 0), box.get("h", 0)
        conf = d.get("confidence", 0.0) or 0.0

        color = "green" if conf >= 0.85 else ("orange" if conf >= 0.5 else "red")
        draw.rectangle([x, y, x + w, y + h], outline=color, width=3)
        draw.text((x, max(0, y - 14)), f"{d.get('label', '?')} ({conf:.2f})", fill=color)

    img.save(OUTPUT_PATH)
    print(f"Annotated image saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()