# apps/api/app/services/report_fetcher.py

import httpx
from app.models.satellite import BoundingBox

RELIEFWEB_URL = "https://api.reliefweb.int/v1/reports"
USGS_WATER_URL = "https://waterservices.usgs.gov/nwis/iv"


class ReportFetcher:
    """
    Fetches situation reports and sensor data for a geographic area.
    Both APIs are free with no authentication required.
    """

    async def fetch_all(self, bbox: BoundingBox) -> list[dict]:
        """Returns a list of {title, url, body, source} dicts."""
        reports = []
        rw = await self._fetch_reliefweb(bbox)
        usgs = await self._fetch_usgs_water(bbox)
        reports.extend(rw)
        reports.extend(usgs)
        return reports

    async def _fetch_reliefweb(self, bbox: BoundingBox) -> list[dict]:
        """
        ReliefWeb full-text search API.
        Searches for reports mentioning flood, wildfire, drought, or disaster
        within the last 90 days. Returns up to 5 most relevant.
        """
        payload = {
            "limit": 5,
            "fields": {
                "include": ["title", "url", "body", "date", "source"]
            },
            "filter": {
                "operator": "AND",
                "conditions": [
                    {
                        "field": "date.created",
                        "value": {"from": "now-90d/d"},
                    },
                ],
            },
            "query": {
                "value": "flood OR wildfire OR drought OR disaster OR cyclone",
                "fields": ["title", "body"],
            },
            "sort": ["date:desc"],
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    RELIEFWEB_URL,
                    json=payload,
                    headers={"User-Agent": "FluxSense/1.0"},
                )
                resp.raise_for_status()
                data = resp.json()

            results = []
            for item in data.get("data", []):
                fields = item.get("fields", {})
                body = fields.get("body", "")
                # Truncate to 800 chars — enough context for summarization
                results.append({
                    "title":  fields.get("title", "Untitled"),
                    "url":    fields.get("url", ""),
                    "body":   body[:800] if body else "",
                    "source": "ReliefWeb",
                })
            return results

        except Exception as e:
            print(f"[ReportFetcher] ReliefWeb error: {e}")
            return []

    async def _fetch_usgs_water(self, bbox: BoundingBox) -> list[dict]:
        """
        USGS Instantaneous Water Services — stream gauge readings.
        Returns current discharge (flow rate) readings for gauges
        within the bounding box. High discharge = flood risk signal.
        """
        params = {
            "format":      "json",
            "bBox":        f"{bbox.min_lon},{bbox.min_lat},{bbox.max_lon},{bbox.max_lat}",
            "parameterCd": "00060",   # discharge in cubic feet/sec
            "siteStatus":  "active",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(USGS_WATER_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

            sites = data.get("value", {}).get("timeSeries", [])
            results = []
            for site in sites[:3]:   # max 3 gauges
                site_name = site.get("sourceInfo", {}).get("siteName", "Unknown")
                values    = site.get("values", [{}])[0].get("value", [])
                latest    = values[-1].get("value", "N/A") if values else "N/A"
                unit      = site.get("variable", {}).get("unit", {}).get("unitCode", "")
                results.append({
                    "title":  f"USGS gauge: {site_name}",
                    "url":    "",
                    "body":   f"Current discharge reading: {latest} {unit}. "
                              f"Location: {site_name}.",
                    "source": "USGS Water Services",
                })
            return results

        except Exception as e:
            print(f"[ReportFetcher] USGS error: {e}")
            return []