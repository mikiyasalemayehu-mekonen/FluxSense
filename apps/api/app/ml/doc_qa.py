# apps/api/app/ml/doc_qa.py

from dataclasses import dataclass
from transformers import pipeline
import pypdf
import io


@dataclass
class QAResult:
    answer: str
    score: float
    context_used: str


class DocumentQA:
    """
    Extracts text from a PDF and answers questions using
    deepset/roberta-base-squad2 — fast, accurate, runs well on CPU.
    """
    _pipeline = None

    @classmethod
    def _load_model(cls):
        if cls._pipeline is None:
            print("[DocQA] Loading QA model...")
            cls._pipeline = pipeline(
                "question-answering",
                model="deepset/roberta-base-squad2",
                device=-1,
            )
            print("[DocQA] Model loaded.")

    def extract_text(self, pdf_bytes: bytes) -> str:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
        return "\n\n".join(pages)

    def answer(self, question: str, context: str) -> QAResult:
        self._load_model()

        # QA models have context length limits — use most relevant 2000 chars
        # Simple approach: find the paragraph most likely to contain the answer
        context_chunk = self._find_best_chunk(question, context)

        result = self._pipeline(
            question=question,
            context=context_chunk,
        )

        return QAResult(
            answer=result["answer"],
            score=round(result["score"], 4),
            context_used=context_chunk[:300] + "...",
        )

    def _find_best_chunk(self, question: str, context: str, chunk_size: int = 2000) -> str:
        """
        Splits context into overlapping chunks and returns the one
        with the most keyword overlap with the question.
        Simple but effective for document QA without a retriever.
        """
        if len(context) <= chunk_size:
            return context

        question_words = set(question.lower().split())
        chunks = []
        step = chunk_size // 2
        for i in range(0, len(context), step):
            chunk = context[i:i + chunk_size]
            if chunk:
                chunks.append(chunk)

        # Score each chunk by keyword overlap
        best_chunk = max(
            chunks,
            key=lambda c: len(question_words & set(c.lower().split())),
        )
        return best_chunk