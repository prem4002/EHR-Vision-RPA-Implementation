# EHR Vision RPA — PoC

A proof of concept that automates patient data entry into EHR web forms using computer vision instead of hardcoded DOM selectors. The pipeline visually detects form fields from a screenshot, maps patient data onto them, fills the form via Playwright, and verifies the values landed correctly — surviving UI layout changes that would break traditional RPA.

---

## Requirements

- Python 3.11
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — Python package manager
- A [Groq API key](https://console.groq.com) (free tier is sufficient)

---

## Setup

**1. Clone the repo and enter the directory**

```bash
git clone https://github.com/prem4002/EHR-Vision-RPA-Implementation
cd "directory/you/cloned/to"
```

**2. Install dependencies**

```bash
uv sync
```

**3. Install the Chromium browser Playwright will drive**

```bash
uv run playwright install chromium
```

**4. Add your Groq API key**

Copy the example env file:

Mac/Linux:
```bash
cp .env.example .env
```

Windows:
```bash
copy .env.example .env
```

Open `.env` and replace `your-key-here` with your actual Groq API key:

```
GROQ_API_KEY=gsk_...
```

**5. Create the output directory**

```bash
mkdir -p output
```

---

## Running the pipeline

The pipeline runs through `main.py`. Two form versions are available — `v1` is a simple single-column layout, `v2` is a two-column grid with scrambled field order and renamed HTML attributes, simulating a vendor relayout.

**Basic run:**

```bash
uv run main.py --form v1
```

**With bounding box visualisation (draws detected fields onto the screenshot):**

```bash
uv run main.py --form v1 --visualise
```

**With before/after screenshot diff (shows what pixels changed after filling):**

```bash
uv run main.py --form v1 --diff
```

**Full run with all outputs:**

```bash
uv run main.py --form v1 --visualise --diff
uv run main.py --form v2 --visualise --diff
```

---

## Output files

All outputs are written to the `output/` directory.

| File | Description |
|---|---|
| `screenshot_{form}.png` | Raw screenshot of the empty form before filling |
| `detection_{form}.json` | Structured field detections from the vision model |
| `annotated_detection_{form}.png` | Screenshot with detected bounding boxes drawn on (green ≥ 0.85, orange ≥ 0.5, red < 0.5) |
| `screenshot_filled_{form}.png` | Screenshot of the form after all fields have been filled |
| `screenshot_difference_{form}.png` | Amplified pixel diff between before and after screenshots |

---

## Project structure

```
├── data/
│   └── patient.json          # Synthetic patient record used for filling
├── scripts/
│   ├── screenshot.py          # Opens the form and captures a screenshot
│   ├── detect.py              # Sends screenshot to Groq vision model, returns field detections
│   └── fill.py                # Maps patient data to detected fields, fills and verifies
├── utils/
│   ├── visualise_detections.py  # Draws bounding boxes onto the screenshot for debugging
│   └── difference.py            # Pixel diff between before/after screenshots
├── site/
│   ├── intake_form_v1.html    # Dummy EHR form — simple single-column layout
│   └── intake_form_v2.html    # Dummy EHR form — two-column grid, scrambled field order, renamed HTML IDs
├── main.py                    # Pipeline orchestrator
├── .env.example               # Environment variable template
└── pyproject.toml             # Python dependencies (managed by uv)
```

---

## Notes

- Detection results are cached to `output/detection_{form}.json`. If you want a fresh detection run, delete that file before running.
- The Groq vision model ID is set in `scripts/detect.py` under `MODEL`. If you get a 404 error, check [console.groq.com/docs/models](https://console.groq.com/docs/models) for the current vision-capable model name and update it.
- Fields with confidence between 0.5 and 0.85 will pause and ask for a `y/n` confirmation in the terminal before filling. This is the human-in-the-loop gate.