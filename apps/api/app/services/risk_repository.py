# apps/api/app/services/risk_repository.py

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
    ) -> str:
        sql = text("""
            INSERT INTO risk_scores
                (tile_id, bbox, overall_score, vegetation_score,
                 water_score, urban_exposure, event_score,
                 trend, acquired_at)
            VALUES
                (:tile_id,
                 ST_GeomFromText(:wkt, 4326),
                 :overall_score, :vegetation_score,
                 :water_score, :urban_exposure, :event_score,
                 :trend, :acquired_at)
            RETURNING id
        """)
        r = await self.db.execute(sql, {
            "tile_id":          tile_id,
            "wkt":              wkt_polygon,
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
        """Get historical risk scores for a geographic area."""
        sql = text("""
            SELECT
                r.id,
                r.tile_id,
                r.overall_score,
                r.vegetation_score,
                r.water_score,
                r.urban_exposure,
                r.event_score,
                r.trend,
                r.acquired_at,
                r.created_at
            FROM risk_scores r
            WHERE ST_Intersects(
                r.bbox,
                ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)
            )
            ORDER BY r.acquired_at DESC
            LIMIT :limit
        """)
        result = await self.db.execute(sql, {
            "min_lon": min_lon,
            "min_lat": min_lat,
            "max_lon": max_lon,
            "max_lat": max_lat,
            "limit":   limit,
        })
        return [dict(row._mapping) for row in result]