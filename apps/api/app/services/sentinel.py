# apps/api/app/services/sentinel.py  (updated for Phase 2)

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.satellite import TileRequest, TileResponse
from app.services.tile_repository import TileRepository

from app.geo.processor import GeoProcessor

SENTINEL_AUTH_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
SENTINEL_PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

class SentinelService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TileRepository(db)
        self.geo = GeoProcessor(output_dir="data/tiles")

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

    async def fetch_tile(self, request: TileRequest) -> TileResponse:
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
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    SENTINEL_PROCESS_URL,
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"},
                )
                resp.raise_for_status()
                raw_bytes = resp.content

            # ── Phase 2: process and persist ──────────────────────────────
            processed = self.geo.process(
                raw_bytes,
                bbox.min_lon, bbox.min_lat,
                bbox.max_lon, bbox.max_lat,
            )

            await self.repo.save_tile(
                tile_id=processed.tile_id,
                wkt_polygon=processed.wkt_polygon,
                acquired_at=request.date_from,
                resolution_m=request.resolution,
                file_path=processed.file_path,
                band_stats=processed.band_stats,
            )

            preview_url = f"http://localhost:8000/tiles/{processed.tile_id}_preview.png"

            return TileResponse(
                tile_id=processed.tile_id,
                bbox=bbox,
                image_url=preview_url,       # no longer null
                cloud_coverage=None,
                acquired_at=str(request.date_from),
                status="ready",
                message=f"Processed: {processed.width}x{processed.height}px. Stored to PostGIS.",
            )

        except httpx.HTTPStatusError as e:
            return TileResponse(
                tile_id="error",
                bbox=bbox,
                image_url=None,
                cloud_coverage=None,
                acquired_at=None,
                status="error",
                message=f"Sentinel API error: {e.response.status_code}",
            )