from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.document import Document, DocumentType
from app.models.user import User
from app.schemas.document import DocumentClarification, DocumentResponse
from app.services.ocr_service import process_document_ocr

router = APIRouter(prefix="/documents", tags=["Document Management"])

CONFIDENCE_THRESHOLD = 0.90


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import os
    import uuid

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "file")[1]
    file_path = os.path.join(settings.UPLOAD_DIR, f"{uuid.uuid4()}{ext}")

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    ocr_result = await process_document_ocr(file_path)

    confidence = ocr_result.get("confidence", 0)
    needs_clarification = confidence < CONFIDENCE_THRESHOLD

    doc = Document(
        user_id=current_user.id,
        document_type=document_type,
        file_path=file_path,
        original_filename=file.filename or "unknown",
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
    return doc


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    document_type: DocumentType | None = None,
    search: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Document).where(Document.user_id == current_user.id)
    if document_type:
        query = query.where(Document.document_type == document_type)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            (Document.company_name.ilike(pattern))
            | (Document.product_name.ilike(pattern))
            | (Document.supplier_name.ilike(pattern))
            | (Document.invoice_number.ilike(pattern))
        )
    query = query.order_by(Document.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.put("/{doc_id}/clarify", response_model=DocumentResponse)
async def clarify_document(
    doc_id: int,
    data: DocumentClarification,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(doc, field, value)
    doc.needs_clarification = False
    await db.flush()
    await db.refresh(doc)
    return doc


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import os

    from fastapi.responses import FileResponse

    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(doc.file_path, filename=doc.original_filename)


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
