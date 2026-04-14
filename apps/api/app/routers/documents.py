# apps/api/app/routers/documents.py

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.ml.doc_qa import DocumentQA
from app.models.satellite import QAResponse

router = APIRouter(prefix="/documents", tags=["documents"])

_doc_qa = DocumentQA()

@router.post("/qa", response_model=QAResponse)
async def document_question_answer(
    question: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Upload a PDF and ask a natural language question about its contents.
    Example: 'Which districts have inadequate drainage?'
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    pdf_bytes = await file.read()

    if len(pdf_bytes) > 10 * 1024 * 1024:   # 10MB limit
        raise HTTPException(status_code=400, detail="PDF too large. Max 10MB.")

    context = _doc_qa.extract_text(pdf_bytes)

    if not context.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from PDF.")

    result = await _doc_qa.answer(question, context)

    return QAResponse(
        question=question,
        answer=result.answer,
        score=result.score,
        context_used=result.context_used,
    )