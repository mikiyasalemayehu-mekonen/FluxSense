# apps/api/app/services/sentinel.py

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.satellite import (
    TileRequest, TileAnalysisResponse, BoundingBox,
    SegmentationSummary, DetectionSummary, NLPSummary
)
from app.services.tile_repository import TileRepository
from app.services.analysis_repository import AnalysisRepository
from app.services.report_fetcher import ReportFetcher
from app.services.nlp_repository import NLPRepository
from app.geo.processor import GeoProcessor
from app.ml.segmentor import Segmentor
from app.ml.detector import Detector
from app.ml.nlp import NLPAnalyser
from app.services.risk_engine import RiskEngine
from app.services.risk_repository import RiskRepository
from app.models.satellite import RiskBreakdown

SENTINEL_AUTH_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
SENTINEL_PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

_segmentor = Segmentor()
_detector  = Detector()
_nlp       = NLPAnalyser()
_risk       = RiskEngine()


class SentinelService:

    def __init__(self, db: AsyncSession):
        self.db            = db
        self.tile_repo     = TileRepository(db)
        self.analysis_repo = AnalysisRepository(db)
        self.geo           = GeoProcessor(output_dir="data/tiles")

    async def _get_access_token(self) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                SENTINEL_AUTH_URL,
                data={
                    "grant_type":    "client_credentials",
                    "client_id":     settings.SENTINEL_CLIENT_ID,
                    "client_secret": settings.SENTINEL_CLIENT_SECRET,
                },
            )
            resp.raise_for_status()
            return resp.json()["access_token"]

    async def fetch_and_analyse(self, request: TileRequest) -> TileAnalysisResponse:
        bbox  = request.bbox
        token = await self._get_access_token()

        payload = {
            "input": {
                "bounds": {
                    "bbox": [bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat],
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
                },
                "data": [{
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {
                            "from": f"{request.date_from}T00:00:00Z",
                            "to":   f"{request.date_to}T23:59:59Z",
                        },
                        "maxCloudCoverage": 30,
                    },
                }],
            },
            "output": {
                "width": 512,
                "height": 512,
                "responses": [{"identifier": "default", "format": {"type": "image/png"}}],
            },
            "evalscript": """
                //VERSION=3
                function setup() {
                    return { input: ["B04","B03","B02"], output: { bands: 3 } };
                }
                function evaluatePixel(sample) {
                    return [3.5*sample.B04, 3.5*sample.B03, 3.5*sample.B02];
                }
            """,
        }

        try:
            # ── 1. Fetch satellite tile ───────────────────────────────
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    SENTINEL_PROCESS_URL,
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"},
                )
                resp.raise_for_status()
                raw_bytes = resp.content

            # ── 2. Geo-process ────────────────────────────────────────
            processed = self.geo.process(
                raw_bytes,
                bbox.min_lon, bbox.min_lat,
                bbox.max_lon, bbox.max_lat,
            )
            await self.tile_repo.save_tile(
                tile_id=processed.tile_id,
                wkt_polygon=processed.wkt_polygon,
                acquired_at=request.date_from,
                resolution_m=request.resolution,
                file_path=processed.file_path,
                band_stats=processed.band_stats,
            )

            base_url    = "http://localhost:8000/tiles"
            preview_url = f"{base_url}/{processed.tile_id}_preview.png"

            # ── 3. Segmentation ───────────────────────────────────────
            seg_result = _segmentor.run(processed.file_path)
            await self.analysis_repo.save_segmentation(
                tile_id=processed.tile_id,
                result=seg_result,
                model_name="nvidia/segformer-b2-finetuned-ade-512-512",
            )
            seg_summary = SegmentationSummary(
                result_id=seg_result.result_id,
                dominant_class=seg_result.dominant_class,
                class_coverage=seg_result.class_coverage,
                colored_mask_url=f"{base_url}/{seg_result.result_id}_seg.png",
            )

            # ── 4. Object detection ───────────────────────────────────
            det_result = _detector.run(processed.file_path)
            await self.analysis_repo.save_detection(
                tile_id=processed.tile_id,
                result=det_result,
                model_name="facebook/detr-resnet-50",
            )
            det_summary = DetectionSummary(
                result_id=det_result.result_id,
                object_count=det_result.object_count,
                infrastructure_count=det_result.infrastructure_count,
                detections=det_result.detections,
            )

            # ── 5. NLP: fetch reports + summarize ─────────────────────
            fetcher    = ReportFetcher()
            reports    = await fetcher.fetch_all(bbox)
            nlp_result = _nlp.analyse(reports)

            nlp_repo = NLPRepository(self.db)
            await nlp_repo.save(processed.tile_id, nlp_result)

            nlp_summary = NLPSummary(
                summary=nlp_result.summary,
                event_type=nlp_result.event_type,
                event_confidence=nlp_result.event_confidence,
                sources=nlp_result.sources,
            )
            # ── 6. Risk scoring ───────────────────────────────────────
            risk_repo = RiskRepository(self.db)
            history   = await risk_repo.get_history_for_bbox(
                bbox.min_lon, bbox.min_lat,
                bbox.max_lon, bbox.max_lat,
            )
            historical_scores = [h["overall_score"] for h in history]

            risk_result = _risk.compute(
                class_coverage=seg_result.class_coverage,
                event_type=nlp_result.event_type,
                event_confidence=nlp_result.event_confidence,
                historical_scores=historical_scores,
            )

            # Get the wkt from the processed tile
            await risk_repo.save(
                tile_id=processed.tile_id,
                wkt_polygon=processed.wkt_polygon,
                score=risk_result,
                acquired_at=request.date_from,
            )

            risk_breakdown = RiskBreakdown(
                overall_score=risk_result.overall_score,
                label=risk_result.label,
                trend=risk_result.trend,
                vegetation_score=risk_result.vegetation_score,
                water_score=risk_result.water_score,
                urban_exposure=risk_result.urban_exposure,
                event_score=risk_result.event_score,
                explanation=risk_result.explanation,
            )

            return TileAnalysisResponse(
                tile_id=processed.tile_id,
                bbox=bbox,
                image_url=preview_url,
                preview_url=preview_url,
                acquired_at=str(request.date_from),
                status="ready",
                message=(
                    f"Tile processed. Land cover: {seg_result.dominant_class}. "
                    f"Event type: {nlp_result.event_type} "
                    f"({round(nlp_result.event_confidence * 100)}% confidence)."
                ),
                segmentation=seg_summary,
                detection=det_summary,
                nlp=nlp_summary,
            )



        except httpx.HTTPStatusError as e:
            return TileAnalysisResponse(
                tile_id=processed.tile_id,
                bbox=bbox,
                image_url=preview_url,
                preview_url=preview_url,
                acquired_at=str(request.date_from),
                status="ready",
                message=(
                    f"Risk: {risk_result.label.upper()} "
                    f"({risk_result.overall_score}/100). "
                    f"Land cover: {seg_result.dominant_class}. "
                    f"Event: {nlp_result.event_type}."
                ),
                segmentation=seg_summary,
                detection=det_summary,
                nlp=nlp_summary,
                risk=risk_breakdown,
            )