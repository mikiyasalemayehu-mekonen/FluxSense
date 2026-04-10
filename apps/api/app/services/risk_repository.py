

import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import date
from app.services.risk_engine import RiskScore


class RiskRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def save(
        self,
        tile_id: str,
        wkt_polygon: str,
        score: RiskScore,
        acquired_at: date,
        min_lon: float = 0,
        min_lat: float = 0,
        max_lon: float = 0,
        max_lat: float = 0,
    ) -> str:
        sql = text("""
            INSERT INTO risk_scores
                (tile_id, min_lon, min_lat, max_lon, max_lat,
                 overall_score, vegetation_score, water_score,
                 urban_exposure, event_score, trend, acquired_at)
            VALUES
                (:tile_id, :min_lon, :min_lat, :max_lon, :max_lat,
                 :overall_score, :vegetation_score, :water_score,
                 :urban_exposure, :event_score, :trend, :acquired_at)
            RETURNING id
        """)
        r = await self.db.execute(sql, {
            "tile_id":          tile_id,
            "min_lon":          min_lon,
            "min_lat":          min_lat,
            "max_lon":          max_lon,
            "max_lat":          max_lat,
            "overall_score":    score.overall_score,
            "vegetation_score": score.vegetation_score,
            "water_score":      score.water_score,
            "urban_exposure":   score.urban_exposure,
            "event_score":      score.event_score,
            "trend":            score.trend,
            "acquired_at":      acquired_at,
        })
        await self.db.commit()
        return r.scalar_one()

    async def get_history_for_bbox(
        self,
        min_lon: float, min_lat: float,
        max_lon: float, max_lat: float,
        limit: int = 30,
    ) -> list[dict]:
        sql = text("""
            SELECT id, tile_id, overall_score, vegetation_score,
                   water_score, urban_exposure, event_score,
                   trend, acquired_at, created_at
            FROM risk_scores
            WHERE min_lon <= :max_lon AND max_lon >= :min_lon
              AND min_lat <= :max_lat AND max_lat >= :min_lat
            ORDER BY acquired_at DESC
            LIMIT :limit
        """)
        result = await self.db.execute(sql, {
            "min_lon": min_lon, "min_lat": min_lat,
            "max_lon": max_lon, "max_lat": max_lat,
            "limit":   limit,
        })
        return [dict(row._mapping) for row in result]