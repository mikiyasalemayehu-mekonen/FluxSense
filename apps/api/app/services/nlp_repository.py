# apps/api/app/services/nlp_repository.py

import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.ml.nlp import NLPResult


class NLPRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def save(self, tile_id: str, result: NLPResult) -> str:
        sql = text("""
            INSERT INTO nlp_results
                (tile_id, sources, summary, event_type, event_confidence, raw_texts)
            VALUES
                (:tile_id,
                 CAST(:sources AS JSONB),
                 :summary,
                 :event_type,
                 :event_confidence,
                 CAST(:raw_texts AS JSONB))
            RETURNING id
        """)
        r = await self.db.execute(sql, {
            "tile_id":          tile_id,
            "sources":          json.dumps(result.sources),
            "summary":          result.summary,
            "event_type":       result.event_type,
            "event_confidence": result.event_confidence,
            "raw_texts":        json.dumps(result.raw_texts),
        })
        await self.db.commit()
        return r.scalar_one()

    async def get_for_tile(self, tile_id: str) -> dict | None:
        sql = text("""
            SELECT id, summary, event_type, event_confidence,
                   sources, created_at
            FROM nlp_results
            WHERE tile_id = :tile_id
            ORDER BY created_at DESC LIMIT 1
        """)
        result = await self.db.execute(sql, {"tile_id": tile_id})
        row = result.fetchone()
        return dict(row._mapping) if row else None