# apps/api/app/models/satellite.py

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class BoundingBox(BaseModel):
    min_lon: float = Field(..., ge=-180, le=180)
    min_lat: float = Field(..., ge=-90, le=90)
    max_lon: float = Field(..., ge=-180, le=180)
    max_lat: float = Field(..., ge=-90, le=90)

class TileRequest(BaseModel):
    bbox: BoundingBox
    date_from: date
    date_to: date
    resolution: int = Field(default=10, description="Meters per pixel: 10, 20, or 60")

class TileResponse(BaseModel):
    tile_id: str
    bbox: BoundingBox
    image_url: Optional[str]
    cloud_coverage: Optional[float]
    acquired_at: Optional[str]
    status: str          # "ready" | "processing" | "error"
    message: Optional[str]

class SegmentationSummary(BaseModel):
    result_id: str
    dominant_class: str
    class_coverage: dict
    colored_mask_url: str

class DetectionSummary(BaseModel):
    result_id: str
    object_count: int
    infrastructure_count: int
    detections: list[dict]

class TileAnalysisResponse(BaseModel):
    tile_id: str
    bbox: BoundingBox
    image_url: Optional[str]
    preview_url: Optional[str]
    acquired_at: Optional[str]
    status: str
    message: Optional[str]
    segmentation: Optional[SegmentationSummary]
    detection: Optional[DetectionSummary]
class NLPSummary(BaseModel):
    summary: str
    event_type: str
    event_confidence: float
    sources: list[dict]

class QAResponse(BaseModel):
    question: str
    answer: str
    score: float
    context_used: str

# Update TileAnalysisResponse to include nlp field
class TileAnalysisResponse(BaseModel):
    tile_id: str
    bbox: BoundingBox
    image_url: Optional[str]
    preview_url: Optional[str]
    acquired_at: Optional[str]
    status: str
    message: Optional[str]
    segmentation: Optional[SegmentationSummary]
    detection: Optional[DetectionSummary]
    nlp: Optional[NLPSummary]          # ← new