# apps/api/app/core/database.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import text
from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


async def init_db():
    statements = [
        "CREATE EXTENSION IF NOT EXISTS postgis",

        """
        CREATE TABLE IF NOT EXISTS satellite_tiles (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            bbox            GEOMETRY(Polygon, 4326) NOT NULL,
            acquired_at     DATE NOT NULL,
            resolution_m    INTEGER NOT NULL,
            cloud_coverage  FLOAT,
            file_path       TEXT NOT NULL,
            band_stats      JSONB,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_tiles_bbox
            ON satellite_tiles USING GIST (bbox)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_tiles_acquired
            ON satellite_tiles (acquired_at)
        """,

        """
        CREATE TABLE IF NOT EXISTS segmentation_results (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tile_id         UUID REFERENCES satellite_tiles(id) ON DELETE CASCADE,
            model_name      TEXT NOT NULL,
            mask_file_path  TEXT NOT NULL,
            class_coverage  JSONB,      -- % of tile per land-cover class
            dominant_class  TEXT,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_seg_tile_id
            ON segmentation_results (tile_id)
        """,
        """
        CREATE TABLE IF NOT EXISTS detection_results (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tile_id         UUID REFERENCES satellite_tiles(id) ON DELETE CASCADE,
            model_name      TEXT NOT NULL,
            detections      JSONB,      -- array of {label, score, bbox_px}
            object_count    INTEGER,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_det_tile_id
            ON detection_results (tile_id)
        """,
    ]

    async with engine.begin() as conn:
        for statement in statements:
            await conn.execute(text(statement))
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session