# apps/api/app/core/migrations.py

TILE_TABLE_SQL = """
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS satellite_tiles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bbox            GEOMETRY(Polygon, 4326) NOT NULL,
    acquired_at     DATE NOT NULL,
    resolution_m    INTEGER NOT NULL,
    cloud_coverage  FLOAT,
    file_path       TEXT NOT NULL,
    band_stats      JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tiles_bbox
    ON satellite_tiles USING GIST (bbox);

CREATE INDEX IF NOT EXISTS idx_tiles_acquired
    ON satellite_tiles (acquired_at);
"""