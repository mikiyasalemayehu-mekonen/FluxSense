# apps/api/app/routers/satellite.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.satellite import TileRequest, TileAnalysisResponse
from app.services.sentinel import SentinelService

router = APIRouter(prefix="/satellite", tags=["satellite"])

@router.post("/tile", response_model=TileAnalysisResponse)
async def fetch_satellite_tile(
    request: TileRequest,
    db: AsyncSession = Depends(get_db),
):
    service = SentinelService(db)
    return await service.fetch_and_analyse(request)   # ← was fetch_tile

@router.get("/tiles/search")
async def search_tiles(
    min_lon: float, min_lat: float,
    max_lon: float, max_lat: float,
    db: AsyncSession = Depends(get_db),
):
    from app.services.tile_repository import TileRepository
    repo = TileRepository(db)
    return await repo.find_tiles_in_bbox(min_lon, min_lat, max_lon, max_lat)

@router.get("/tiles/{tile_id}/analysis")
async def get_tile_analysis(
    tile_id: str,
    db: AsyncSession = Depends(get_db),
):
    from app.services.analysis_repository import AnalysisRepository
    repo = AnalysisRepository(db)
    return await repo.get_analysis_for_tile(tile_id)