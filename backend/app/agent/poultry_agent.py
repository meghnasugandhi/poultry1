from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.registry import MCPRegistry
from app.models.finance import ExpenseCategory, Transaction, TransactionType
from app.models.inventory import InventoryCategory
from app.models.user import User
from app.services.translation_service import translate_text


class PoultryAgent:
    """Routes farmer queries to MCP tools and returns natural language responses."""

    def __init__(self, user: User, db: AsyncSession):
        self.user = user
        self.db = db
        self.mcp = MCPRegistry(db, user)

    async def process_message(self, message: str, language: str = "en") -> str:
        msg = message.lower().strip()
        response = await self._route_intent(msg)
        if language != "en":
            response = translate_text(response, language)
        return response

    async def _route_intent(self, msg: str) -> str:
        if any(kw in msg for kw in ["feed stock", "feed remain", "how much feed", "feed inventory"]):
            items = await self.mcp.execute("get_stock", {"category": "feed"})
            return self._format_stock("Feed", items)
        if any(kw in msg for kw in ["medicine inventory", "medicine stock", "show medicine"]):
            items = await self.mcp.execute("get_stock", {"category": "medicine"})
            return self._format_stock("Medicine", items)
        if any(kw in msg for kw in ["vaccine stock", "vaccine inventory"]):
            items = await self.mcp.execute("get_stock", {"category": "vaccine"})
            return self._format_stock("Vaccine", items)
        if any(kw in msg for kw in ["low stock", "running low"]):
            items = await self.mcp.execute("get_low_stock")
            if not items:
                return "All stock levels are healthy. No low stock alerts."
            lines = ["Low Stock Alerts:"] + [
                f"- {i['product_name']}: {i['quantity']} {i['unit']}" for i in items
            ]
            return "\n".join(lines)
        if "feed expense" in msg or "feed cost" in msg:
            data = await self.mcp.execute("get_expenses", {"category": "feed"})
            return f"Total feed expense: ₹{data['total']:,.2f}"
        if "medicine expense" in msg:
            data = await self.mcp.execute("get_expenses", {"category": "medicines"})
            return f"Total medicine expense: ₹{data['total']:,.2f}"
        if any(kw in msg for kw in ["profit", "loss", "overall profit"]):
            data = await self.mcp.execute("get_profit_loss")
            pl = data["profit_loss"]
            status = "profit" if pl >= 0 else "loss"
            return (
                f"Overall {status}: ₹{abs(pl):,.2f} "
                f"(Revenue: ₹{data['revenue']:,.2f}, Expenses: ₹{data['expenses']:,.2f})"
            )
        if "monthly expense" in msg or "show expense" in msg:
            summary = await self.mcp.execute("get_monthly_summary")
            return (
                f"Monthly summary ({summary['month']}/{summary['year']}): "
                f"Revenue ₹{summary['revenue']:,.2f}, Expenses ₹{summary['expenses']:,.2f}, "
                f"Profit/Loss ₹{summary['profit_loss']:,.2f}"
            )
        if "feed bill" in msg or "invoice" in msg or "document" in msg:
            query = msg.replace("show", "").replace("find", "").strip()
            docs = await self.mcp.execute("search_documents", {"query": query})
            if not docs:
                return "No matching documents found."
            lines = ["Matching documents:"] + [
                f"- {d['filename']} | {d.get('company') or 'Unknown'} | ₹{d.get('cost') or 0}"
                for d in docs[:5]
            ]
            return "\n".join(lines)
        if "fcr" in msg or "calculate fcr" in msg:
            return (
                "To calculate FCR, go to Calculator or provide: feed_consumed and weight_gain. "
                "Formula: FCR = Total Feed Consumed / Total Weight Gain"
            )
        if "mortality" in msg:
            return (
                "To calculate mortality, provide: dead_birds and total_birds. "
                "Formula: Mortality % = (Dead Birds / Total Birds) × 100"
            )
        if "report" in msg or "generate" in msg and "pdf" in msg:
            return (
                "I can generate reports: Feed Expense, Medicine Expense, Inventory, "
                "Profit & Loss, Vaccination, Sales, and Batch. "
                "Use the Reports page or say e.g. 'Generate inventory report PDF'."
            )
        if "dashboard" in msg or "farm status" in msg:
            stats = await self.mcp.execute("get_dashboard_stats")
            return (
                f"Farm: {stats['farm_name']} | Birds: {stats['total_birds']} | "
                f"Feed stock: {stats['feed_stock']} kg"
            )
        return (
            "I'm your Poultry ERP assistant. Ask about inventory, finances, documents, "
            "calculations, or reports. Examples: 'How much feed stock remains?', "
            "'Show overall profit.', 'Show feed bills from May.'"
        )

    def _format_stock(self, label: str, items: list[dict]) -> str:
        if not items:
            return f"No {label.lower()} items in inventory."
        lines = [f"{label} Inventory:"] + [
            f"- {i['product_name']}: {i['quantity']} {i['unit']}" for i in items
        ]
        return "\n".join(lines)
