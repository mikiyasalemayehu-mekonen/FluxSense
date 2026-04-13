# apps/api/app/ml/doc_qa.py

import httpx
import os
import io
from dataclasses import dataclass

HF_API_URL = "https://api-inference.huggingface.co/models"
HF_TOKEN   = os.getenv("HF_API_TOKEN", "")


@dataclass
class QAResult:
    answer:       str
    score:        float
    context_used: str


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    import pypdf
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    pages  = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


class DocumentQA:
    """Document QA via HuggingFace Inference API — no local model."""

    def extract_text(self, pdf_bytes: bytes) -> str:
        return extract_text_from_pdf(pdf_bytes)

    def answer(self, question: str, context: str) -> QAResult:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self._answer_async(question, context)
        )

    async def _answer_async(self, question: str, context: str) -> QAResult:
        chunk = self._find_best_chunk(question, context)

        headers = {
            "Authorization": f"Bearer {HF_TOKEN}",
            "Content-Type":  "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{HF_API_URL}/deepset/roberta-base-squad2",
                    headers=headers,
                    json={"inputs": {"question": question, "context": chunk}},
                )
                if resp.status_code == 503:
                    import asyncio
                    await asyncio.sleep(20)
                    resp = await client.post(
                        f"{HF_API_URL}/deepset/roberta-base-squad2",
                        headers=headers,
                        json={"inputs": {"question": question, "context": chunk}},
                    )
                resp.raise_for_status()
                result = resp.json()
                return QAResult(
                    answer=result.get("answer", "No answer found."),
                    score=round(result.get("score", 0.0), 4),
                    context_used=chunk[:300] + "...",
                )
        except Exception as e:
            return QAResult(
                answer=f"QA service unavailable: {str(e)}",
                score=0.0,
                context_used=chunk[:300] + "...",
            )

    def _find_best_chunk(self, question: str, context: str, chunk_size: int = 2000) -> str:
        if len(context) <= chunk_size:
            return context
        question_words = set(question.lower().split())
        step   = chunk_size // 2
        chunks = [context[i:i + chunk_size] for i in range(0, len(context), step) if context[i:i + chunk_size]]
        return max(chunks, key=lambda c: len(question_words & set(c.lower().split())))