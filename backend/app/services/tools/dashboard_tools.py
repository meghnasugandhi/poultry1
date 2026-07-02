import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import Transaction, TransactionType
from app.models.inventory import InventoryCategory, InventoryItem
from app.models.user import User


class DashboardToolService:
    def __init__(self, db: AsyncSession, user: User, logger: logging.Logger | None = None):
        self.db = db
        self.user = user
        self.logger = logger or logging.getLogger("poultry.mcp.dashboard")

    async def dashboard_summary(self) -> dict[str, Any]:
        feed_stock = float((await self.db.execute(select(func.coalesce(func.sum(InventoryItem.quantity), 0)).where(InventoryItem.user_id == self.user.id, InventoryItem.category == InventoryCategory.FEED))).scalar() or 0)
        low_stock = float((await self.db.execute(select(func.count()).select_from(InventoryItem).where(InventoryItem.user_id == self.user.id, InventoryItem.quantity <= InventoryItem.reorder_level))).scalar() or 0)
        revenue = float((await self.db.execute(select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.user_id == self.user.id, Transaction.transaction_type == TransactionType.REVENUE))).scalar() or 0)
        expenses = float((await self.db.execute(select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.user_id == self.user.id, Transaction.transaction_type == TransactionType.EXPENSE))).scalar() or 0)
        return {"farm_name": self.user.farm_name, "total_birds": self.user.current_bird_count, "feed_stock": feed_stock, "low_stock_items": int(low_stock), "revenue": revenue, "expenses": expenses, "profit_loss": revenue - expenses}

    async def analytics_summary(self) -> dict[str, Any]:
        return {"summary": await self.dashboard_summary()}

    async def farm_summary(self) -> dict[str, Any]:
        return await self.dashboard_summary()
