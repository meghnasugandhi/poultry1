"""Turn an OCR-extracted document into finance + inventory records automatically.

Used by the AI Assistant when a farmer uploads a bill and asks to "add this".
"""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentType
from app.models.finance import (
    ExpenseCategory,
    RevenueCategory,
    Transaction,
    TransactionType,
)
from app.models.inventory import InventoryCategory, InventoryItem, StockMovement
from app.models.user import User

_DOC_TO_EXPENSE = {
    DocumentType.FEED_BILL: ExpenseCategory.FEED,
    DocumentType.MEDICINE_BILL: ExpenseCategory.MEDICINES,
    DocumentType.VACCINE_BILL: ExpenseCategory.VACCINES,
    DocumentType.PURCHASE_RECEIPT: ExpenseCategory.MISCELLANEOUS,
}

_DOC_TO_INVENTORY = {
    DocumentType.FEED_BILL: InventoryCategory.FEED,
    DocumentType.MEDICINE_BILL: InventoryCategory.MEDICINE,
    DocumentType.VACCINE_BILL: InventoryCategory.VACCINE,
}


async def ingest_document(db: AsyncSession, user: User, doc: Document) -> list[str]:
    """Create finance/inventory records from a parsed document. Returns a list
    of human-readable descriptions of what was added."""
    actions: list[str] = []
    inv_date = doc.invoice_date or date.today()
    label = doc.company_name or doc.product_name or doc.original_filename

    if doc.document_type == DocumentType.SALES_INVOICE:
        if doc.cost:
            db.add(
                Transaction(
                    user_id=user.id,
                    transaction_type=TransactionType.REVENUE,
                    revenue_category=RevenueCategory.BIRD_SALES,
                    amount=doc.cost,
                    description=f"Sales invoice: {label}",
                    transaction_date=inv_date,
                )
            )
            actions.append(f"Recorded revenue of ₹{doc.cost:,.2f}")
        return actions

    expense_cat = _DOC_TO_EXPENSE.get(doc.document_type)
    if expense_cat and doc.cost:
        db.add(
            Transaction(
                user_id=user.id,
                transaction_type=TransactionType.EXPENSE,
                expense_category=expense_cat,
                amount=doc.cost,
                description=f"{doc.document_type.value.replace('_', ' ').title()}: {label}",
                transaction_date=inv_date,
            )
        )
        actions.append(f"Added {expense_cat.value} expense of ₹{doc.cost:,.2f}")

    inv_cat = _DOC_TO_INVENTORY.get(doc.document_type)
    if inv_cat and doc.product_name and doc.quantity:
        item = InventoryItem(
            user_id=user.id,
            category=inv_cat,
            product_name=doc.product_name,
            quantity=doc.quantity,
            unit="kg" if inv_cat == InventoryCategory.FEED else "units",
            number_of_bags=doc.number_of_bags,
            supplier_name=doc.supplier_name,
            cost_per_unit=(doc.cost / doc.quantity) if doc.cost and doc.quantity else None,
        )
        db.add(item)
        await db.flush()
        db.add(
            StockMovement(
                item_id=item.id,
                change_amount=doc.quantity,
                reason="Added from uploaded bill",
            )
        )
        actions.append(f"Added {doc.quantity:g} {item.unit} of {doc.product_name} to inventory")

    return actions
