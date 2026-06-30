from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.finance import SuggestedTransaction, Transaction, TransactionType
from app.models.user import User
from app.schemas.finance import SuggestedTransactionCreate, SuggestedTransactionResponse
from app.models.finance import ExpenseCategory, RevenueCategory

router = APIRouter(prefix="/suggested-transactions", tags=["Suggested Transactions"])

@router.get("/", response_model=list[SuggestedTransactionResponse])
async def list_suggested_transactions(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(SuggestedTransaction).where(SuggestedTransaction.user_id == current_user.id).order_by(SuggestedTransaction.created_at.desc()))
    return result.scalars().all()

@router.post("/{s_id}/approve", response_model=SuggestedTransactionResponse)
async def approve_suggested_transaction(s_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SuggestedTransaction).where(SuggestedTransaction.id == s_id, SuggestedTransaction.user_id == current_user.id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Suggested transaction not found")
    if s.status != "suggested":
        raise HTTPException(status_code=400, detail="Already processed")

    # create real transaction
    tx = Transaction(
        user_id=current_user.id,
        transaction_type=s.transaction_type,
        revenue_category=s.revenue_category,
        expense_category=s.expense_category,
        amount=s.amount,
        description=s.description,
        transaction_date=s.transaction_date,
    )
    db.add(tx)
    s.status = "approved"
    await db.flush()
    await db.refresh(s)
    return s

@router.post("/{s_id}/reject", response_model=SuggestedTransactionResponse)
async def reject_suggested_transaction(s_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SuggestedTransaction).where(SuggestedTransaction.id == s_id, SuggestedTransaction.user_id == current_user.id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Suggested transaction not found")
    if s.status != "suggested":
        raise HTTPException(status_code=400, detail="Already processed")
    s.status = "rejected"
    await db.flush()
    await db.refresh(s)
    return s


@router.put("/{s_id}", response_model=SuggestedTransactionResponse)
async def update_suggested_transaction(
    s_id: int, data: SuggestedTransactionCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(SuggestedTransaction).where(SuggestedTransaction.id == s_id, SuggestedTransaction.user_id == current_user.id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Suggested transaction not found")
    if s.status != "suggested":
        raise HTTPException(status_code=400, detail="Cannot edit processed suggestion")
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(s, field, val)
    await db.flush()
    await db.refresh(s)
    return s


@router.post("/bulk-approve", response_model=list[SuggestedTransactionResponse])
async def bulk_approve(ids: list[int], current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    resp = []
    for s_id in ids:
        result = await db.execute(select(SuggestedTransaction).where(SuggestedTransaction.id == s_id, SuggestedTransaction.user_id == current_user.id))
        s = result.scalar_one_or_none()
        if not s or s.status != "suggested":
            continue
        tx = Transaction(
            user_id=current_user.id,
            transaction_type=s.transaction_type,
            revenue_category=s.revenue_category,
            expense_category=s.expense_category,
            amount=s.amount,
            description=s.description,
            transaction_date=s.transaction_date,
        )
        db.add(tx)
        s.status = "approved"
        await db.flush()
        await db.refresh(s)
        resp.append(s)
    return resp


@router.post("/bulk-reject", response_model=list[SuggestedTransactionResponse])
async def bulk_reject(ids: list[int], current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    resp = []
    for s_id in ids:
        result = await db.execute(select(SuggestedTransaction).where(SuggestedTransaction.id == s_id, SuggestedTransaction.user_id == current_user.id))
        s = result.scalar_one_or_none()
        if not s or s.status != "suggested":
            continue
        s.status = "rejected"
        await db.flush()
        await db.refresh(s)
        resp.append(s)
    return resp
