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

ROOT = Path(__file__).parent.parent


def _visualise(screenshot_path, detection_path, output_path):
    detections = json.loads(detection_path.read_text())
    img = Image.open(screenshot_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    for d in detections:
        box = d.get("bbox") or {}
        x, y, w, h = box.get("x", 0), box.get("y", 0), box.get("w", 0), box.get("h", 0)
        conf = d.get("confidence", 0.0) or 0.0

        color = "green" if conf >= 0.85 else ("orange" if conf >= 0.5 else "red")
        draw.rectangle([x, y, x + w, y + h], outline=color, width=3)
        draw.text((x, max(0, y - 14)), f"{d.get('label', '?')} ({conf:.2f})", fill=color)

    img.save(output_path)
    print(f"Annotated image saved to {output_path}")

def run(form="v1"):
    screenshot_path = ROOT / "output" / f"screenshot_{form}.png"
    detection_path = ROOT / "output" / f"detection_{form}.json"
    output_path = ROOT / "output" / f"annotated_detection_{form}.png"
    _visualise(screenshot_path, detection_path, output_path)

if __name__ == "__main__":
    run()