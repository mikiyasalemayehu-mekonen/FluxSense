# packages/geo/reprojector.py

from pyproj import Transformer

def reproject_bbox(
    min_lon: float, min_lat: float,
    max_lon: float, max_lat: float,
    from_crs: str = "EPSG:4326",
    to_crs: str = "EPSG:3857",
) -> tuple[float, float, float, float]:
    """
    Reproject a bounding box between coordinate systems.
    EPSG:4326 = WGS84 lat/lon (what users provide)
    EPSG:3857 = Web Mercator (what Mapbox renders)
    """
    transformer = Transformer.from_crs(from_crs, to_crs, always_xy=True)
    min_x, min_y = transformer.transform(min_lon, min_lat)
    max_x, max_y = transformer.transform(max_lon, max_lat)
    return min_x, min_y, max_x, max_y