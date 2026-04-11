# apps/api/app/routers/risk.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from app.core.database import get_db
from app.models.satellite import RiskBreakdown, RiskForecast, ForecastPoint, BoundingBox
from app.services.risk_repository import RiskRepository
from app.services.risk_engine import RiskEngine
from app.services.forecaster import Forecaster

router = APIRouter(prefix="/risk", tags=["risk"])

_forecaster = Forecaster()
_engine     = RiskEngine()


@router.get("/forecast")
async def get_risk_forecast(
    min_lon: float, min_lat: float,
    max_lon: float, max_lat: float,
    db: AsyncSession = Depends(get_db),
):
    repo    = RiskRepository(db)
    history = await repo.get_history_for_bbox(
        min_lon, min_lat, max_lon, max_lat
    )

    if not history:
        return {
            "tile_id":  "none",
            "bbox":     {"min_lon": min_lon, "min_lat": min_lat,
                         "max_lon": max_lon, "max_lat": max_lat},
            "current":  None,
            "forecast": None,
            "history":  [],
            "message":  "No risk data yet. Run a tile analysis first.",
        }

    latest = history[0]

    current = {
        "overall_score":    latest["overall_score"],
        "label":            _engine._score_to_label(latest["overall_score"]),
        "trend":            latest["trend"],
        "vegetation_score": latest["vegetation_score"],
        "water_score":      latest["water_score"],
        "urban_exposure":   latest["urban_exposure"],
        "event_score":      latest["event_score"],
        "explanation":      f"Based on {len(history)} historical observations.",
    }

    scores = [h["overall_score"] for h in reversed(history)]
    dates  = [h["acquired_at"]   for h in reversed(history)]
    parsed_dates = [
        d if isinstance(d, date) else date.fromisoformat(str(d)[:10])
        for d in dates
    ]

    fc = _forecaster.forecast(scores, parsed_dates)

    forecast = {
        "points":         [{"date": d, "score": s} for d, s in zip(fc.dates, fc.scores)],
        "trend":          fc.trend,
        "peak_risk_date": fc.peak_risk_date,
        "confidence":     fc.confidence,
    }

    return {
        "tile_id":  str(latest["tile_id"]),
        "bbox":     {"min_lon": min_lon, "min_lat": min_lat,
                     "max_lon": max_lon, "max_lat": max_lat},
        "current":  current,
        "forecast": forecast,
        "history":  [
            {k: str(v) if not isinstance(v, (int, float, str, bool, type(None))) else v
             for k, v in row.items()}
            for row in history
        ],
    }