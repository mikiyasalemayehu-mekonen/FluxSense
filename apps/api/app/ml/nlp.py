# apps/api/app/ml/nlp.py

from dataclasses import dataclass

EVENT_LABELS = [
    "flooding", "wildfire", "drought",
    "earthquake", "hurricane or cyclone",
    "landslide", "normal conditions",
]


@dataclass
class NLPResult:
    summary:          str
    event_type:       str
    event_confidence: float
    sources:          list[dict]
    raw_texts:        list[str]


class NLPAnalyser:
    """Runs NLP via HuggingFace Inference API — no local model needed."""

    def analyse(self, reports: list[dict]) -> NLPResult:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self._analyse_async(reports)
        )

    async def _analyse_async(self, reports: list[dict]) -> NLPResult:
        from app.ml.hf_client import run_summarization, run_zero_shot

        if not reports:
            return NLPResult(
                summary="No recent situation reports found for this region.",
                event_type="normal conditions",
                event_confidence=0.5,
                sources=[],
                raw_texts=[],
            )

        combined = " ".join(
            f"{r['title']}. {r['body']}"
            for r in reports if r.get("body")
        )[:1024]

        try:
            summary = await run_summarization(combined)
        except Exception as e:
            print(f"[NLP] Summarization failed: {e}")
            summary = combined[:200]

        try:
            clf    = await run_zero_shot(summary, EVENT_LABELS)
            event_type       = clf["labels"][0]
            event_confidence = round(clf["scores"][0], 4)
        except Exception as e:
            print(f"[NLP] Classification failed: {e}")
            event_type       = "normal conditions"
            event_confidence = 0.5

        sources = [
            {"title": r["title"], "url": r["url"], "source": r["source"]}
            for r in reports
        ]

        return NLPResult(
            summary=summary,
            event_type=event_type,
            event_confidence=event_confidence,
            sources=sources,
            raw_texts=[r["body"] for r in reports if r.get("body")],
        )