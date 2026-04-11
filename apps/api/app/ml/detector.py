# apps/api/app/ml/detector.py

from dataclasses import dataclass, field

@dataclass
class DetectionResult:
    result_id: str
    detections: list[dict]
    object_count: int
    infrastructure_count: int


class Detector:
    """
    DETR disabled on Railway free tier — too memory intensive.
    Returns empty detection result. Re-enable when on paid plan.
    """
    def run(self, geotiff_path: str, confidence_threshold: float = 0.7) -> DetectionResult:
        import uuid
        return DetectionResult(
            result_id=str(uuid.uuid4()),
            detections=[],
            object_count=0,
            infrastructure_count=0,
        )