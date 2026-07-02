import json
from types import SimpleNamespace

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.poultry_agent import PoultryAgent
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.notification import ChatMessage, ChatSession
from app.models.user import User
from app.schemas.assistant import ChatRequest, ChatResponse
from app.services.translation_service import translate_text

router = APIRouter(prefix="/assistant", tags=["AI Assistant"])

SUGGESTED_QUESTIONS = [
    "How much feed stock remains?",
    "What was my feed expense last month?",
    "Show overall profit.",
    "Calculate FCR.",
    "Generate inventory report PDF.",
]


def _is_database_locked(exc: OperationalError) -> bool:
    return "database is locked" in str(exc).lower()


async def _chat_without_history(
    data: ChatRequest,
    user_id: int,
    preferred_language: str,
    voice_enabled: bool,
    db: AsyncSession,
) -> ChatResponse:
    await db.rollback()
    fallback_user = SimpleNamespace(
        id=user_id,
        preferred_language=SimpleNamespace(value=preferred_language),
        voice_enabled=voice_enabled,
    )
    agent = PoultryAgent(user=fallback_user, db=db)
    lang = data.language or preferred_language
    response_text = await agent._route_intent(data.message.lower())
    if response_text == agent._default_response() and lang != "en":
        response_text = translate_text(response_text, lang)
    return ChatResponse(
        session_id=data.session_id or 0,
        message=response_text,
        suggested_questions=SUGGESTED_QUESTIONS,
        voice_enabled=voice_enabled,
    )


async def _stream_response(agent: PoultryAgent, message: str, language: str, session_id: int | None) -> str:
    yield f"data: {json.dumps({'session_id': session_id, 'chunk': ''})}\n\n"
    response_text = ""
    try:
        async for chunk in agent.process_message_stream(message, language=language, session_id=session_id):
            response_text += chunk
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
    except AttributeError:
        response_text = await agent.process_message(message, language=language, session_id=session_id)
        yield f"data: {json.dumps({'chunk': response_text})}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/chat", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = current_user.id
    preferred_language = current_user.preferred_language.value
    voice_enabled = current_user.voice_enabled
    try:
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
        response_text = await agent.process_message(data.message, language=lang, session_id=session.id)

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
    except OperationalError as exc:
        if not _is_database_locked(exc):
            raise
        return await _chat_without_history(data, user_id, preferred_language, voice_enabled, db)


@router.post("/chat/stream")
async def chat_stream(
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

    async def stream_generator():
        yield f"data: {json.dumps({'session_id': session.id, 'chunk': ''})}\n\n"
        response_text = ""
        try:
            async for chunk in agent.process_message_stream(data.message, language=lang, session_id=session.id):
                response_text += chunk
                yield f"data: {json.dumps({'session_id': session.id, 'chunk': chunk})}\n\n"
        except AttributeError:
            response_text = await agent.process_message(data.message, language=lang, session_id=session.id)
            yield f"data: {json.dumps({'session_id': session.id, 'chunk': response_text})}\n\n"

        assistant_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=response_text,
            language=data.language,
        )
        db.add(assistant_msg)
        await db.flush()
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


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
