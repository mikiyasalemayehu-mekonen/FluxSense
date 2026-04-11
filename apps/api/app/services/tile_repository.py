# apps/api/app/services/tile_repository.py

import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import date


class TileRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_tile(
        self,
        tile_id: str,
        wkt_polygon: str,
        acquired_at: date,
        resolution_m: int,
        file_path: str,
        band_stats: dict,
        cloud_coverage: float | None = None,
        min_lon: float = 0,
        min_lat: float = 0,
        max_lon: float = 0,
        max_lat: float = 0,
    ) -> str:
        sql = text("""
            INSERT INTO satellite_tiles
                (id, bbox_wkt, min_lon, min_lat, max_lon, max_lat,
                 acquired_at, resolution_m, file_path, band_stats, cloud_coverage)
            VALUES
                (:id, :wkt, :min_lon, :min_lat, :max_lon, :max_lat,
                 :acquired_at, :resolution_m, :file_path,
                 CAST(:band_stats AS JSONB), :cloud_coverage)
            RETURNING id
        """)
        result = await self.db.execute(sql, {
            "id":             tile_id,
            "wkt":            wkt_polygon,
            "min_lon":        min_lon,
            "min_lat":        min_lat,
            "max_lon":        max_lon,
            "max_lat":        max_lat,
            "acquired_at":    acquired_at,
            "resolution_m":   resolution_m,
            "file_path":      file_path,
            "band_stats":     json.dumps(band_stats),
            "cloud_coverage": cloud_coverage,
        })
        await self.db.commit()
        return result.scalar_one()

    async def find_tiles_in_bbox(
        self,
        min_lon: float, min_lat: float,
        max_lon: float, max_lat: float,
    ) -> list[dict]:
        sql = text("""
            SELECT
                id,
                bbox_wkt,
                min_lon,
                min_lat,
                max_lon,
                max_lat,
                acquired_at,
                resolution_m,
                file_path,
                band_stats,
                cloud_coverage,
                created_at
            FROM satellite_tiles
            WHERE min_lon <= :max_lon AND max_lon >= :min_lon
              AND min_lat <= :max_lat AND max_lat >= :min_lat
            ORDER BY acquired_at DESC
        """)
        result = await self.db.execute(sql, {
            "min_lon": min_lon,
            "min_lat": min_lat,
            "max_lon": max_lon,
            "max_lat": max_lat,
        })
        return [dict(row._mapping) for row in result]