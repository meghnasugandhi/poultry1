import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.poultry_agent import PoultryAgent
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.document import Document, DocumentType
from app.models.notification import ChatMessage, ChatSession
from app.models.user import User
from app.schemas.assistant import ChatRequest, ChatResponse
from app.services.ingest_service import ingest_document
from app.services.ocr_service import process_document_ocr

router = APIRouter(prefix="/assistant", tags=["AI Assistant"])

CONFIDENCE_THRESHOLD = 0.90

SUGGESTED_QUESTIONS = [
    "How much feed stock remains?",
    "What was my feed expense last month?",
    "Show overall profit.",
    "Add 50 kg broiler feed",
    "Sold 20 birds for 5000",
    "What stock is running low?",
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


@router.post("/upload", response_model=ChatResponse)
async def upload_and_ingest(
    file: UploadFile = File(...),
    message: str = Form(""),
    session_id: int | None = Form(None),
    language: str = Form("en"),
    document_type: str = Form("feed_bill"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept a bill/image/PDF, run OCR, and automatically create the document,
    expense/revenue and inventory records — the multi-modal 'read this and add it'."""
    try:
        doc_type = DocumentType(document_type)
    except ValueError:
        doc_type = DocumentType.FEED_BILL

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "file")[1]
    file_path = os.path.join(settings.UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    ocr_result = await process_document_ocr(file_path)
    confidence = ocr_result.get("confidence", 0)
    needs_clarification = confidence < CONFIDENCE_THRESHOLD

    doc = Document(
        user_id=current_user.id,
        document_type=doc_type,
        file_path=file_path,
        original_filename=file.filename or "upload",
        company_name=ocr_result.get("company_name"),
        product_name=ocr_result.get("product_name"),
        quantity=ocr_result.get("quantity"),
        number_of_bags=ocr_result.get("number_of_bags"),
        cost=ocr_result.get("cost"),
        invoice_date=ocr_result.get("invoice_date"),
        invoice_number=ocr_result.get("invoice_number"),
        supplier_name=ocr_result.get("supplier_name"),
        ocr_confidence=confidence,
        needs_clarification=needs_clarification,
        raw_ocr_text=ocr_result.get("raw_text"),
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    actions = await ingest_document(db, current_user, doc)

    lines = [f"I read \"{file.filename}\" ({doc_type.value.replace('_', ' ')})."]
    if actions:
        lines.append("Here's what I added automatically:")
        lines.extend(f"• {a}" for a in actions)
    else:
        lines.append("I couldn't confidently extract amounts or items from this file.")
    if needs_clarification:
        lines.append(
            f"OCR confidence was {confidence * 100:.0f}% (below 90%). "
            "Please review it on the Documents page and correct any fields if needed."
        )
    response_text = "\n".join(lines)

    if session_id:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id, ChatSession.user_id == current_user.id
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = ChatSession(user_id=current_user.id, title=(file.filename or "Uploaded bill")[:50])
        db.add(session)
        await db.flush()

    user_text = message.strip() or f"Uploaded {file.filename}"
    db.add(ChatMessage(session_id=session.id, role="user", content=user_text))
    db.add(
        ChatMessage(
            session_id=session.id,
            role="assistant",
            content=response_text,
            language=language,
        )
    )
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
