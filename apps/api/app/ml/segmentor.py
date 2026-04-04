import os
import uuid
import numpy as np
import rasterio
from PIL import Image
from dataclasses import dataclass
from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation
import torch
import torch.nn.functional as F

# SegFormer fine-tuned on ADE20K — 150 classes including
# water, vegetation, building, road, sky, earth/soil etc.
# Swap for a remote-sensing specific model in Phase 7 polish.
MODEL_NAME = "nvidia/segformer-b2-finetuned-ade-512-512"

# Map ADE20K class indices to our 5 risk-relevant categories
# Full label list: https://huggingface.co/datasets/huggingface/label-files
CATEGORY_MAP = {
    "water":      [21, 26, 60, 113, 128],   # sea, river, lake, water, waterfall
    "vegetation": [4, 9, 17, 66, 72, 96],   # tree, grass, plant, flower, palm, swamp
    "urban":      [0, 1, 2, 6, 29, 46, 53], # wall, building, sky, road, house, signboard, bridge
    "bare_soil":  [13, 46, 94],             # earth, field, land
    "other":      [],                        # catch-all
}


@dataclass
class SegmentationResult:
    result_id: str
    mask_file_path: str
    class_coverage: dict   # {"water": 12.4, "vegetation": 38.1, ...}
    dominant_class: str
    colored_mask_path: str


# Color palette for the visual overlay (RGBA)
CLASS_COLORS = {
    "water":      (30,  144, 255, 180),   # dodger blue
    "vegetation": (34,  139, 34,  180),   # forest green
    "urban":      (169, 169, 169, 180),   # gray
    "bare_soil":  (139, 90,  43,  180),   # brown
    "other":      (200, 200, 200, 120),   # light gray
}


class Segmentor:
    """
    Runs SegFormer semantic segmentation on a GeoTIFF tile.
    Models are loaded once and cached as class attributes
    so they survive across requests without reloading.
    """
    _processor = None
    _model = None

    @classmethod
    def _load_model(cls):
        if cls._model is None:
            print(f"[Segmentor] Loading {MODEL_NAME} ...")
            cls._processor = SegformerImageProcessor.from_pretrained(MODEL_NAME)
            cls._model = SegformerForSemanticSegmentation.from_pretrained(MODEL_NAME)
            cls._model.eval()
            print("[Segmentor] Model loaded.")

    def run(self, geotiff_path: str, output_dir: str = "data/tiles") -> SegmentationResult:
        self._load_model()
        result_id = str(uuid.uuid4())

        # 1. Read GeoTIFF bands back into a uint8 RGB image
        rgb = self._load_rgb_from_tiff(geotiff_path)

        # 2. Run SegFormer inference
        inputs = self._processor(images=rgb, return_tensors="pt")
        with torch.no_grad():
            outputs = self._model(**inputs)

        # 3. Upsample logits to original image size
        logits = outputs.logits                          # (1, num_classes, H/4, W/4)
        upsampled = F.interpolate(
            logits,
            size=rgb.size[::-1],                        # (H, W)
            mode="bilinear",
            align_corners=False,
        )
        predicted_mask = upsampled.argmax(dim=1).squeeze().numpy()  # (H, W) int

        # 4. Map raw class indices → our 5 categories
        category_mask = self._map_to_categories(predicted_mask)

        # 5. Compute coverage percentages
        total_pixels = category_mask.size
        class_coverage = {}
        for cat in CLASS_COLORS:
            cat_idx = list(CLASS_COLORS.keys()).index(cat)
            count = int(np.sum(category_mask == cat_idx))
            class_coverage[cat] = round((count / total_pixels) * 100, 2)

        dominant_class = max(class_coverage, key=class_coverage.get)

        # 6. Save raw mask as numpy array (for Phase 5 delta analysis)
        mask_path = os.path.join(output_dir, f"{result_id}_mask.npy")
        np.save(mask_path, category_mask)

        # 7. Save colored PNG overlay for frontend
        colored_path = os.path.join(output_dir, f"{result_id}_seg.png")
        self._save_colored_mask(category_mask, rgb.size, colored_path)

        return SegmentationResult(
            result_id=result_id,
            mask_file_path=mask_path,
            class_coverage=class_coverage,
            dominant_class=dominant_class,
            colored_mask_path=colored_path,
        )

    def _load_rgb_from_tiff(self, path: str) -> Image.Image:
        with rasterio.open(path) as src:
            r = src.read(1)
            g = src.read(2)
            b = src.read(3)
        # Convert 0-1 float back to 0-255 uint8
        rgb_array = np.stack([r, g, b], axis=-1)
        rgb_array = (np.clip(rgb_array, 0, 1) * 255).astype(np.uint8)
        return Image.fromarray(rgb_array, mode="RGB")

    def _map_to_categories(self, mask: np.ndarray) -> np.ndarray:
        """Map ADE20K class indices to our 5-category schema."""
        category_mask = np.full(mask.shape, 4, dtype=np.uint8)  # default: "other"
        for cat_idx, (cat_name, class_indices) in enumerate(CATEGORY_MAP.items()):
            if cat_name == "other":
                continue
            for cls_idx in class_indices:
                category_mask[mask == cls_idx] = cat_idx
        return category_mask

    def _save_colored_mask(
        self, category_mask: np.ndarray, size: tuple, path: str
    ):
        """Render category mask as a colored RGBA overlay PNG."""
        h, w = category_mask.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        for cat_idx, (cat_name, color) in enumerate(CLASS_COLORS.items()):
            rgba[category_mask == cat_idx] = color
        img = Image.fromarray(rgba, mode="RGBA")
        img = img.resize(size, Image.NEAREST)
        img.save(path, format="PNG")