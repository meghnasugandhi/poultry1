import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.finance import Transaction
from app.models.inventory import InventoryItem
from app.models.user import User


class SearchToolService:
    def __init__(self, db: AsyncSession, user: User, logger: logging.Logger | None = None):
        self.db = db
        self.user = user
        self.logger = logger or logging.getLogger("poultry.mcp.search")

    async def search_documents(self, query: str = "") -> list[dict[str, Any]]:
        if not query:
            return []
        pattern = f"%{query}%"
        result = await self.db.execute(select(Document).where(Document.user_id == self.user.id, (Document.company_name.ilike(pattern)) | (Document.supplier_name.ilike(pattern)) | (Document.original_filename.ilike(pattern)) ))
        return [{"id": d.id, "filename": d.original_filename, "company": d.company_name, "cost": d.cost} for d in result.scalars().all()]

    async def search_inventory(self, query: str = "") -> list[dict[str, Any]]:
        if not query:
            return []
        pattern = f"%{query}%"
        result = await self.db.execute(select(InventoryItem).where(InventoryItem.user_id == self.user.id, InventoryItem.product_name.ilike(pattern)))
        return [{"product_name": i.product_name, "quantity": i.quantity, "unit": i.unit, "category": i.category.value} for i in result.scalars().all()]

    async def search_finance(self, query: str = "") -> list[dict[str, Any]]:
        if not query:
            return []
        pattern = f"%{query}%"
        result = await self.db.execute(select(Transaction).where(Transaction.user_id == self.user.id, Transaction.description.ilike(pattern)))
        return [{"description": t.description, "amount": t.amount, "type": t.transaction_type.value} for t in result.scalars().all()]

    async def search_reports(self, query: str = "") -> list[dict[str, Any]]:
        return [{"query": query, "status": "available"}]
