"""
Synthetic dataset generator for EHR Vision RPA.

Generates randomised HTML forms, renders each one headlessly via Playwright,
auto-extracts ground-truth bounding boxes from the DOM (zero manual annotation),
and writes a COCO-format dataset ready for DETR fine-tuning.

Usage:
    uv run generate_dataset.py --count 1000 --output synthetic_data/output
    uv run generate_dataset.py --count 50 --output synthetic_data/output --seed 42
"""

import argparse
from pathlib import Path

from synthetic_data.form_builder import build_random_config, generate_form
from synthetic_data.renderer import render
from synthetic_data.coco_writer import COCODataset


def main():
    parser = argparse.ArgumentParser(
        description="EHR Vision RPA — synthetic dataset generator"
    )
    parser.add_argument(
        "--count", type=int, default=100,
        help="Number of screenshots to generate (default: 100)"
    )
    parser.add_argument(
        "--output", type=str, default="synthetic_data/output",
        help="Output directory (default: synthetic_data/output)"
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility (optional)"
    )
    args = parser.parse_args()

    if args.seed is not None:
        import random
        random.seed(args.seed)
        print(f"Random seed set to {args.seed}")

    output_dir = Path(args.output)
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    dataset = COCODataset()
    failed  = 0

    print(f"Generating {args.count} forms → {output_dir}/\n")

    for i in range(args.count):
        config   = build_random_config()
        html     = generate_form(config)
        filename = f"form_{i:05d}.png"
        img_path = images_dir / filename

        try:
            annotations = render(html, img_path)
        except Exception as e:
            print(f"  [WARN] form_{i:05d} failed to render: {e}")
            failed += 1
            continue

        image_id = dataset.add_image(filename)
        for ann in annotations:
            dataset.add_annotation(image_id, ann["widget_class"], ann["bbox"])

        if (i + 1) % 25 == 0 or (i + 1) == args.count:
            print(f"  {i + 1}/{args.count} generated "
                  f"({dataset._ann_id} annotations so far)")

    dataset.save(output_dir / "dataset.json")

    if failed:
        print(f"\n{failed} form(s) failed to render and were skipped.")


if __name__ == "__main__":
    main()
