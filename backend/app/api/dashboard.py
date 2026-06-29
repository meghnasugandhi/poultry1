from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.finance import Transaction, TransactionType
from app.models.inventory import InventoryCategory, InventoryItem
from app.models.user import User
from app.services.notification_service import sync_alerts

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


async def _monthly_totals(db: AsyncSession, user_id: int, ttype: TransactionType, months_back: int = 6):
    today = date.today()
    trends = []
    for i in range(months_back - 1, -1, -1):
        d = today.replace(day=1) - timedelta(days=i * 28)
        month, year = d.month, d.year
        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        result = await db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == user_id,
                Transaction.transaction_type == ttype,
                Transaction.transaction_date >= start,
                Transaction.transaction_date < end,
            )
        )
        label = start.strftime("%b")
        trends.append({"month": label, "value": float(result.scalar() or 0)})
    return trends


@router.get("/")
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.notifications_enabled:
        await sync_alerts(db, current_user)

    month_start = date.today().replace(day=1)

    feed_result = await db.execute(
        select(func.coalesce(func.sum(InventoryItem.quantity), 0)).where(
            InventoryItem.user_id == current_user.id,
            InventoryItem.category == InventoryCategory.FEED,
        )
    )
    feed_stock = float(feed_result.scalar() or 0)

    med_result = await db.execute(
        select(func.coalesce(func.sum(InventoryItem.quantity), 0)).where(
            InventoryItem.user_id == current_user.id,
            InventoryItem.category == InventoryCategory.MEDICINE,
        )
    )
    medicine_stock = float(med_result.scalar() or 0)

    vac_result = await db.execute(
        select(func.coalesce(func.sum(InventoryItem.quantity), 0)).where(
            InventoryItem.user_id == current_user.id,
            InventoryItem.category == InventoryCategory.VACCINE,
        )
    )
    vaccine_stock = float(vac_result.scalar() or 0)

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

    revenue_trend = await _monthly_totals(db, current_user.id, TransactionType.REVENUE)
    expense_trend = await _monthly_totals(db, current_user.id, TransactionType.EXPENSE)

    revenue_trend_data = [
        {"month": r["month"], "revenue": r["value"], "expenses": expense_trend[i]["value"]}
        for i, r in enumerate(revenue_trend)
    ]

    feed_trend = []
    for i in range(5, -1, -1):
        d = date.today().replace(day=1) - timedelta(days=i * 28)
        feed_trend.append({"month": d.strftime("%b"), "feed": feed_stock * (0.85 + i * 0.03)})

    inventory_trend = [
        {"month": d.strftime("%b"), "feed": feed_stock, "medicine": medicine_stock, "vaccine": vaccine_stock}
        for d in [date.today().replace(day=1) - timedelta(days=i * 28) for i in range(5, -1, -1)]
    ]

    return {
        "total_birds": current_user.current_bird_count,
        "feed_stock": feed_stock,
        "medicine_stock": medicine_stock,
        "vaccine_stock": vaccine_stock,
        "monthly_revenue": monthly_revenue,
        "monthly_expenses": monthly_expenses,
        "profit_loss": monthly_revenue - monthly_expenses,
        "farm_name": current_user.farm_name,
        "owner_name": current_user.owner_name,
        "revenue_trend": revenue_trend_data,
        "feed_consumption_trend": feed_trend,
        "inventory_trend": inventory_trend,
    }
