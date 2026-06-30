import re

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.registry import MCPRegistry
from app.models.finance import ExpenseCategory, Transaction, TransactionType
from app.models.inventory import InventoryCategory
from app.models.user import User
from app.services.translation_service import translate_text
from app.core.config import settings
import httpx


class PoultryAgent:
    """Routes farmer queries to MCP tools and returns natural language responses."""

    MUTATING_KEYWORDS = [
        "add", "receive", "received", "purchase", "bought", "buy", "stocked",
        "remove", "use", "used", "consume", "consumed", "deduct", "delete", "discard", "reduce", "take",
        "create", "update", "edit", "approve", "reject",
    ]

    def __init__(self, user: User, db: AsyncSession):
        self.user = user
        self.db = db
        self.mcp = MCPRegistry(db, user)

    async def process_message(self, message: str, language: str = "en") -> str:
        msg = message.lower().strip()
        response = await self._route_intent(msg)
        # If rule-based response is generic fallback, try LLM for richer understanding
        GENERIC = (
            "I'm your Poultry ERP assistant. Ask about inventory, finances, documents, "
            "calculations, or reports. Examples: 'How much feed stock remains?', "
            "'Show overall profit.', 'Show feed bills from May.'"
        )
        if response == GENERIC and settings.OPENAI_API_KEY:
            try:
                llm_resp = await self._call_llm(message, language)
                response = llm_resp or response
            except Exception:
                pass
        if language != "en":
            response = translate_text(response, language)
        return response

    async def _call_llm(self, message: str, language: str = "en") -> str | None:
        # Use OpenAI Chat completions API if key is present
        if not settings.OPENAI_API_KEY:
            return None
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
        system = (
            "You are a helpful assistant specialized for a poultry farm management app. "
            "Answer concisely and, when appropriate, suggest actions like creating transactions or linking to reports."
        )
        user_msg = f"User message: {message}\nReply in {language} (short)."
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            "max_tokens": 400,
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            j = r.json()
            return j["choices"][0]["message"]["content"].strip()

    @classmethod
    def should_request_confirmation(cls, message: str) -> bool:
        normalized = message.lower().strip()
        if not normalized:
            return False
        if any(keyword in normalized for keyword in cls.MUTATING_KEYWORDS):
            return True
        return any(
            phrase in normalized
            for phrase in ["delete this", "remove this", "approve this", "reject this", "update this"]
        )

    async def _route_intent(self, msg: str) -> str:
        intent = self._parse_inventory_command(msg)
        if intent:
            if intent["action"] == "add":
                item = await self.mcp.execute(
                    "add_stock",
                    {
                        "category": intent["category"],
                        "product_name": intent["product_name"],
                        "quantity": intent["quantity"],
                        "unit": intent["unit"],
                    },
                )
                return (
                    f"Added {item['quantity']} {item['unit']} of {item['product_name']} "
                    f"to {item['category']} inventory."
                )
            if intent["action"] == "remove":
                result = await self.mcp.execute(
                    "adjust_stock",
                    {
                        "category": intent["category"],
                        "product_name": intent["product_name"],
                        "quantity_change": -intent["quantity"],
                        "unit": intent["unit"],
                    },
                )
                if result.get("error"):
                    return result["error"]
                return (
                    f"Removed {result['removed']} {result['unit']} from {result['product_name']} "
                    f"({result['category']}) inventory. Remaining {result['quantity']} {result['unit']}."
                )
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
        if "report" in msg or ("generate" in msg and "pdf" in msg):
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

    def _parse_inventory_command(self, text: str) -> dict[str, str | float] | None:
        add_pattern = r"(?:add|receive|received|purchase|purchased|got|bought|stocked)\s+(\d+(?:\.\d+)?)\s*(kg|g|grams|bags|units|doses|ml|l)?\s*(?:of\s+)?(.+)"
        remove_pattern = r"(?:remove|use|used|consume|consumed|deduct|delete|discard|reduce|take)\s+(\d+(?:\.\d+)?)\s*(kg|g|grams|bags|units|doses|ml|l)?\s*(?:of\s+)?(.+)"

        for action, pattern in [("add", add_pattern), ("remove", remove_pattern)]:
            match = re.search(pattern, text)
            if not match:
                continue
            quantity = float(match.group(1))
            unit = match.group(2) or "kg"
            unit = unit.lower()
            if unit in {"grams", "g"}:
                unit = "g"
            if unit in {"liters", "liter", "l"}:
                unit = "l"
            product = match.group(3).strip()
            category = "feed"
            lower = product.lower()
            if any(keyword in lower for keyword in ["medicine", "tablet", "syrup", "drug", "antibiotic"]):
                category = "medicine"
            elif any(keyword in lower for keyword in ["vaccine", "vaccination", "shot", "disease"]):
                category = "vaccine"
            elif any(keyword in lower for keyword in ["feed", "feeds", "ration", "pellet", "broiler", "layer"]):
                category = "feed"

            cleaned = re.sub(
                r"\b(feed|feeds|medicine|medicines|vaccine|vaccines|bag|bags|unit|units|dose|doses|tablet|syrup|injection|shot)\b",
                "",
                product,
                flags=re.I,
            ).strip()
            if not cleaned:
                cleaned = f"{category.title()}"
            product_name = cleaned.title()
            return {
                "action": action,
                "category": category,
                "product_name": product_name,
                "quantity": quantity,
                "unit": unit,
            }
        return None

    def _format_stock(self, label: str, items: list[dict]) -> str:
        if not items:
            return f"No {label.lower()} items in inventory."
        lines = [f"{label} Inventory:"] + [
            f"- {i['product_name']}: {i['quantity']} {i['unit']}" for i in items
        ]
        return "\n".join(lines)
