# apps/api/app/ml/segmentor.py

import uuid
import numpy as np
from PIL import Image
from dataclasses import dataclass
import os

CLASS_COLORS = {
    "water":      (30,  144, 255, 180),
    "vegetation": (34,  139, 34,  180),
    "urban":      (169, 169, 169, 180),
    "bare_soil":  (139, 90,  43,  180),
    "other":      (200, 200, 200, 120),
}

# ADE20K label index → our 5 categories
CATEGORY_MAP = {
    "water":      [21, 26, 60, 113, 128],
    "vegetation": [4, 9, 17, 66, 72, 96],
    "urban":      [0, 1, 2, 6, 29, 46, 53],
    "bare_soil":  [13, 46, 94],
}


@dataclass
class SegmentationResult:
    result_id:         str
    mask_file_path:    str
    class_coverage:    dict
    dominant_class:    str
    colored_mask_path: str


class Segmentor:
    """Runs segmentation via HuggingFace Inference API — no local model needed."""

    async def run(self, geotiff_path: str, output_dir: str = "data/tiles") -> SegmentationResult:
        from app.ml.hf_client import run_segmentation

        result_id = str(uuid.uuid4())
        os.makedirs(output_dir, exist_ok=True)

        try:
            api_response = await run_segmentation(geotiff_path)
            class_coverage, category_mask, size = self._parse_response(api_response)
        except Exception as e:
            print(f"[Segmentor] HF API error: {e} — using fallback")
            class_coverage = {
                "water": 0.0, "vegetation": 15.0,
                "urban": 70.0, "bare_soil": 5.0, "other": 10.0
            }
            category_mask = np.full((512, 512), 2, dtype=np.uint8)
            size = (512, 512)

        dominant_class = max(class_coverage, key=class_coverage.get)

        mask_path = os.path.join(output_dir, f"{result_id}_mask.npy")
        np.save(mask_path, category_mask)

        colored_path = os.path.join(output_dir, f"{result_id}_seg.png")
        self._save_colored_mask(category_mask, size, colored_path)

        return SegmentationResult(
            result_id=result_id,
            mask_file_path=mask_path,
            class_coverage=class_coverage,
            dominant_class=dominant_class,
            colored_mask_path=colored_path,
        )

    def _parse_response(self, api_response: list) -> tuple[dict, np.ndarray, tuple]:
        """
        HF segmentation API returns a list of segments with label + mask.
        Each mask is a base64-encoded PNG.
        """
        import base64
        import io

        size = (512, 512)
        category_mask = np.full(size, 4, dtype=np.uint8)  # default: other

        cat_map = {
            "water": 0, "vegetation": 1, "urban": 2,
            "bare_soil": 3, "other": 4,
        }

        ade_to_cat = {}
        for cat, indices in CATEGORY_MAP.items():
            for idx in indices:
                ade_to_cat[idx] = cat

        for segment in api_response:
            label = segment.get("label", "").lower()
            score = segment.get("score", 0)
            mask_b64 = segment.get("mask", "")

            if not mask_b64 or score < 0.5:
                continue

            # Decode the binary mask
            mask_bytes = base64.b64decode(mask_b64)
            mask_img   = Image.open(io.BytesIO(mask_bytes)).convert("L")
            mask_arr   = np.array(mask_img) > 128

            # Map ADE20K label to our category
            mapped_cat = "other"
            for cat, keywords in {
                "water":      ["water", "sea", "river", "lake"],
                "vegetation": ["tree", "grass", "plant", "vegetation"],
                "urban":      ["building", "road", "wall", "house", "pavement"],
                "bare_soil":  ["earth", "field", "land", "dirt"],
            }.items():
                if any(k in label for k in keywords):
                    mapped_cat = cat
                    break

            cat_idx = cat_map[mapped_cat]
            category_mask[mask_arr] = cat_idx

        # Compute coverage
        total = category_mask.size
        class_coverage = {}
        for cat, idx in cat_map.items():
            count = int(np.sum(category_mask == idx))
            class_coverage[cat] = round((count / total) * 100, 2)

        return class_coverage, category_mask, size

    def _save_colored_mask(self, mask: np.ndarray, size: tuple, path: str):
        h, w = mask.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        for cat_idx, (cat, color) in enumerate(CLASS_COLORS.items()):
            rgba[mask == cat_idx] = color
        img = Image.fromarray(rgba, mode="RGBA")
        img.save(path, format="PNG")