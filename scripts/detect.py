"""
send screenshot to vision model and get back field detections
(label, type, bounding box, confidence)

run with: uv run python detect.py
"""

import base64
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

ROOT = Path(__file__).parent.parent

IMG_WIDTH, IMG_HEIGHT = 1280, 800  # must match the viewport used in screenshot.py

# groq vision model. Model IDs on Groq are renamed/deprecated, have to be changed
# fairly often — if this one 404s, check https://console.groq.com/docs/models
# for the current vision-capable model and swap it in here.
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

ALLOWED_TYPES = ["TEXT_FIELD", "PASSWORD_FIELD", "DROPDOWN", "CHECKBOX", "RADIO_BUTTON", "BUTTON", "LINK"]

PROMPT = f"""You are analyzing a screenshot of a web form, {IMG_WIDTH}x{IMG_HEIGHT} pixels,
origin (0,0) at the top-left corner.

Identify EVERY interactive form element visible: text inputs, dropdowns,
checkboxes, radio buttons, and buttons. For each one, return:

- "label": the visible label text associated with it (e.g. "Date of Birth")
- "type": one of these values: {ALLOWED_TYPES}
- "bbox": {{"x": <int>, "y": <int>, "w": <int>, "h": <int>}} — pixel
  coordinates of the INPUT/CONTROL itself (not the label text), x/y is the
  top-left corner of the box
- "confidence": your confidence this detection is correct, 0.0 to 1.0

Respond with ONLY a raw JSON array of these objects. No markdown fences,
no commentary, no explanation before or after — just the JSON array.
"""


def encode_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


#to remove markdown features
def strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


def _detect(screenshot_path, output_path):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not found — check your .env file")

    if not screenshot_path.exists():
        raise RuntimeError(f"No screenshot found at {screenshot_path} — run day1_screenshot.py first")

    client = Groq(api_key=api_key)
    image_b64 = encode_image(screenshot_path)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                ],
            }
        ],
        temperature=0.0,
        max_tokens=2000,
    )

    raw_text = response.choices[0].message.content
    cleaned = strip_code_fences(raw_text)

    try:
        detections = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print("--- RAW MODEL OUTPUT (failed to parse as JSON) ---")
        print(raw_text)
        raise RuntimeError(f"Model did not return valid JSON: {e}")

    output_path.write_text(json.dumps(detections, indent=2))
    print(f"Saved {len(detections)} detections to {output_path}\n")

    for d in detections:
        conf = d.get("confidence", 0.0) or 0.0
        print(f"  [{conf:.2f}] {d.get('type', '?'):12s} '{d.get('label', '?')}'  bbox={d.get('bbox')}")

def run(form="v1"):
    screenshot_path = ROOT / "output" / f"screenshot_{form}.png"
    output_path = ROOT / "output" / f"detection_{form}.json"
    _detect(screenshot_path, output_path)

if __name__ == "__main__":
    run()