# apps/api/app/services/sentinel.py  (full file)

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.satellite import TileRequest, TileAnalysisResponse, BoundingBox
from app.models.satellite import SegmentationSummary, DetectionSummary
from app.services.tile_repository import TileRepository
from app.services.analysis_repository import AnalysisRepository
from app.geo.processor import GeoProcessor
from app.ml.segmentor import Segmentor
from app.ml.detector import Detector

SENTINEL_AUTH_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
SENTINEL_PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

# Instantiate models once — they cache themselves on first use
_segmentor = Segmentor()
_detector  = Detector()


class SentinelService:

    def __init__(self, db: AsyncSession):
        self.db           = db
        self.tile_repo    = TileRepository(db)
        self.analysis_repo = AnalysisRepository(db)
        self.geo          = GeoProcessor(output_dir="data/tiles")

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
        bbox = request.bbox
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
            # ── 1. Fetch satellite tile ────────────────────────────────
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    SENTINEL_PROCESS_URL,
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"},
                )
                resp.raise_for_status()
                raw_bytes = resp.content

            # ── 2. Geo-process → GeoTIFF + preview PNG ────────────────
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

            base_url = "http://localhost:8000/tiles"
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

            return TileAnalysisResponse(
                tile_id=processed.tile_id,
                bbox=bbox,
                image_url=preview_url,
                preview_url=preview_url,
                acquired_at=str(request.date_from),
                status="ready",
                message=f"Tile processed. Dominant land cover: {seg_result.dominant_class}. "
                        f"Objects detected: {det_result.object_count}.",
                segmentation=seg_summary,
                detection=det_summary,
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
            )