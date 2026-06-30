from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.poultry_agent import PoultryAgent
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.notification import ChatMessage, ChatSession
from app.models.user import User
from app.schemas.assistant import ChatRequest, ChatResponse

router = APIRouter(prefix="/assistant", tags=["AI Assistant"])

SUGGESTED_QUESTIONS = [
    "How much feed stock remains?",
    "What was my feed expense last month?",
    "Show overall profit.",
    "Calculate FCR.",
    "Generate inventory report PDF.",
]


@router.post("/chat", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.session_id:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == data.session_id,
                ChatSession.user_id == current_user.id,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = ChatSession(user_id=current_user.id, title=data.message[:50])
        db.add(session)
        await db.flush()

    user_msg = ChatMessage(session_id=session.id, role="user", content=data.message)
    db.add(user_msg)

    agent = PoultryAgent(user=current_user, db=db)
    lang = data.language or current_user.preferred_language.value
    response_text = await agent.process_message(data.message, language=lang)

    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=response_text,
        language=data.language,
    )
    db.add(assistant_msg)
    await db.flush()

    return ChatResponse(
        session_id=session.id,
        message=response_text,
        suggested_questions=SUGGESTED_QUESTIONS,
        voice_enabled=current_user.voice_enabled,
    )


@router.get("/sessions")
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
    )
    return [
        {"id": s.id, "title": s.title, "created_at": s.created_at, "updated_at": s.updated_at}
        for s in result.scalars().all()
    ]


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == current_user.id
        )
    )
    if not result.scalar_one_or_none():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Session not found")

    messages = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    return [
        {"id": m.id, "role": m.role, "content": m.content, "language": m.language, "created_at": m.created_at}
        for m in messages.scalars().all()
    ]


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Session not found")

    await db.delete(session)
    await db.flush()
    return {"message": "Session deleted"}
