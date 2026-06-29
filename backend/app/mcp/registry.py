"""Unified MCP tool registry — all 9 MCP servers as callable tools."""

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.finance import ExpenseCategory, RevenueCategory, Transaction, TransactionType
from app.models.inventory import InventoryCategory, InventoryItem, StockMovement
from app.models.user import User
from app.services.calculator_service import CALCULATORS
from app.services.ocr_service import process_document_ocr
from app.services.report_service import generate_report
from app.services.translation_service import get_ui_bundle, translate_text
from app.schemas.assistant import ExportFormat, ReportType


class MCPRegistry:
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user

    async def execute(self, tool: str, params: dict[str, Any] | None = None) -> Any:
        params = params or {}
        handlers = {
            # Inventory MCP
            "get_stock": self.get_stock,
            "add_stock": self.add_stock,
            "get_low_stock": self.get_low_stock,
            "get_expiring": self.get_expiring,
            # Document MCP
            "search_documents": self.search_documents,
            "get_document": self.get_document,
            # OCR MCP
            "extract_invoice": self.extract_invoice,
            # Finance MCP
            "get_expenses": self.get_expenses,
            "get_revenue": self.get_revenue,
            "get_profit_loss": self.get_profit_loss,
            "get_monthly_summary": self.get_monthly_summary,
            # Report MCP
            "generate_report": self.mcp_generate_report,
            # Calculator MCP
            "calculate": self.calculate,
            # Translation MCP
            "translate_text": self.mcp_translate,
            "translate_ui": self.mcp_translate_ui,
            # Database MCP
            "get_dashboard_stats": self.get_dashboard_stats,
            "get_user_profile": self.get_user_profile,
        }
        handler = handlers.get(tool)
        if not handler:
            raise ValueError(f"Unknown MCP tool: {tool}")
        return await handler(**params)

    # --- Inventory MCP ---
    async def get_stock(self, category: str | None = None) -> list[dict]:
        query = select(InventoryItem).where(InventoryItem.user_id == self.user.id)
        if category:
            query = query.where(InventoryItem.category == InventoryCategory(category))
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

    async def add_stock(self, category: str, product_name: str, quantity: float, unit: str = "kg") -> dict:
        item = InventoryItem(
            user_id=self.user.id,
            category=InventoryCategory(category),
            product_name=product_name,
            quantity=quantity,
            unit=unit,
        )
        self.db.add(item)
        await self.db.flush()
        self.db.add(StockMovement(item_id=item.id, change_amount=quantity, reason="MCP add"))
        return {"id": item.id, "product_name": product_name, "quantity": quantity}

    async def get_low_stock(self) -> list[dict]:
        result = await self.db.execute(
            select(InventoryItem).where(InventoryItem.user_id == self.user.id)
        )
        return [
            {"product_name": i.product_name, "quantity": i.quantity, "unit": i.unit}
            for i in result.scalars().all()
            if i.quantity <= i.reorder_level
        ]

    async def get_expiring(self) -> list[dict]:
        deadline = date.today() + timedelta(days=30)
        result = await self.db.execute(
            select(InventoryItem).where(
                InventoryItem.user_id == self.user.id,
                InventoryItem.expiry_date.isnot(None),
                InventoryItem.expiry_date <= deadline,
            )
        )
        return [
            {"product_name": i.product_name, "expiry_date": str(i.expiry_date)}
            for i in result.scalars().all()
        ]

    # --- Document MCP ---
    async def search_documents(self, query: str = "", document_type: str | None = None, month: str | None = None) -> list[dict]:
        q = select(Document).where(Document.user_id == self.user.id)
        if document_type:
            q = q.where(Document.document_type == document_type)
        if query:
            pattern = f"%{query}%"
            q = q.where(
                (Document.company_name.ilike(pattern))
                | (Document.supplier_name.ilike(pattern))
                | (Document.original_filename.ilike(pattern))
            )
        if month:
            try:
                m, y = map(int, month.split("/"))
                q = q.where(extract("month", Document.created_at) == m, extract("year", Document.created_at) == y)
            except ValueError:
                pass
        result = await self.db.execute(q.order_by(Document.created_at.desc()))
        return [
            {
                "id": d.id,
                "filename": d.original_filename,
                "company": d.company_name,
                "cost": d.cost,
                "date": str(d.invoice_date or d.created_at.date()),
            }
            for d in result.scalars().all()
        ]

    async def get_document(self, document_id: int) -> dict | None:
        result = await self.db.execute(
            select(Document).where(Document.id == document_id, Document.user_id == self.user.id)
        )
        d = result.scalar_one_or_none()
        if not d:
            return None
        return {
            "id": d.id,
            "filename": d.original_filename,
            "company_name": d.company_name,
            "product_name": d.product_name,
            "cost": d.cost,
            "invoice_number": d.invoice_number,
        }

    async def extract_invoice(self, file_path: str) -> dict:
        return await process_document_ocr(file_path)

    # --- Finance MCP ---
    async def get_expenses(self, category: str | None = None, start_date: str | None = None, end_date: str | None = None) -> dict:
        q = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == self.user.id,
            Transaction.transaction_type == TransactionType.EXPENSE,
        )
        if category:
            q = q.where(Transaction.expense_category == ExpenseCategory(category))
        if start_date:
            q = q.where(Transaction.transaction_date >= date.fromisoformat(start_date))
        if end_date:
            q = q.where(Transaction.transaction_date <= date.fromisoformat(end_date))
        total = float((await self.db.execute(q)).scalar() or 0)
        return {"total": total, "category": category}

    async def get_revenue(self, category: str | None = None) -> dict:
        q = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == self.user.id,
            Transaction.transaction_type == TransactionType.REVENUE,
        )
        if category:
            q = q.where(Transaction.revenue_category == RevenueCategory(category))
        total = float((await self.db.execute(q)).scalar() or 0)
        return {"total": total, "category": category}

    async def get_profit_loss(self) -> dict:
        rev = float(
            (await self.db.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.user_id == self.user.id,
                    Transaction.transaction_type == TransactionType.REVENUE,
                )
            )).scalar()
            or 0
        )
        exp = float(
            (await self.db.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.user_id == self.user.id,
                    Transaction.transaction_type == TransactionType.EXPENSE,
                )
            )).scalar()
            or 0
        )
        return {"revenue": rev, "expenses": exp, "profit_loss": rev - exp}

    async def get_monthly_summary(self, month: int | None = None, year: int | None = None) -> dict:
        today = date.today()
        m = month or today.month
        y = year or today.year
        start = date(y, m, 1)
        end = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
        rev = float(
            (await self.db.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.user_id == self.user.id,
                    Transaction.transaction_type == TransactionType.REVENUE,
                    Transaction.transaction_date >= start,
                    Transaction.transaction_date < end,
                )
            )).scalar()
            or 0
        )
        exp = float(
            (await self.db.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.user_id == self.user.id,
                    Transaction.transaction_type == TransactionType.EXPENSE,
                    Transaction.transaction_date >= start,
                    Transaction.transaction_date < end,
                )
            )).scalar()
            or 0
        )
        return {"month": m, "year": y, "revenue": rev, "expenses": exp, "profit_loss": rev - exp}

    # --- Report MCP ---
    async def mcp_generate_report(self, report_type: str, format: str = "pdf") -> str:
        return await generate_report(
            user=self.user,
            report_type=ReportType(report_type),
            export_format=ExportFormat(format),
            db=self.db,
        )

    # --- Calculator MCP ---
    async def calculate(self, calculation_type: str, inputs: dict[str, float]) -> dict:
        calc = CALCULATORS.get(calculation_type)
        if not calc:
            raise ValueError(f"Unknown calculation: {calculation_type}")
        result = calc["fn"](inputs)
        return {"formula": calc["formula"], **result}

    # --- Translation MCP ---
    async def mcp_translate(self, text: str, target_language: str) -> str:
        return translate_text(text, target_language)

    async def mcp_translate_ui(self, target_language: str) -> dict[str, str]:
        return get_ui_bundle(target_language)

    # --- Database MCP ---
    async def get_dashboard_stats(self) -> dict:
        feed = float(
            (await self.db.execute(
                select(func.coalesce(func.sum(InventoryItem.quantity), 0)).where(
                    InventoryItem.user_id == self.user.id,
                    InventoryItem.category == InventoryCategory.FEED,
                )
            )).scalar()
            or 0
        )
        return {
            "total_birds": self.user.current_bird_count,
            "feed_stock": feed,
            "farm_name": self.user.farm_name,
        }

    async def get_user_profile(self) -> dict:
        return {
            "owner_name": self.user.owner_name,
            "farm_name": self.user.farm_name,
            "email": self.user.email,
            "mobile": self.user.mobile_number,
            "language": self.user.preferred_language.value,
        }
