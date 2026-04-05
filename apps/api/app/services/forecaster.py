# apps/api/app/services/forecaster.py

import numpy as np
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class ForecastResult:
    dates:        list[str]    # ISO date strings
    scores:       list[float]  # predicted scores
    trend:        str
    peak_risk_date: str | None
    confidence:   str          # "high" | "medium" | "low"


class Forecaster:
    """
    Lightweight linear + seasonal trend forecaster.
    Uses numpy polyfit — no heavy model needed for Phase 5.
    Swap for PatchTST in Phase 7 if you want to flex ML forecasting.
    """

    def forecast(
        self,
        historical_scores: list[float],
        historical_dates: list[date],
        horizon_days: int = 7,
    ) -> ForecastResult:

        n = len(historical_scores)

        if n < 2:
            # Not enough history — return flat forecast at current score
            base = historical_scores[-1] if historical_scores else 30.0
            last_date = historical_dates[-1] if historical_dates else date.today()
            future_dates = [last_date + timedelta(days=i+1) for i in range(horizon_days)]
            return ForecastResult(
                dates=[d.isoformat() for d in future_dates],
                scores=[round(base, 2)] * horizon_days,
                trend="stable",
                peak_risk_date=None,
                confidence="low",
            )

        # Fit a linear trend to historical scores
        x = np.arange(n, dtype=float)
        y = np.array(historical_scores, dtype=float)
        coeffs = np.polyfit(x, y, deg=min(2, n - 1))
        poly   = np.poly1d(coeffs)

        # Project forward
        future_x      = np.arange(n, n + horizon_days, dtype=float)
        raw_forecast   = poly(future_x)
        clamped        = np.clip(raw_forecast, 0, 100)
        forecast_scores = [round(float(v), 2) for v in clamped]

        # Future dates
        last_date    = historical_dates[-1]
        future_dates = [
            last_date + timedelta(days=i + 1)
            for i in range(horizon_days)
        ]

        # Trend direction
        slope = coeffs[0] if len(coeffs) >= 2 else 0
        if slope > 2:
            trend = "rising"
        elif slope < -2:
            trend = "falling"
        else:
            trend = "stable"

        # Peak risk date
        peak_idx = int(np.argmax(clamped))
        peak_risk_date = future_dates[peak_idx].isoformat() \
            if forecast_scores[peak_idx] > 50 else None

        confidence = "high" if n >= 5 else "medium" if n >= 3 else "low"

        return ForecastResult(
            dates=[d.isoformat() for d in future_dates],
            scores=forecast_scores,
            trend=trend,
            peak_risk_date=peak_risk_date,
            confidence=confidence,
        )