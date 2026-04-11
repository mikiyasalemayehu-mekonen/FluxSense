# apps/api/app/ml/nlp.py

from dataclasses import dataclass
from transformers import pipeline
import torch

# BART for summarization — lightweight, fast, good quality
# SUMMARIZATION_MODEL = "facebook/bart-large-cnn"

# # Zero-shot classification using a NLI model
# # No training data needed — just define your labels
# ZEROSHOT_MODEL = "facebook/bart-large-mnli"
# Replace these two lines
# SUMMARIZATION_MODEL = "facebook/bart-large-cnn"       # 1.6GB ❌
# ZEROSHOT_MODEL      = "facebook/bart-large-mnli"      # 1.6GB ❌

# With these — same results, fraction of the RAM
SUMMARIZATION_MODEL = "facebook/bart-base"          # 140MB vs 300MB
ZEROSHOT_MODEL      = "typeform/distilbert-base-uncased-mnli"  # 250MB

# Risk event labels we care about
EVENT_LABELS = [
    "flooding",
    "wildfire",
    "drought",
    "earthquake",
    "hurricane or cyclone",
    "landslide",
    "normal conditions",
]


@dataclass
class NLPResult:
    summary: str
    event_type: str
    event_confidence: float
    sources: list[dict]
    raw_texts: list[str]


class NLPAnalyser:
    """
    Summarizes situation reports and classifies event type.
    Pipelines are loaded once and cached as class attributes.
    """
    _summarizer = None
    _classifier = None

    @classmethod
    def _load_models(cls):
        if cls._summarizer is None:
            print("[NLP] Loading summarization model...")
            cls._summarizer = pipeline(
                "summarization",
                model=SUMMARIZATION_MODEL,
                device=-1,          # CPU
                torch_dtype=torch.float32,
            )
            print("[NLP] Loading zero-shot classifier...")
            cls._classifier = pipeline(
                "zero-shot-classification",
                model=ZEROSHOT_MODEL,
                device=-1,
            )
            print("[NLP] Models loaded.")

    def analyse(self, reports: list[dict]) -> NLPResult:
        self._load_models()

        if not reports:
            return NLPResult(
                summary="No recent situation reports found for this region.",
                event_type="normal conditions",
                event_confidence=0.5,
                sources=[],
                raw_texts=[],
            )

        # 1. Concatenate report bodies into one input text
        combined = " ".join(
            f"{r['title']}. {r['body']}"
            for r in reports
            if r.get("body")
        )

        # BART has a 1024 token limit — truncate combined text safely
        combined = combined[:3000]

        # 2. Summarize
        summary_result = self._summarizer(
            combined,
            max_length=180,
            min_length=60,
            do_sample=False,
        )
        summary = summary_result[0]["summary_text"]

        # 3. Zero-shot classify — what type of event is this?
        classification = self._classifier(
            summary,
            candidate_labels=EVENT_LABELS,
        )
        event_type       = classification["labels"][0]
        event_confidence = round(classification["scores"][0], 4)

        sources = [
            {"title": r["title"], "url": r["url"], "source": r["source"]}
            for r in reports
        ]
        raw_texts = [r["body"] for r in reports if r.get("body")]

        return NLPResult(
            summary=summary,
            event_type=event_type,
            event_confidence=event_confidence,
            sources=sources,
            raw_texts=raw_texts,
        )