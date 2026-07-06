# PoC Documentation

**Project:** EHR Vision-Based RPA Proof of Concept  
**Status:**  
**Stack:** Python 3.11, Playwright, Groq API (Llama 4 Scout Vision)

---

## What the PoC demonstrates

**The core thesis:** a pipeline that detects form fields visually and fills them correctly, surviving a genuine UI layout change that would break a selector-based bot.

Concretely, the pipeline:

- Takes a screenshot of a web form
- Sends it to a vision LLM with a structured prompt, receives back field labels, types, bounding boxes, and confidence scores — no HTML read
- Maps a patient data record onto the detected fields using label matching
- Uses each field's approximate screen location to resolve the exact DOM element via `document.elementFromPoint()`, then fills it via Playwright
- Applies two-threshold confidence gating — auto-fills high-confidence fields, pauses for human review on uncertain ones, discards anything below the minimum threshold
- Re-reads every filled field from the DOM after filling and compares against the expected value
- Takes a final screenshot and produces a pixel diff against the pre-fill state

The pipeline is run against two form versions. v1 is a simple single-column layout. v2 is a two-column grid with completely different field order and renamed HTML IDs and name attributes — simulating what a vendor portal looks like after a redesign. The pipeline fills both correctly using the same code with no configuration change, because it relies on visible label text rather than HTML internals.

---

## Pipeline stages

**1. Screenshot** — `scripts/screenshot.py`

Playwright opens the target HTML form in a headless Chromium browser at a fixed 1280×800 viewport and captures a PNG screenshot. The viewport is fixed because the vision model is told the image dimensions upfront — coordinates it returns must match the actual rendered layout.

**2. Detect** — `scripts/detect.py`

The screenshot is base64-encoded and sent to Groq's vision API. A structured prompt instructs the model to return a JSON array of detected form elements, each with a label, type (TEXT_FIELD, DROPDOWN, BUTTON, etc.), bounding box in pixel coordinates, and a confidence score. The response is stripped of any markdown formatting and parsed. Results are cached to disk so subsequent runs don't re-call the API.

**3. Fill** — `scripts/fill.py`

For each field in the patient record, a rule map translates the data key to the expected visible label on the form. The matching function finds the detection with that label — exact match first, fuzzy match (difflib) as fallback, returning a match confidence score. The combined confidence (min of map confidence and detection confidence) determines the action:

- ≥ 0.85 — auto-fill
- 0.50 – 0.84 — pause for human confirmation at the console
- < 0.50 — discard, do not fill

Filling uses `document.elementFromPoint()` at the bbox center to resolve the actual DOM element, with a recovery fallback for when the point lands on a label or wrapper div instead of the input. After all fields are processed, every field is re-read from the DOM and compared against the expected value. Mismatches are reported.

**4. Visualise** — `utils/visualise_detections.py` (optional, `--visualise`)

Draws the detected bounding boxes onto the screenshot using Pillow. Green for confidence ≥ 0.85, orange for ≥ 0.50, red for below. Used to visually confirm the model's detections are landing on the right elements.

**5. Diff** — `utils/difference.py` (optional, `--diff`)

Pixel-level comparison between the pre-fill and post-fill screenshots using Pillow's `ImageChops.difference`. Detects whether anything visually changed on screen. This is a separate verification from the DOM re-read — it catches the case where a fill operation returned success but the value never rendered visually (detached element, hidden field, JavaScript validation blocking the update).

---

## Sample output — v1

```
Screenshot saved to: output/screenshot_v1.png
Saved 7 detections to output/detection_v1.json

  [1.00] TEXT_FIELD   'Patient Name'    bbox={'x': 302, 'y': 175, 'w': 639, 'h': 30}
  [1.00] TEXT_FIELD   'Date of Birth'   bbox={'x': 302, 'y': 244, 'w': 639, 'h': 30}
  [1.00] DROPDOWN     'Sex'             bbox={'x': 302, 'y': 313, 'w': 639, 'h': 30}
  [1.00] TEXT_FIELD   'Insurance ID'    bbox={'x': 302, 'y': 382, 'w': 639, 'h': 30}
  [1.00] TEXT_FIELD   'Address'         bbox={'x': 302, 'y': 451, 'w': 639, 'h': 30}
  [1.00] TEXT_FIELD   'Phone Number'    bbox={'x': 302, 'y': 520, 'w': 639, 'h': 30}

patient_name → 'Patient Name'   (map=1.00, detect=1.00)  auto-filled
dob          → 'Date of Birth'  (map=1.00, detect=1.00)  auto-filled
sex          → 'Sex'            (map=1.00, detect=1.00)  auto-filled
insurance_id → 'Insurance ID'   (map=1.00, detect=1.00)  auto-filled
address      → 'Address'        (map=1.00, detect=1.00)  auto-filled
phone        → 'Phone Number'   (map=1.00, detect=1.00)  auto-filled

--- Verification ---
  [OK] patient_name: expected='Jane A. Doe'                            actual='Jane A. Doe'
  [OK] dob:          expected='01/15/1990'                             actual='01/15/1990'
  [OK] sex:          expected='F'                                      actual='F'
  [OK] insurance_id: expected='INS-77234901'                           actual='INS-77234901'
  [OK] address:      expected='412 Maple Street, Springfield, IL 62704' actual='412 Maple Street, Springfield, IL 62704'
  [OK] phone:        expected='555-201-3344'                           actual='555-201-3344'

All fields verified successfully
Changed region: (400, 169, 880, 583) — Changed pixels: 5856
```

---

## Sample output — v2 (relayouted form, renamed HTML IDs)

The v2 form has a two-column grid layout, reversed field order, and completely renamed HTML `id` and `name` attributes. A selector-based bot would fail on every field. The vision pipeline fills all fields correctly, with the Sex dropdown triggering the human review gate at 0.80 confidence.

```
  [0.90] TEXT_FIELD   'Phone Number'   ← moved to top of form
  [0.90] TEXT_FIELD   'Address'
  [0.90] TEXT_FIELD   'Insurance ID'
  [0.80] DROPDOWN     'Sex'            ← lower confidence on two-column layout
  [0.90] TEXT_FIELD   'Date of Birth'
  [0.90] TEXT_FIELD   'Patient Name'   ← moved to bottom of form

sex → 'Sex'  (map=1.00, detect=0.80)
  Confidence 0.80 is in the review band. Fill 'Sex' with 'F'? (y/n): y
  filled after human approval

All fields verified successfully
Save clicked
```

---

## Known limitations

**Bounding box instability**

The vision model produces slightly different bounding box coordinates on every run for the same form. This is expected — vision LLMs generate coordinates as language tokens without a dedicated regression head, and floating-point execution order on GPUs introduces small run-to-run differences. The DOM-snap (`document.elementFromPoint`) absorbs this imprecision, but it means raw bounding box coordinates cannot be trusted as stable values.

**Label-only field matching**

`find_detection_by_label` matches exclusively on visible label text. Forms where fields are identified by placeholder text, `aria-label`, or `name` attributes only — with no visible label — will not match. This is the most significant limitation for real EHR forms where labels are sometimes asterisks, icons, or absent entirely.

**Overconfident model scores**

The vision model reports `1.00` confidence on most detections, including ones where bounding boxes are imprecise. Confidence scores from this model are not calibrated and should not be used as a reliable accuracy signal. They are useful as a rough soft gate but the DOM re-read verification is the real correctness check.

**Single workflow, synthetic data**

The PoC covers one workflow (demographics entry) against one synthetic patient record. No real EHR, no real patient data, no API integration.

**No audit log**

Actions taken are printed to the console only. Production use in a healthcare context requires an immutable per-run audit log recording timestamp, patient ID, each field filled, verification result, and any human review decisions.

---

## What would be improved next

**Attribute-enriched field matching**

After visual detection, resolve each detected field's DOM element and extract its HTML attributes — `placeholder`, `aria-label`, `name`, `id`, `title`. Match against all of these with a priority order, not just visible label text. This makes the pipeline viable on real EHR forms where visible labels are missing or ambiguous.

**Source API integration**

Replace `patient.json` with a live fetch from a source system (EHR API, insurance eligibility API). Add a normalisation layer to transform the API's schema (split name fields, ISO dates, unformatted phone numbers) into the pipeline's expected format. Extend verification to compare DOM values against the original API response, not just what was attempted — this catches normalisation bugs that would otherwise pass silently.

**Audit logging**

Write a structured JSON log per run to `output/audit/`. Each entry records timestamp, form version, patient identifier, each field's expected value, actual DOM value, confidence scores, and human review decisions. Required for any real healthcare deployment.

**Composite field handling**

Some EHR date fields split into three separate inputs (month, day, year) inside one container. The current `querySelector` fallback always picks the first input, which would fill only the month. Detect composite fields during the enrich step and split the data value accordingly before filling.

**Trained vision model replacement**

Replace the vision LLM with a dedicated detection model (ViT backbone + DETR detection head) trained on annotated EHR screenshots. This eliminates bounding box instability, reduces cost per page from an LLM API call to a fast local inference pass, and produces calibrated confidence scores. This is the full Phase 1–4 roadmap from the architecture document — months of work, not appropriate for PoC scope.

**Real EHR sandbox testing**

Validate the pipeline against a sandbox instance of Epic or athenahealth. The dummy forms prove the concept; real EHR forms have additional complexity — JavaScript-driven field validation, dynamic field visibility, session authentication, multi-page workflows — that the PoC does not cover.