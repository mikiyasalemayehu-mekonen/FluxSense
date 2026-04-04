

import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.ml.segmentor import SegmentationResult
from app.ml.detector import DetectionResult


class AnalysisRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_segmentation(
        self, tile_id: str, result: SegmentationResult, model_name: str
    ) -> str:
        sql = text("""
            INSERT INTO segmentation_results
                (id, tile_id, model_name, mask_file_path, class_coverage, dominant_class)
            VALUES
                (:id, :tile_id, :model_name, :mask_file_path,
                 CAST(:class_coverage AS JSONB), :dominant_class)
            RETURNING id
        """)
        r = await self.db.execute(sql, {
            "id":             result.result_id,
            "tile_id":        tile_id,
            "model_name":     model_name,
            "mask_file_path": result.mask_file_path,
            "class_coverage": json.dumps(result.class_coverage),
            "dominant_class": result.dominant_class,
        })
        await self.db.commit()
        return r.scalar_one()

    async def save_detection(
        self, tile_id: str, result: DetectionResult, model_name: str
    ) -> str:
        sql = text("""
            INSERT INTO detection_results
                (id, tile_id, model_name, detections, object_count)
            VALUES
                (:id, :tile_id, :model_name,
                 CAST(:detections AS JSONB), :object_count)
            RETURNING id
        """)
        r = await self.db.execute(sql, {
            "id":           result.result_id,
            "tile_id":      tile_id,
            "model_name":   model_name,
            "detections":   json.dumps(result.detections),
            "object_count": result.object_count,
        })
        await self.db.commit()
        return r.scalar_one()

    async def get_analysis_for_tile(self, tile_id: str) -> dict:
        seg_sql = text("""
            SELECT id, model_name, class_coverage, dominant_class, created_at
            FROM segmentation_results
            WHERE tile_id = :tile_id
            ORDER BY created_at DESC LIMIT 1
        """)
        det_sql = text("""
            SELECT id, model_name, detections, object_count, created_at
            FROM detection_results
            WHERE tile_id = :tile_id
            ORDER BY created_at DESC LIMIT 1
        """)

        seg = await self.db.execute(seg_sql, {"tile_id": tile_id})
        det = await self.db.execute(det_sql, {"tile_id": tile_id})

        seg_row = seg.fetchone()
        det_row = det.fetchone()

        return {
            "segmentation": dict(seg_row._mapping) if seg_row else None,
            "detection":    dict(det_row._mapping) if det_row else None,
        }