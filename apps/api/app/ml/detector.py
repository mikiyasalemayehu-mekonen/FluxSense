# apps/api/app/ml/detector.py

import uuid
from dataclasses import dataclass


@dataclass
class DetectionResult:
    result_id:            str
    detections:           list[dict]
    object_count:         int
    infrastructure_count: int


class Detector:
    """
    Object detection via HF API is rate-limited on free tier.
    Returns empty result — re-enable with paid HF Inference Endpoints.
    """
    def run(self, geotiff_path: str, confidence_threshold: float = 0.7) -> DetectionResult:
        return DetectionResult(
            result_id=str(uuid.uuid4()),
            detections=[],
            object_count=0,
            infrastructure_count=0,
        )