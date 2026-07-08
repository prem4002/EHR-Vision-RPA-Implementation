"""
Builds and saves a COCO-format object detection dataset.

COCO format is the standard for detection datasets and what Hugging Face's
DETR implementation expects. Three required sections:
  images      — one entry per screenshot
  annotations — one entry per widget instance (bbox + class)
  categories  — the fixed list of widget classes mapped to integer IDs
"""

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from core.taxonomy import WIDGET_CLASSES, CLASS_TO_IDX


class COCODataset:
    def __init__(self):
        self.images      = []
        self.annotations = []
        self._img_id  = 0
        self._ann_id  = 0

    def add_image(self, file_name: str,
                  width: int = 1280, height: int = 800) -> int:
        self._img_id += 1
        self.images.append({
            "id":        self._img_id,
            "file_name": file_name,
            "width":     width,
            "height":    height,
        })
        return self._img_id

    def add_annotation(self, image_id: int,
                       widget_class: str, bbox: dict) -> None:
        if widget_class not in CLASS_TO_IDX:
            return  # unknown class — skip rather than crash
        self._ann_id += 1
        x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
        self.annotations.append({
            "id":          self._ann_id,
            "image_id":    image_id,
            "category_id": CLASS_TO_IDX[widget_class],
            "bbox":        [x, y, w, h],   # COCO format: [x, y, width, height]
            "area":        w * h,
            "iscrowd":     0,
        })

    def save(self, output_path: Path) -> None:
        categories = [
            {"id": CLASS_TO_IDX[cls], "name": cls, "supercategory": "ui_widget"}
            for cls in WIDGET_CLASSES
        ]
        data = {
            "info": {
                "description":   "EHR Vision RPA — Synthetic UI Widget Dataset",
                "version":       "1.0",
                "year":          datetime.now().year,
                "date_created":  datetime.now().isoformat(),
            },
            "licenses":    [],
            "images":      self.images,
            "annotations": self.annotations,
            "categories":  categories,
        }
        output_path.write_text(json.dumps(data, indent=2))

        # summary
        print(f"\nDataset saved to {output_path}")
        print(f"  Images:       {len(self.images)}")
        print(f"  Annotations:  {len(self.annotations)}")
        counts = Counter(a["category_id"] for a in self.annotations)
        print("\n  Per-class counts:")
        for cls in WIDGET_CLASSES:
            idx = CLASS_TO_IDX[cls]
            print(f"    {cls:<22} {counts.get(idx, 0):>5}")
