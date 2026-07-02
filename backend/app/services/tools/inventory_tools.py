import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import InventoryCategory, InventoryItem, StockMovement
from app.models.user import User


class InventoryToolService:
    def __init__(self, db: AsyncSession, user: User, logger: logging.Logger | None = None):
        self.db = db
        self.user = user
        self.logger = logger or logging.getLogger("poultry.mcp.inventory")

    def _normalize_category(self, category: str) -> InventoryCategory:
        if isinstance(category, InventoryCategory):
            return category
        try:
            return InventoryCategory(category.lower())
        except ValueError as exc:
            raise ValueError("Unsupported inventory category") from exc

    async def _find_item(self, category: str, product_name: str, unit: str | None = None) -> InventoryItem | None:
        query = select(InventoryItem).where(
            InventoryItem.user_id == self.user.id,
            InventoryItem.category == self._normalize_category(category),
            func.lower(InventoryItem.product_name) == product_name.lower(),
        )
        if unit:
            query = query.where(InventoryItem.unit == unit)
        result = await self.db.execute(query)
        item = result.scalar_one_or_none()
        if item:
            return item
        if not unit and product_name:
            result = await self.db.execute(
                select(InventoryItem).where(
                    InventoryItem.user_id == self.user.id,
                    InventoryItem.category == self._normalize_category(category),
                    InventoryItem.product_name.ilike(f"%{product_name}%"),
                )
            )
            return result.scalar_one_or_none()
        return None

    async def add_stock(self, category: str, product_name: str, quantity: float, unit: str = "kg", reason: str = "MCP add") -> dict[str, Any]:
        if not product_name or not product_name.strip():
            raise ValueError("Product name is required")
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero")
        category_enum = self._normalize_category(category)
        normalized_name = product_name.strip()
        item = await self._find_item(category=category_enum.value, product_name=normalized_name, unit=unit)
        if item:
            item.quantity += quantity
        else:
            item = InventoryItem(
                user_id=self.user.id,
                category=category_enum,
                product_name=normalized_name,
                quantity=quantity,
                unit=unit,
            )
            self.db.add(item)
            await self.db.flush()
        self.db.add(StockMovement(item_id=item.id, change_amount=quantity, reason=reason))
        await self.db.flush()
        self.logger.info("inventory.add_stock", extra={"product": normalized_name, "quantity": quantity, "category": category_enum.value})
        return {
            "id": item.id,
            "product_name": item.product_name,
            "category": item.category.value,
            "quantity": item.quantity,
            "unit": item.unit,
        }

    async def remove_stock(self, category: str, product_name: str, quantity: float, unit: str = "kg", reason: str = "MCP remove") -> dict[str, Any]:
        return await self.adjust_stock(category=category, product_name=product_name, quantity_change=-quantity, unit=unit, reason=reason)

    async def adjust_stock(self, category: str, product_name: str, quantity_change: float, unit: str = "kg", reason: str = "MCP adjust") -> dict[str, Any]:
        if not product_name or not product_name.strip():
            raise ValueError("Product name is required")
        if quantity_change == 0:
            raise ValueError("Quantity change cannot be zero")
        category_enum = self._normalize_category(category)
        item = await self._find_item(category=category_enum.value, product_name=product_name.strip(), unit=unit)
        if not item:
            raise ValueError(f"No {category_enum.value} inventory item found for '{product_name}'")
        actual_change = quantity_change
        if item.quantity + actual_change < 0:
            actual_change = -item.quantity
            item.quantity = 0
        else:
            item.quantity += actual_change
        self.db.add(StockMovement(item_id=item.id, change_amount=actual_change, reason=reason))
        await self.db.flush()
        self.logger.info("inventory.adjust_stock", extra={"product": item.product_name, "change": actual_change})
        return {
            "id": item.id,
            "product_name": item.product_name,
            "category": item.category.value,
            "quantity": item.quantity,
            "unit": item.unit,
            "removed": abs(actual_change) if actual_change < 0 else 0,
        }

    async def transfer_stock(self, from_category: str, to_category: str, product_name: str, quantity: float, unit: str = "kg") -> dict[str, Any]:
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero")
        await self.remove_stock(category=from_category, product_name=product_name, quantity=quantity, unit=unit, reason="transfer out")
        await self.add_stock(category=to_category, product_name=product_name, quantity=quantity, unit=unit, reason="transfer in")
        return {"status": "transferred", "quantity": quantity, "product_name": product_name}

    async def get_stock(self, category: str | None = None) -> list[dict[str, Any]]:
        query = select(InventoryItem).where(InventoryItem.user_id == self.user.id)
        if category:
            query = query.where(InventoryItem.category == self._normalize_category(category))
        result = await self.db.execute(query)
        return [
            {
                "product_name": i.product_name,
                "category": i.category.value,
                "quantity": i.quantity,
                "unit": i.unit,
                "is_low": i.quantity <= i.reorder_level,
            }
            for i in result.scalars().all()
        ]

    async def get_low_stock(self) -> list[dict[str, Any]]:
        result = await self.db.execute(select(InventoryItem).where(InventoryItem.user_id == self.user.id))
        return [
            {"product_name": i.product_name, "category": i.category.value, "quantity": i.quantity, "unit": i.unit}
            for i in result.scalars().all()
            if i.quantity <= i.reorder_level
        ]

    async def predict_stock_shortage(self, days_ahead: int = 7) -> dict[str, Any]:
        if days_ahead <= 0:
            raise ValueError("days_ahead must be positive")
        result = await self.db.execute(select(InventoryItem).where(InventoryItem.user_id == self.user.id))
        items = result.scalars().all()
        predicted = [
            {
                "product_name": item.product_name,
                "category": item.category.value,
                "quantity": item.quantity,
                "reorder_level": item.reorder_level,
                "risk": "high" if item.quantity <= item.reorder_level else "medium",
            }
            for item in items
            if item.quantity <= item.reorder_level
        ]
        return {"days_ahead": days_ahead, "predicted_shortage": predicted}
