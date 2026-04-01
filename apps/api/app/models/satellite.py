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