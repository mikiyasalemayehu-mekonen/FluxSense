

import uuid
import numpy as np
import rasterio
from PIL import Image
from dataclasses import dataclass, field
from transformers import DetrImageProcessor, DetrForObjectDetection
import torch

MODEL_NAME = "facebook/detr-resnet-50"

# Classes from COCO that are relevant to infrastructure risk assessment
INFRASTRUCTURE_LABELS = {
    "car", "truck", "bus", "train",
    "boat", "airplane",
    "traffic light", "fire hydrant", "stop sign",
    "bench", "chair",
    "bridge",                         # not in COCO but kept for future fine-tuning
}


@dataclass
class DetectionResult:
    result_id: str
    detections: list[dict]            # [{label, score, bbox_px: [x1,y1,x2,y2]}]
    object_count: int
    infrastructure_count: int


class Detector:
    """
    Runs DETR object detection on a GeoTIFF tile.
    Best suited for high-resolution urban tiles.
    """
    _processor = None
    _model = None

    @classmethod
    def _load_model(cls):
        if cls._model is None:
            print(f"[Detector] Loading {MODEL_NAME} ...")
            cls._processor = DetrImageProcessor.from_pretrained(MODEL_NAME)
            cls._model = DetrForObjectDetection.from_pretrained(MODEL_NAME)
            cls._model.eval()
            print("[Detector] Model loaded.")

    def run(self, geotiff_path: str, confidence_threshold: float = 0.7) -> DetectionResult:
        self._load_model()
        result_id = str(uuid.uuid4())

        rgb = self._load_rgb_from_tiff(geotiff_path)

        inputs = self._processor(images=rgb, return_tensors="pt")
        with torch.no_grad():
            outputs = self._model(**inputs)

        # Post-process into human-readable detections
        target_sizes = torch.tensor([rgb.size[::-1]])
        results = self._processor.post_process_object_detection(
            outputs,
            threshold=confidence_threshold,
            target_sizes=target_sizes,
        )[0]

        detections = []
        for score, label, box in zip(
            results["scores"], results["labels"], results["boxes"]
        ):
            label_name = self._model.config.id2label[label.item()]
            detections.append({
                "label":   label_name,
                "score":   round(score.item(), 4),
                "bbox_px": [round(v, 1) for v in box.tolist()],  # [x1, y1, x2, y2]
            })

        infrastructure = [
            d for d in detections
            if d["label"] in INFRASTRUCTURE_LABELS
        ]

        return DetectionResult(
            result_id=result_id,
            detections=detections,
            object_count=len(detections),
            infrastructure_count=len(infrastructure),
        )

    def _load_rgb_from_tiff(self, path: str) -> Image.Image:
        with rasterio.open(path) as src:
            r = src.read(1)
            g = src.read(2)
            b = src.read(3)
        rgb_array = np.stack([r, g, b], axis=-1)
        rgb_array = (np.clip(rgb_array, 0, 1) * 255).astype(np.uint8)
        return Image.fromarray(rgb_array, mode="RGB")