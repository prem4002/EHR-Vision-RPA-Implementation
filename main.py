import argparse
from scripts.screenshot import run as screenshot
from scripts.detect import run as detect
from scripts.fill import run as fill

FORMS = {
    "v1": "site/intake_form_v1.html",
    "v2": "site/intake_form_v2.html",
}

def main():
    parser = argparse.ArgumentParser(description="EHR Vision RPA — PoC pipeline")
    parser.add_argument("--form", choices=["v1", "v2"], default="v1")
    parser.add_argument("--visualise", action="store_true", help="annotate detections after detect step")
    parser.add_argument("--diff", action="store_true", help="run screenshot diff after fill step")
    args = parser.parse_args()

    form_path = FORMS[args.form]
    print(f"\n=== Running pipeline on {form_path} ===\n")

    screenshot(form=args.form)
    detect(form=args.form)

    if args.visualise:
        from utils.visualise_detections import run as visualise
        visualise(form=args.form)

    fill(form=args.form)

    if args.diff:
        from utils.difference import run as diff
        diff(form=args.form)

if __name__ == "__main__":
    main()