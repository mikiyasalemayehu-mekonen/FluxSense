# apps/api/app/services/risk_engine.py

from dataclasses import dataclass


# Weight of each signal in the final score (must sum to 1.0)
WEIGHTS = {
    "vegetation": 0.25,   # low vegetation = higher risk
    "water":      0.30,   # high water coverage = flood risk
    "urban":      0.20,   # urban exposure amplifies damage
    "event":      0.25,   # NLP event classification confidence
}

# NLP event type → base risk contribution (0-100)
EVENT_RISK_MAP = {
    "flooding":            90,
    "hurricane or cyclone": 85,
    "landslide":           80,
    "wildfire":            75,
    "earthquake":          70,
    "drought":             55,
    "normal conditions":   10,
}


@dataclass
class RiskScore:
    overall_score:    float   # 0-100
    vegetation_score: float
    water_score:      float
    urban_exposure:   float
    event_score:      float
    trend:            str     # "rising" | "stable" | "falling"
    label:            str     # "low" | "moderate" | "high" | "critical"
    explanation:      str


class RiskEngine:
    """
    Computes a composite risk score from segmentation,
    detection, and NLP analysis results.
    """

    def compute(
        self,
        class_coverage: dict,
        event_type: str,
        event_confidence: float,
        historical_scores: list[float],
    ) -> RiskScore:

        # ── 1. Vegetation score ───────────────────────────────────────
        # Low vegetation in a normally green area = stress/drought signal
        veg_pct = class_coverage.get("vegetation", 0)
        vegetation_score = max(0, 100 - (veg_pct * 2.5))

        # ── 2. Water score ────────────────────────────────────────────
        # Any water coverage above baseline is a flood indicator
        water_pct = class_coverage.get("water", 0)
        water_score = min(100, water_pct * 8)

        # ── 3. Urban exposure ─────────────────────────────────────────
        # Urban areas amplify damage when other risk factors are present
        urban_pct = class_coverage.get("urban", 0)
        urban_exposure = min(100, urban_pct * 1.1)

        # ── 4. Event score ────────────────────────────────────────────
        base_event_risk = EVENT_RISK_MAP.get(event_type, 20)
        event_score = base_event_risk * event_confidence

        # ── 5. Weighted composite ─────────────────────────────────────
        overall = (
            vegetation_score * WEIGHTS["vegetation"] +
            water_score      * WEIGHTS["water"] +
            urban_exposure   * WEIGHTS["urban"] +
            event_score      * WEIGHTS["event"]
        )
        overall = round(min(100, max(0, overall)), 2)

        # ── 6. Trend from historical scores ───────────────────────────
        trend = self._compute_trend(historical_scores + [overall])

        # ── 7. Risk label ─────────────────────────────────────────────
        label = self._score_to_label(overall)

        explanation = (
            f"Score driven by {round(urban_exposure)}% urban exposure, "
            f"{round(veg_pct)}% vegetation coverage, "
            f"{round(water_pct)}% water presence, "
            f"and '{event_type}' event signal ({round(event_confidence*100)}% confidence)."
        )

        return RiskScore(
            overall_score=overall,
            vegetation_score=round(vegetation_score, 2),
            water_score=round(water_score, 2),
            urban_exposure=round(urban_exposure, 2),
            event_score=round(event_score, 2),
            trend=trend,
            label=label,
            explanation=explanation,
        )

    def _compute_trend(self, scores: list[float]) -> str:
        if len(scores) < 3:
            return "stable"
        recent   = scores[-3:]
        slope    = (recent[-1] - recent[0]) / 2
        if slope > 3:
            return "rising"
        elif slope < -3:
            return "falling"
        return "stable"

    def _score_to_label(self, score: float) -> str:
        if score >= 70:
            return "critical"
        elif score >= 50:
            return "high"
        elif score >= 30:
            return "moderate"
        return "low"