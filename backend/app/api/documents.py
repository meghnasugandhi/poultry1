from datetime import date
from pydantic import BaseModel

from app.models.inventory import InventoryItem, InventoryCategory, StockMovement
from app.models.finance import Transaction, TransactionType, ExpenseCategory

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.document import Document, DocumentType
from app.models.finance import Transaction, TransactionType, ExpenseCategory, RevenueCategory, SuggestedTransaction
from app.models.user import User
from app.schemas.document import DocumentClarification, DocumentResponse
from app.services.ocr_service import process_document_ocr

router = APIRouter(prefix="/documents", tags=["Document Management"])

CONFIDENCE_THRESHOLD = 0.90


def _infer_document_type(raw_text: str, filename: str) -> DocumentType:
    text = f"{raw_text} {filename or ''}".lower()
    if any(keyword in text for keyword in ["medicine", "drug", "tablet", "chemicals"]):
        return DocumentType.MEDICINE_BILL
    if any(keyword in text for keyword in ["feed", "fodder", "broiler feed", "layer feed"]):
        return DocumentType.FEED_BILL
    if any(keyword in text for keyword in ["vaccine", "vaccination", "vaccine bill"]):
        return DocumentType.VACCINE_BILL
    if any(keyword in text for keyword in ["sales invoice", "invoice", "sale", "revenue"]):
        return DocumentType.SALES_INVOICE
    if any(keyword in text for keyword in ["purchase receipt", "receipt", "purchase", "supplier", "vendor"]):
        return DocumentType.PURCHASE_RECEIPT
    return DocumentType.PURCHASE_RECEIPT


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    document_type: DocumentType | None = Form(None),
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

    if document_type is None:
        document_type = _infer_document_type(ocr_result.get("raw_text", ""), file.filename or "")

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
    # If OCR parsed key fields and confidence is high, create a suggested transaction (for review)
    try:
        from datetime import date as _date
        if doc.ocr_confidence and doc.ocr_confidence >= CONFIDENCE_THRESHOLD and doc.cost:
            tx_date = doc.invoice_date or _date.today()
            if document_type in (DocumentType.FEED_BILL, DocumentType.PURCHASE_RECEIPT):
                st = SuggestedTransaction(
                    user_id=current_user.id,
                    document_id=doc.id,
                    transaction_type=TransactionType.EXPENSE,
                    expense_category=ExpenseCategory.FEED if document_type == DocumentType.FEED_BILL else ExpenseCategory.MISCELLANEOUS,
                    amount=doc.cost,
                    description=f"Parsed from {doc.original_filename}",
                    transaction_date=tx_date,
                )
                db.add(st)
                await db.flush()
            elif document_type == DocumentType.MEDICINE_BILL:
                st = SuggestedTransaction(
                    user_id=current_user.id,
                    document_id=doc.id,
                    transaction_type=TransactionType.EXPENSE,
                    expense_category=ExpenseCategory.MEDICINES,
                    amount=doc.cost,
                    description=f"Parsed from {doc.original_filename}",
                    transaction_date=tx_date,
                )
                db.add(st)
                await db.flush()
            elif document_type == DocumentType.SALES_INVOICE:
                rc = RevenueCategory.BIRD_SALES
                if doc.product_name and 'egg' in (doc.product_name or '').lower():
                    rc = RevenueCategory.EGG_SALES
                st = SuggestedTransaction(
                    user_id=current_user.id,
                    document_id=doc.id,
                    transaction_type=TransactionType.REVENUE,
                    revenue_category=rc,
                    amount=doc.cost,
                    description=f"Parsed from {doc.original_filename}",
                    transaction_date=tx_date,
                )
                db.add(st)
                await db.flush()
    except Exception:
        # Do not block document upload if suggestion creation fails
        pass

    return doc


class DocumentProcessRequest(BaseModel):
    add_inventory: bool = True
    add_finance: bool = True


@router.post("/{doc_id}/process")
async def process_document(
    doc_id: int,
    payload: DocumentProcessRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    response: dict = {}

    # Add to inventory
    if payload.add_inventory:
        qty = doc.quantity or doc.number_of_bags or 1
        # determine category
        if doc.document_type == DocumentType.VACCINE_BILL:
            cat = InventoryCategory.VACCINE
        elif doc.document_type == DocumentType.MEDICINE_BILL:
            cat = InventoryCategory.MEDICINE
        else:
            cat = InventoryCategory.FEED

        product_name = doc.product_name or (doc.original_filename or "Document Item")

        existing = await db.execute(
            select(InventoryItem).where(
                InventoryItem.user_id == current_user.id,
                InventoryItem.product_name == product_name,
                InventoryItem.category == cat,
            )
        )
        item = existing.scalar_one_or_none()
        if item:
            item.quantity = (item.quantity or 0) + float(qty)
        else:
            unit = "pack" if "pack" in (doc.original_filename or "").lower() else "kg"
            item = InventoryItem(
                user_id=current_user.id,
                category=cat,
                product_name=product_name,
                quantity=float(qty),
                unit=unit,
                number_of_bags=doc.number_of_bags,
                supplier_name=doc.supplier_name,
                cost_per_unit=(doc.cost or None),
            )
            db.add(item)
            await db.flush()

        movement = StockMovement(item_id=item.id, change_amount=float(qty), reason="Added from document upload", notes=f"Document ID {doc.id}")
        db.add(movement)
        await db.flush()
        response["inventory"] = {"item_id": item.id, "quantity": item.quantity}

    # Add to finance
    if payload.add_finance and doc.cost:
        if doc.document_type == DocumentType.VACCINE_BILL:
            exp_cat = ExpenseCategory.VACCINES
        elif doc.document_type == DocumentType.MEDICINE_BILL:
            exp_cat = ExpenseCategory.MEDICINES
        elif doc.document_type == DocumentType.FEED_BILL:
            exp_cat = ExpenseCategory.FEED
        else:
            exp_cat = ExpenseCategory.MISCELLANEOUS

        tx_date = doc.invoice_date or date.today()
        tx = Transaction(
            user_id=current_user.id,
            transaction_type=TransactionType.EXPENSE,
            expense_category=exp_cat,
            amount=doc.cost,
            description=f"From document {doc.original_filename}",
            transaction_date=tx_date,
        )
        db.add(tx)
        await db.flush()
        response["finance"] = {"transaction_id": tx.id, "amount": tx.amount}

    await db.flush()
    return response


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


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
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

    await db.delete(doc)
    await db.flush()
    return None


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
