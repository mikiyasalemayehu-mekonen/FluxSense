# apps/api/app/routers/risk.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from app.core.database import get_db
from app.models.satellite import RiskResponse, RiskBreakdown, RiskForecast, ForecastPoint, BoundingBox
from app.services.risk_repository import RiskRepository
from app.services.risk_engine import RiskEngine
from app.services.forecaster import Forecaster

router = APIRouter(prefix="/risk", tags=["risk"])

_forecaster = Forecaster()
_engine     = RiskEngine()


@router.get("/forecast", response_model=RiskResponse)
async def get_risk_forecast(
    min_lon: float, min_lat: float,
    max_lon: float, max_lat: float,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns current risk score, 7-day forecast, and
    historical scores for a bounding box.
    """
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
        }

    # Most recent score is current
    latest = history[0]
    current = RiskBreakdown(
        overall_score=    latest["overall_score"],
        label=            _engine._score_to_label(latest["overall_score"]),
        trend=            latest["trend"],
        vegetation_score= latest["vegetation_score"],
        water_score=      latest["water_score"],
        urban_exposure=   latest["urban_exposure"],
        event_score=      latest["event_score"],
        explanation=      f"Based on {len(history)} historical observations.",
    )

    # Forecast from historical scores
    scores = [h["overall_score"] for h in reversed(history)]
    dates  = [h["acquired_at"] for h in reversed(history)]

    # Convert dates to date objects if needed
    parsed_dates = [
        d if isinstance(d, date) else date.fromisoformat(str(d)[:10])
        for d in dates
    ]

    forecast_result = _forecaster.forecast(scores, parsed_dates)
    forecast = RiskForecast(
        points=[
            ForecastPoint(date=d, score=s)
            for d, s in zip(forecast_result.dates, forecast_result.scores)
        ],
        trend=           forecast_result.trend,
        peak_risk_date=  forecast_result.peak_risk_date,
        confidence=      forecast_result.confidence,
    )

    return RiskResponse(
        tile_id= str(latest["tile_id"]),
        bbox=    BoundingBox(
                    min_lon=min_lon, min_lat=min_lat,
                    max_lon=max_lon, max_lat=max_lat,
                 ),
        current= current,
        forecast=forecast,
        history= history,
    )