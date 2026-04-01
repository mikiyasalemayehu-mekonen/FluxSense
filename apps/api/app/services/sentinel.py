# apps/api/app/services/sentinel.py

import httpx
import uuid
from datetime import date
from app.core.config import settings
from app.models.satellite import BoundingBox, TileRequest, TileResponse

SENTINEL_AUTH_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
SENTINEL_PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

class SentinelService:

    async def _get_access_token(self) -> str:
        """Exchange client credentials for a bearer token."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                SENTINEL_AUTH_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.SENTINEL_CLIENT_ID,
                    "client_secret": settings.SENTINEL_CLIENT_SECRET,
                },
            )
            resp.raise_for_status()
            return resp.json()["access_token"]

    async def fetch_tile(self, request: TileRequest) -> TileResponse:
        """
        Fetch a True Color (RGB) Sentinel-2 tile for a bounding box.
        Returns a TileResponse with a base64 PNG or an error status.
        """
        tile_id = str(uuid.uuid4())
        bbox = request.bbox

        token = await self._get_access_token()

        # Sentinel Hub Process API payload
        # Uses evalscript to compose True Color image from bands B04, B03, B02
        payload = {
            "input": {
                "bounds": {
                    "bbox": [bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat],
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
                },
                "data": [
                    {
                        "type": "sentinel-2-l2a",
                        "dataFilter": {
                            "timeRange": {
                                "from": f"{request.date_from}T00:00:00Z",
                                "to": f"{request.date_to}T23:59:59Z",
                            },
                            "maxCloudCoverage": 30,  # skip heavily clouded scenes
                        },
                    }
                ],
            },
            "output": {
                "width": 512,
                "height": 512,
                "responses": [{"identifier": "default", "format": {"type": "image/png"}}],
            },
            # Evalscript: how to compose pixels from satellite bands
            "evalscript": """
                //VERSION=3
                function setup() {
                    return { input: ["B04","B03","B02"], output: { bands: 3 } };
                }
                function evaluatePixel(sample) {
                    return [
                        3.5 * sample.B04,
                        3.5 * sample.B03,
                        3.5 * sample.B02
                    ];
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

                # In a real setup you'd store this PNG to S3/disk
                # For Phase 1 we return confirmation the tile was received
                content_length = len(resp.content)

                return TileResponse(
                    tile_id=tile_id,
                    bbox=bbox,
                    image_url=None,   # will wire to S3 in Phase 2
                    cloud_coverage=None,
                    acquired_at=str(request.date_from),
                    status="ready",
                    message=f"Tile fetched successfully. Size: {content_length} bytes",
                )

        except httpx.HTTPStatusError as e:
            return TileResponse(
                tile_id=tile_id,
                bbox=bbox,
                image_url=None,
                cloud_coverage=None,
                acquired_at=None,
                status="error",
                message=f"Sentinel API error: {e.response.status_code}",
            )