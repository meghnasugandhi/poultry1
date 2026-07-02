import logging
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import ExpenseCategory, RevenueCategory, Transaction, TransactionType
from app.models.user import User


class FinanceToolService:
    def __init__(self, db: AsyncSession, user: User, logger: logging.Logger | None = None):
        self.db = db
        self.user = user
        self.logger = logger or logging.getLogger("poultry.mcp.finance")

    def _expense_category(self, category: str | None) -> ExpenseCategory | None:
        if not category:
            return None
        try:
            return ExpenseCategory(category.lower())
        except ValueError as exc:
            raise ValueError("Unsupported expense category") from exc

    def _revenue_category(self, category: str | None) -> RevenueCategory | None:
        if not category:
            return None
        try:
            return RevenueCategory(category.lower())
        except ValueError as exc:
            raise ValueError("Unsupported revenue category") from exc

    async def create_expense(self, amount: float, description: str, category: str = "miscellaneous", transaction_date: str | None = None) -> dict[str, Any]:
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        tx = Transaction(
            user_id=self.user.id,
            transaction_type=TransactionType.EXPENSE,
            expense_category=self._expense_category(category),
            amount=amount,
            description=description,
            transaction_date=date.fromisoformat(transaction_date) if transaction_date else date.today(),
        )
        self.db.add(tx)
        await self.db.flush()
        self.logger.info("finance.create_expense", extra={"amount": amount, "category": category})
        return {"id": tx.id, "transaction_type": tx.transaction_type.value, "amount": tx.amount, "description": tx.description}

    async def create_income(self, amount: float, description: str, category: str = "other_income", transaction_date: str | None = None) -> dict[str, Any]:
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        tx = Transaction(
            user_id=self.user.id,
            transaction_type=TransactionType.REVENUE,
            revenue_category=self._revenue_category(category),
            amount=amount,
            description=description,
            transaction_date=date.fromisoformat(transaction_date) if transaction_date else date.today(),
        )
        self.db.add(tx)
        await self.db.flush()
        self.logger.info("finance.create_income", extra={"amount": amount, "category": category})
        return {"id": tx.id, "transaction_type": tx.transaction_type.value, "amount": tx.amount, "description": tx.description}

    async def supplier_summary(self) -> dict[str, Any]:
        result = await self.db.execute(select(Transaction).where(Transaction.user_id == self.user.id).order_by(Transaction.transaction_date.desc()))
        rows = result.scalars().all()
        grouped: dict[str, float] = {}
        for tx in rows:
            key = tx.description or "Unspecified"
            grouped[key] = grouped.get(key, 0.0) + float(tx.amount)
        return {"suppliers": grouped}

    async def cash_flow(self) -> dict[str, Any]:
        revenue = float((await self.db.execute(select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.user_id == self.user.id, Transaction.transaction_type == TransactionType.REVENUE))).scalar() or 0)
        expenses = float((await self.db.execute(select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.user_id == self.user.id, Transaction.transaction_type == TransactionType.EXPENSE))).scalar() or 0)
        return {"revenue": revenue, "expenses": expenses, "net": revenue - expenses}

    async def profit_loss(self) -> dict[str, Any]:
        flow = await self.cash_flow()
        return {"revenue": flow["revenue"], "expenses": flow["expenses"], "profit_loss": flow["net"]}

    async def get_expenses(self, category: str | None = None) -> dict[str, Any]:
        query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == self.user.id,
            Transaction.transaction_type == TransactionType.EXPENSE,
        )
        if category:
            query = query.where(Transaction.expense_category == self._expense_category(category))
        total = float((await self.db.execute(query)).scalar() or 0)
        return {"category": category, "total": total}

    async def get_revenue(self, category: str | None = None) -> dict[str, Any]:
        query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == self.user.id,
            Transaction.transaction_type == TransactionType.REVENUE,
        )
        if category:
            query = query.where(Transaction.revenue_category == self._revenue_category(category))
        total = float((await self.db.execute(query)).scalar() or 0)
        return {"category": category, "total": total}

    async def get_profit_loss(self) -> dict[str, Any]:
        return await self.profit_loss()

    async def get_monthly_summary(self, month: int | None = None, year: int | None = None) -> dict[str, Any]:
        return await self.monthly_finance(month=month, year=year)

    async def monthly_finance(self, month: int | None = None, year: int | None = None) -> dict[str, Any]:
        today = date.today()
        month = month or today.month
        year = year or today.year
        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        revenue = float((await self.db.execute(select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.user_id == self.user.id, Transaction.transaction_type == TransactionType.REVENUE, Transaction.transaction_date >= start, Transaction.transaction_date < end))).scalar() or 0)
        expenses = float((await self.db.execute(select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.user_id == self.user.id, Transaction.transaction_type == TransactionType.EXPENSE, Transaction.transaction_date >= start, Transaction.transaction_date < end))).scalar() or 0)
        return {"month": month, "year": year, "revenue": revenue, "expenses": expenses, "profit_loss": revenue - expenses}
