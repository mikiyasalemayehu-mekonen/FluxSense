# apps/api/app/routers/satellite.py  (updated)

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.satellite import TileRequest, TileResponse
from app.services.sentinel import SentinelService

router = APIRouter(prefix="/satellite", tags=["satellite"])

@router.post("/tile", response_model=TileResponse)
async def fetch_satellite_tile(
    request: TileRequest,
    db: AsyncSession = Depends(get_db),
):
    service = SentinelService(db)
    return await service.fetch_tile(request)

@router.get("/tiles/search")
async def search_tiles(
    min_lon: float, min_lat: float,
    max_lon: float, max_lat: float,
    db: AsyncSession = Depends(get_db),
):
    """Return all stored tiles that overlap a bounding box."""
    from app.services.tile_repository import TileRepository
    repo = TileRepository(db)
    return await repo.find_tiles_in_bbox(min_lon, min_lat, max_lon, max_lat)