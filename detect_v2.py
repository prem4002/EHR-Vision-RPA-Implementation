"""
v2 of day2_detect.py — ONLY SCREENSHOT_PATH and OUTPUT_PATH differ.
Same prompt, same model, same parsing logic, same everything else.

Run with: uv run python detect_v2.py
"""

import base64
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

SCREENSHOT_PATH = Path(__file__).parent / "output" / "screenshot_v2.png"  # <-- only change
OUTPUT_PATH = Path(__file__).parent / "output" / "detections_v2.json"          # <-- only change

IMG_WIDTH, IMG_HEIGHT = 1280, 800

MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"  # update if Groq has deprecated this — check console.groq.com/docs/models

ALLOWED_TYPES = ["TEXT_FIELD", "PASSWORD_FIELD", "DROPDOWN", "CHECKBOX", "RADIO_BUTTON", "BUTTON", "LINK"]

PROMPT = f"""You are analyzing a screenshot of a web form, {IMG_WIDTH}x{IMG_HEIGHT} pixels,
origin (0,0) at the top-left corner.

Identify every interactive form element visible: text inputs, dropdowns,
checkboxes, radio buttons, and buttons. For each one, return:

- "label": the visible label text associated with it (e.g. "Date of Birth")
- "type": one of exactly these values: {ALLOWED_TYPES}
- "bbox": {{"x": <int>, "y": <int>, "w": <int>, "h": <int>}} — pixel
  coordinates of the INPUT/CONTROL itself (not the label text), x/y is the
  top-left corner of the box
- "confidence": your confidence this detection is correct, 0.0 to 1.0

Respond with ONLY a raw JSON array of these objects. No markdown fences,
no commentary, no explanation before or after — just the JSON array.
"""


def encode_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


def main():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not found — check your .env file")

    if not SCREENSHOT_PATH.exists():
        raise RuntimeError(f"No screenshot found at {SCREENSHOT_PATH} — run day1_screenshot_v2.py first")

    client = Groq(api_key=api_key)
    image_b64 = encode_image(SCREENSHOT_PATH)

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

    OUTPUT_PATH.write_text(json.dumps(detections, indent=2))
    print(f"Saved {len(detections)} detections to {OUTPUT_PATH}\n")

    for d in detections:
        conf = d.get("confidence", 0.0) or 0.0
        print(f"  [{conf:.2f}] {d.get('type', '?'):12s} '{d.get('label', '?')}'  bbox={d.get('bbox')}")


if __name__ == "__main__":
    main()