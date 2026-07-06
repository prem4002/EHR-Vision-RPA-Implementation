"""
map the synthetic patient record onto detected fields and fill the
live form via Playwright. Uses two-threshold confidence gating (Section 6.2
style) high confidence -> auto-fill, mid confidence -> ask a human at the
console, low confidence -> discard

Coordinates from vision are imprecise by nature — rather than trusting the box itself, we use its center
point only to ask the browser "what DOM element is here?" (Section
9.2's vision-locates / DOM-executes pattern in the doc). This absorbs a lot of the
sloppiness in the boxes for free.

run with: uv run python fill.py
"""

import asyncio
import difflib
import json
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).parent.parent
FORMS = {
    "v1": ROOT / "site" / "intake_form_v1.html",
    "v2": ROOT / "site" / "intake_form_v2.html",
}
PATIENT_PATH = ROOT / "data" / "patient.json"

ACT_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.5

# Deterministic rule map: source patient.json key -> exact label text on
# this form. Checked first because it's free and certain (Section 10.1's
# "rule-based mapping checked first, AI fallback second" pattern) — fuzzy
# matching only kicks in for anything a label doesn't match exactly.
# This is hard coded data which is for the PoC, it will be changed with fuzzy 
# logic later on
LABEL_RULES = {
    "patient_name": "Patient Name",
    "dob": "Date of Birth",
    "sex": "Sex",
    "insurance_id": "Insurance ID",
    "address": "Address",
    "phone": "Phone Number",
}

#Here label is assumed to have the attribute's name
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

# for get element_at_point to get the box position
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

    # elementFromPoint can land on a <label> or a <div> wrapper instead of
    # the actual input — especially when the vision model's bbox center sits
    # slightly high and hits the label above the field. Resolve upward:
    # 1. label with a 'for' attr  → getElementById(for) is the exact input
    # 2. anything else non-fillable → search the nearest container for an input
    if tag not in ("input", "select", "textarea"):
        element = (await page.evaluate_handle(
            """([x, y]) => {
                const el = document.elementFromPoint(x, y);
                if (el.tagName.toLowerCase() === 'label' && el.htmlFor) {
                    return document.getElementById(el.htmlFor);
                }
                const container = el.closest('div, form, fieldset') || el.parentElement;
                return container ? container.querySelector('input, select, textarea') : null;
            }""",
            [cx, cy],
        )).as_element()

        if element is None:
            print(f"    !! Could not resolve to a fillable element at ({cx:.0f},{cy:.0f}) — skipping")
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
    """Re-read whatever is actually in a field right now, via the DOM —
    not from the vision model, not from what we tried to fill. This is
    the 'reread the field value' half of Section 7's verification engine.
    """
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


async def _fill(form_path, detection_path, screenshot_path):
    patient = json.loads(PATIENT_PATH.read_text())
    detections = json.loads(detection_path.read_text())
    form_url = f"file://{form_path.resolve()}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        await page.goto(form_url)
        await page.wait_for_load_state("networkidle")

        for key, value in patient.items():
            target_label = LABEL_RULES.get(key)
            #debug
            if not target_label:
                print(f"[skip] '{key}' has no mapping rule — full system would fall back to AI semantic match here")
                continue

            detection, map_confidence = find_detection_by_label(detections, target_label)
            #debug
            if detection is None:
                print(f"[escalate] '{key}' -> no detection found for label '{target_label}'")
                continue

            det_confidence = detection.get("confidence", 0.0) or 0.0
            combined_confidence = min(map_confidence, det_confidence)

            print(f"\n{key} -> '{target_label}'  (map={map_confidence:.2f}, detect={det_confidence:.2f})")

            if combined_confidence >= ACT_THRESHOLD:
                ok = await fill_field(page, detection, value)
                #debug
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

        # --- Verification: re-read what's actually in each field and
        # compare to what we expected to put there. This catches the case
        # where a fill silently landed on the wrong element, or didn't
        # take at all — the script believing it "auto-filled" something
        # is not the same as it actually being correct on screen.
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
            print(f"\n{len(mismatches)} field(s) failed verification — would route to human review queue in production")
        else:
            print("\nAll fields verified successfully")

        # Final action: click Save. Not part of patient.json data, but the
        # natural last sub-goal of a demographics-entry task.
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

        await page.screenshot(path=str(screenshot_path))
        print(f"\nFinal screenshot saved to {screenshot_path}")

        await browser.close()

def run(form="v1"):
    form_path = FORMS[form]
    screenshot_path = ROOT / "output" / f"screenshot_filled_{form}.png"
    detection_path = ROOT / "output" / f"detection_{form}.json"
    asyncio.run(_fill(form_path, detection_path, screenshot_path))

if __name__ == "__main__":
    run()