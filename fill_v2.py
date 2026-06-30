"""
v2 of day3_fill.py — ONLY the path constants at the top differ.
LABEL_RULES is UNCHANGED: it maps to visible label text, and the label
text is the one thing we deliberately kept identical between v1 and v2.
Everything else — mapping function, DOM-snap, fill, verification,
confidence gating — is byte-for-byte the same code.

Run with: uv run python fill_v2.py
"""

import asyncio
import difflib
import json
from pathlib import Path

from playwright.async_api import async_playwright

FORM_PATH = Path(__file__).parent / "site" / "intake_form_v2.html"        # <-- only change
DETECTIONS_PATH = Path(__file__).parent / "output" / "detections_v2.json"   # <-- only change
PATIENT_PATH = Path(__file__).parent / "site" / "patient.json"
RESULT_SCREENSHOT = Path(__file__).parent / "output" / "screenshot_v2_filled.png"  # <-- only change

ACT_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.5

# Unchanged from v1 — these are the visible labels, not IDs or positions.
LABEL_RULES = {
    "patient_name": "Patient Name",
    "dob": "Date of Birth",
    "sex": "Sex",
    "insurance_id": "Insurance ID",
    "address": "Address",
    "phone": "Phone Number",
}


def find_detection_by_label(detections, target_label):
    for d in detections:
        if d.get("label", "").strip().lower() == target_label.strip().lower():
            return d, 1.0
    labels = [d.get("label", "") for d in detections]
    matches = difflib.get_close_matches(target_label, labels, n=1, cutoff=0.0)
    if matches:
        best_label = matches[0]
        score = difflib.SequenceMatcher(None, target_label.lower(), best_label.lower()).ratio()
        for d in detections:
            if d.get("label", "") == best_label:
                return d, score
    return None, 0.0


async def get_element_at_point(page, x, y):
    handle = await page.evaluate_handle("([x, y]) => document.elementFromPoint(x, y)", [x, y])
    return handle.as_element()


def bbox_center(detection):
    box = detection.get("bbox") or {}
    cx = box.get("x", 0) + box.get("w", 0) / 2
    cy = box.get("y", 0) + box.get("h", 0) / 2
    return cx, cy


async def fill_field(page, detection, value):
    cx, cy = bbox_center(detection)
    element = await get_element_at_point(page, cx, cy)
    if element is None:
        print(f"    !! No DOM element found at ({cx:.0f},{cy:.0f}) — skipping")
        return False

    tag = await element.evaluate("el => el.tagName.toLowerCase()")
    if tag == "select":
        try:
            await element.select_option(value=str(value))
        except Exception:
            await element.select_option(label=str(value))
    else:
        await element.fill(str(value))
    return True


async def read_field_value(page, detection):
    cx, cy = bbox_center(detection)
    element = await get_element_at_point(page, cx, cy)
    if element is None:
        return None
    tag = await element.evaluate("el => el.tagName.toLowerCase()")
    if tag == "select":
        return await element.evaluate(
            "el => el.options[el.selectedIndex] ? el.options[el.selectedIndex].value : null"
        )
    return await element.evaluate("el => el.value")


async def main():
    patient = json.loads(PATIENT_PATH.read_text())
    detections = json.loads(DETECTIONS_PATH.read_text())
    form_url = f"file://{FORM_PATH.resolve()}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        await page.goto(form_url)
        await page.wait_for_load_state("networkidle")

        for key, value in patient.items():
            target_label = LABEL_RULES.get(key)
            if not target_label:
                print(f"[skip] '{key}' has no mapping rule")
                continue

            detection, map_confidence = find_detection_by_label(detections, target_label)
            if detection is None:
                print(f"[escalate] '{key}' -> no detection found for label '{target_label}'")
                continue

            det_confidence = detection.get("confidence", 0.0) or 0.0
            combined_confidence = min(map_confidence, det_confidence)

            print(f"\n{key} -> '{target_label}'  (map={map_confidence:.2f}, detect={det_confidence:.2f})")

            if combined_confidence >= ACT_THRESHOLD:
                ok = await fill_field(page, detection, value)
                print("  auto-filled" if ok else "  fill failed")
            elif combined_confidence >= REVIEW_THRESHOLD:
                answer = input(
                    f"  Confidence {combined_confidence:.2f} is in the review band. "
                    f"Fill '{target_label}' with '{value}'? (y/n): "
                )
                if answer.strip().lower() == "y":
                    ok = await fill_field(page, detection, value)
                    print("  filled after human approval" if ok else "  fill failed")
                else:
                    print("  skipped by human reviewer")
            else:
                print(f"  discarded (confidence {combined_confidence:.2f} below review threshold)")

        print("\n--- Verification ---")
        mismatches = []
        for key, value in patient.items():
            target_label = LABEL_RULES.get(key)
            if not target_label:
                continue
            detection, _ = find_detection_by_label(detections, target_label)
            if detection is None:
                continue

            actual = await read_field_value(page, detection)
            expected = str(value)
            match = actual is not None and actual.strip().lower() == expected.strip().lower()

            status = "OK" if match else "MISMATCH"
            print(f"  [{status}] {key}: expected='{expected}'  actual='{actual}'")
            if not match:
                mismatches.append((key, expected, actual))

        if mismatches:
            print(f"\n{len(mismatches)} field(s) failed verification")
        else:
            print("\nAll fields verified successfully")

        save_detection = next(
            (d for d in detections if d.get("type") == "BUTTON" and "save" in d.get("label", "").lower()),
            None,
        )
        if save_detection:
            conf = save_detection.get("confidence", 0.0) or 0.0
            print(f"\nSave button detected (confidence={conf:.2f})")
            proceed = conf >= ACT_THRESHOLD
            if REVIEW_THRESHOLD <= conf < ACT_THRESHOLD:
                proceed = input("  Confidence below act-threshold — click Save anyway? (y/n): ").strip().lower() == "y"
            if proceed:
                cx, cy = bbox_center(save_detection)
                element = await get_element_at_point(page, cx, cy)
                if element:
                    await element.click()
                    print("  Save clicked")
                else:
                    print("  !! No element found at Save's coordinates — falling back to raw point click")
                    await page.mouse.click(cx, cy)
            else:
                print("  Not clicking Save (confidence too low for this run)")
        else:
            print("\nNo Save button detected at all — skipping submit step")

        await page.screenshot(path=str(RESULT_SCREENSHOT))
        print(f"\nFinal screenshot saved to {RESULT_SCREENSHOT}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())