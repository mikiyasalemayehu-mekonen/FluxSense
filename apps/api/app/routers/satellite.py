# apps/api/app/routers/satellite.py

from fastapi import APIRouter, Depends
from app.models.satellite import TileRequest, TileResponse
from app.services.sentinel import SentinelService

router = APIRouter(prefix="/satellite", tags=["satellite"])

@router.post("/tile", response_model=TileResponse)
async def fetch_satellite_tile(
    request: TileRequest,
    service: SentinelService = Depends(SentinelService),
):
    """
    Fetch a Sentinel-2 true-color tile for a bounding box and date range.
    Phase 1: confirms fetch. Phase 2: stores and returns a URL.
    """
    return await service.fetch_tile(request)