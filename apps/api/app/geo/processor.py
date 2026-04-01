# packages/geo/processor.py

import io
import uuid
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds
from rasterio.enums import Resampling
from PIL import Image
from pathlib import Path
from dataclasses import dataclass

@dataclass
class ProcessedTile:
    tile_id: str
    file_path: str
    width: int
    height: int
    band_stats: dict      # min, max, mean per band
    wkt_polygon: str      # WKT for PostGIS insert


class GeoProcessor:
    """
    Converts raw satellite PNG bytes from Sentinel Hub
    into a normalized, georeferenced tile stored on disk.
    """

    def __init__(self, output_dir: str = "data/tiles"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def process(
        self,
        raw_bytes: bytes,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
    ) -> ProcessedTile:
        tile_id = str(uuid.uuid4())

        # 1. Load raw PNG into numpy array
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        arr = np.array(img, dtype=np.float32)   # shape: (H, W, 3)

        # 2. Normalize each band to 0–1 range
        #    Sentinel-2 reflectance values can be blown out — normalize properly
        normalized = self._normalize_bands(arr)

        # 3. Compute per-band statistics (useful for risk analysis later)
        band_stats = self._compute_stats(normalized)

        # 4. Save as GeoTIFF (georeferenced raster)
        geotiff_path = self._save_geotiff(
            normalized, tile_id, min_lon, min_lat, max_lon, max_lat
        )

        # 5. Also save a viewport-ready PNG for the frontend
        self._save_preview_png(normalized, tile_id)

        # 6. Build WKT polygon for PostGIS
        wkt = (
            f"POLYGON(("
            f"{min_lon} {min_lat}, "
            f"{max_lon} {min_lat}, "
            f"{max_lon} {max_lat}, "
            f"{min_lon} {max_lat}, "
            f"{min_lon} {min_lat}"
            f"))"
        )

        h, w = normalized.shape[:2]
        return ProcessedTile(
            tile_id=tile_id,
            file_path=str(geotiff_path),
            width=w,
            height=h,
            band_stats=band_stats,
            wkt_polygon=wkt,
        )

    def _normalize_bands(self, arr: np.ndarray) -> np.ndarray:
        """
        Per-band percentile stretch (2nd–98th percentile).
        Much better than simple 0-255 normalization for satellite imagery
        because clouds and shadows skew the histogram heavily.
        """
        result = np.zeros_like(arr, dtype=np.float32)
        for i in range(arr.shape[2]):
            band = arr[:, :, i]
            p2  = np.percentile(band, 2)
            p98 = np.percentile(band, 98)
            if p98 > p2:
                result[:, :, i] = np.clip((band - p2) / (p98 - p2), 0, 1)
            else:
                result[:, :, i] = band / 255.0
        return result

    def _compute_stats(self, arr: np.ndarray) -> dict:
        band_names = ["red", "green", "blue"]
        stats = {}
        for i, name in enumerate(band_names):
            band = arr[:, :, i]
            stats[name] = {
                "min":  round(float(band.min()), 4),
                "max":  round(float(band.max()), 4),
                "mean": round(float(band.mean()), 4),
                "std":  round(float(band.std()), 4),
            }
        return stats

    def _save_geotiff(
        self,
        arr: np.ndarray,
        tile_id: str,
        min_lon: float, min_lat: float,
        max_lon: float, max_lat: float,
    ) -> Path:
        """
        Write a georeferenced GeoTIFF — each pixel maps to real-world coordinates.
        This is what Phase 3 model inference will consume.
        """
        h, w = arr.shape[:2]
        transform = from_bounds(min_lon, min_lat, max_lon, max_lat, w, h)

        path = self.output_dir / f"{tile_id}.tif"
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=h,
            width=w,
            count=3,                    # RGB bands
            dtype=rasterio.float32,
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            for i in range(3):
                # rasterio uses band-first ordering (C, H, W)
                dst.write(arr[:, :, i], i + 1)

        return path

    def _save_preview_png(self, arr: np.ndarray, tile_id: str) -> Path:
        """
        8-bit PNG for the frontend map overlay.
        Converts normalized 0–1 float back to 0–255 uint8.
        """
        preview = (arr * 255).astype(np.uint8)
        img = Image.fromarray(preview, mode="RGB")
        path = self.output_dir / f"{tile_id}_preview.png"
        img.save(path, format="PNG", optimize=True)
        return path