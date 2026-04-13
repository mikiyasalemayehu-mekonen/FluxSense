# apps/api/app/services/sentinel.py

import os
import gc
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.satellite import (
    TileRequest, TileAnalysisResponse,
    SegmentationSummary, DetectionSummary, NLPSummary, RiskBreakdown
)
from app.services.tile_repository import TileRepository
from app.services.analysis_repository import AnalysisRepository
from app.services.report_fetcher import ReportFetcher
from app.services.nlp_repository import NLPRepository
from app.services.risk_engine import RiskEngine
from app.services.risk_repository import RiskRepository
from app.geo.processor import GeoProcessor
from app.ml.segmentor import Segmentor
from app.ml.detector import Detector
from app.ml.nlp import NLPAnalyser

SENTINEL_AUTH_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
SENTINEL_PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"


class SentinelService:
    _segmentor: Segmentor | None   = None
    _detector:  Detector | None    = None
    _nlp:       NLPAnalyser | None = None
    _risk:      RiskEngine         = RiskEngine()

    def __init__(self, db: AsyncSession):
        self.db            = db
        self.tile_repo     = TileRepository(db)
        self.analysis_repo = AnalysisRepository(db)
        self.geo           = GeoProcessor(output_dir="data/tiles")

    @classmethod
    def _get_segmentor(cls) -> Segmentor:
        if cls._segmentor is None:
            cls._segmentor = Segmentor()
        return cls._segmentor

    @classmethod
    def _get_detector(cls) -> Detector:
        if cls._detector is None:
            cls._detector = Detector()
        return cls._detector

    @classmethod
    def _get_nlp(cls) -> NLPAnalyser:
        if cls._nlp is None:
            cls._nlp = NLPAnalyser()
        return cls._nlp

    def _get_base_url(self) -> str:
        return os.getenv("TILES_BASE_URL", "http://localhost:8000/tiles")

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
            async with httpx.AsyncClient(timeout=60.0) as client:
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
                min_lon=bbox.min_lon,
                min_lat=bbox.min_lat,
                max_lon=bbox.max_lon,
                max_lat=bbox.max_lat,
            )

            base_url    = self._get_base_url()
            preview_url = f"{base_url}/{processed.tile_id}_preview.png"

            # ── 3. Segmentation ───────────────────────────────────────
            seg_result = self._get_segmentor().run(processed.file_path)
            gc.collect()
            await self.analysis_repo.save_segmentation(
                tile_id=processed.tile_id,
                result=seg_result,
                model_name="nvidia/segformer-b0-finetuned-ade-512-512",
            )
            seg_summary = SegmentationSummary(
                result_id=seg_result.result_id,
                dominant_class=seg_result.dominant_class,
                class_coverage=seg_result.class_coverage,
                colored_mask_url=f"{base_url}/{seg_result.result_id}_seg.png",
            )

            # ── 4. Object detection — disabled on free tier ───────────
            det_result = self._get_detector().run(processed.file_path)
            await self.analysis_repo.save_detection(
                tile_id=processed.tile_id,
                result=det_result,
                model_name="disabled-free-tier",
            )
            det_summary = DetectionSummary(
                result_id=det_result.result_id,
                object_count=det_result.object_count,
                infrastructure_count=det_result.infrastructure_count,
                detections=det_result.detections,
            )

            # ── 5. NLP: optional, skip gracefully if OOM ─────────────
            try:
                fetcher    = ReportFetcher()
                reports    = await fetcher.fetch_all(bbox)
                nlp_result = await self._get_nlp().analyse(reports)
                gc.collect()
                nlp_repo   = NLPRepository(self.db)
                await nlp_repo.save(processed.tile_id, nlp_result)
                nlp_summary = NLPSummary(
                    summary=nlp_result.summary,
                    event_type=nlp_result.event_type,
                    event_confidence=nlp_result.event_confidence,
                    sources=nlp_result.sources,
                )
                event_type       = nlp_result.event_type
                event_confidence = nlp_result.event_confidence
            except Exception as nlp_err:
                print(f"[NLP] Skipped: {nlp_err}")
                nlp_summary = NLPSummary(
                    summary="NLP unavailable on current plan.",
                    event_type="normal conditions",
                    event_confidence=0.5,
                    sources=[],
                )
                event_type       = "normal conditions"
                event_confidence = 0.5

            # ── 6. Risk scoring ───────────────────────────────────────
            risk_repo = RiskRepository(self.db)
            history   = await risk_repo.get_history_for_bbox(
                bbox.min_lon, bbox.min_lat,
                bbox.max_lon, bbox.max_lat,
            )
            historical_scores = [h["overall_score"] for h in history]

            risk_result = self._risk.compute(
                class_coverage=seg_result.class_coverage,
                event_type=event_type,
                event_confidence=event_confidence,
                historical_scores=historical_scores,
            )
            await risk_repo.save(
                tile_id=processed.tile_id,
                wkt_polygon=processed.wkt_polygon,
                score=risk_result,
                acquired_at=request.date_from,
                min_lon=bbox.min_lon,
                min_lat=bbox.min_lat,
                max_lon=bbox.max_lon,
                max_lat=bbox.max_lat,
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
                    f"Risk: {risk_result.label.upper()} "
                    f"({risk_result.overall_score}/100). "
                    f"Land cover: {seg_result.dominant_class}. "
                    f"Event: {event_type}."
                ),
                segmentation=seg_summary,
                detection=det_summary,
                nlp=nlp_summary,
                risk=risk_breakdown,
            )

        except httpx.HTTPStatusError as e:
            return TileAnalysisResponse(
                tile_id="error",
                bbox=bbox,
                image_url=None,
                preview_url=None,
                acquired_at=None,
                status="error",
                message=f"Sentinel API error: {e.response.status_code}",
                segmentation=None,
                detection=None,
                nlp=None,
                risk=None,
            )

        except Exception as e:
            return TileAnalysisResponse(
                tile_id="error",
                bbox=bbox,
                image_url=None,
                preview_url=None,
                acquired_at=None,
                status="error",
                message=f"Analysis failed: {str(e)}",
                segmentation=None,
                detection=None,
                nlp=None,
                risk=None,
            )