from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.finance import ExpenseCategory, RevenueCategory, Transaction, TransactionType
from app.models.inventory import InventoryCategory, InventoryItem
from app.models.user import User
from app.schemas.finance import FinancialSummary, TransactionCreate, TransactionResponse

router = APIRouter(prefix="/finance", tags=["Financial Management"])


@router.post("/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.transaction_type == TransactionType.REVENUE and not data.revenue_category:
        raise HTTPException(status_code=400, detail="Revenue category required")
    if data.transaction_type == TransactionType.EXPENSE and not data.expense_category:
        raise HTTPException(status_code=400, detail="Expense category required")

    transaction = Transaction(
        user_id=current_user.id,
        transaction_type=data.transaction_type,
        revenue_category=data.revenue_category,
        expense_category=data.expense_category,
        amount=data.amount,
        description=data.description,
        transaction_date=data.transaction_date or date.today(),
    )
    db.add(transaction)
    await db.flush()
    await db.refresh(transaction)
    return transaction


@router.get("/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    transaction_type: TransactionType | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Transaction).where(Transaction.user_id == current_user.id)
    if transaction_type:
        query = query.where(Transaction.transaction_type == transaction_type)
    query = query.order_by(Transaction.transaction_date.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == current_user.id,
        )
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await db.delete(transaction)


@router.get("/summary", response_model=FinancialSummary)
async def get_financial_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    month_start = today.replace(day=1)

    revenue_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == TransactionType.REVENUE,
            Transaction.transaction_date >= month_start,
        )
    )
    monthly_revenue = float(revenue_result.scalar() or 0)

    expense_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == TransactionType.EXPENSE,
            Transaction.transaction_date >= month_start,
        )
    )
    monthly_expenses = float(expense_result.scalar() or 0)

    revenue_breakdown: dict[str, float] = {}
    for cat in RevenueCategory:
        r = await db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == current_user.id,
                Transaction.transaction_type == TransactionType.REVENUE,
                Transaction.revenue_category == cat,
                Transaction.transaction_date >= month_start,
            )
        )
        revenue_breakdown[cat.value] = float(r.scalar() or 0)

    expense_breakdown: dict[str, float] = {}
    for cat in ExpenseCategory:
        r = await db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == current_user.id,
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.expense_category == cat,
                Transaction.transaction_date >= month_start,
            )
        )
        expense_breakdown[cat.value] = float(r.scalar() or 0)

    return FinancialSummary(
        monthly_revenue=monthly_revenue,
        monthly_expenses=monthly_expenses,
        profit_loss=monthly_revenue - monthly_expenses,
        revenue_breakdown=revenue_breakdown,
        expense_breakdown=expense_breakdown,
    )
