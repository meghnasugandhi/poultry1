from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.rag_service import RAGService

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/query")
async def query_rag(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    question = str(payload.get("question") or "").strip()
    if not question:
        return {"answer": "Please ask a question so I can retrieve the relevant context."}
    service = RAGService()
    prompt = await service.augment_prompt(db, current_user.id, question)
    return {
        "answer": f"Retrieved context prepared for: {question}",
        "prompt": prompt,
    }
