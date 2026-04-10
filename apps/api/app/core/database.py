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
        # No PostGIS — store bbox as plain text WKT
        """
        CREATE TABLE IF NOT EXISTS satellite_tiles (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            bbox_wkt        TEXT NOT NULL,
            min_lon         FLOAT NOT NULL,
            min_lat         FLOAT NOT NULL,
            max_lon         FLOAT NOT NULL,
            max_lat         FLOAT NOT NULL,
            acquired_at     DATE NOT NULL,
            resolution_m    INTEGER NOT NULL,
            cloud_coverage  FLOAT,
            file_path       TEXT NOT NULL,
            band_stats      JSONB,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )
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
            class_coverage  JSONB,
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
            detections      JSONB,
            object_count    INTEGER,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_det_tile_id
            ON detection_results (tile_id)
        """,
        """
        CREATE TABLE IF NOT EXISTS nlp_results (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tile_id          UUID REFERENCES satellite_tiles(id) ON DELETE CASCADE,
            sources          JSONB,
            summary          TEXT,
            event_type       TEXT,
            event_confidence FLOAT,
            raw_texts        JSONB,
            created_at       TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_nlp_tile_id
            ON nlp_results (tile_id)
        """,
        """
        CREATE TABLE IF NOT EXISTS risk_scores (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tile_id          UUID REFERENCES satellite_tiles(id) ON DELETE CASCADE,
            min_lon          FLOAT NOT NULL,
            min_lat          FLOAT NOT NULL,
            max_lon          FLOAT NOT NULL,
            max_lat          FLOAT NOT NULL,
            overall_score    FLOAT NOT NULL,
            vegetation_score FLOAT,
            water_score      FLOAT,
            urban_exposure   FLOAT,
            event_score      FLOAT,
            trend            TEXT,
            acquired_at      DATE NOT NULL,
            created_at       TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_risk_tile_id
            ON risk_scores (tile_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_risk_acquired
            ON risk_scores (acquired_at)
        """,
    ]

    async with engine.begin() as conn:
        for statement in statements:
            await conn.execute(text(statement))
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session