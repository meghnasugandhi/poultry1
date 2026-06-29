import re
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.registry import MCPRegistry
from app.models.finance import (
    ExpenseCategory,
    RevenueCategory,
    Transaction,
    TransactionType,
)
from app.models.inventory import InventoryCategory, InventoryItem, StockMovement
from app.models.user import User
from app.services.calculator_service import CALCULATORS
from app.services.translation_service import translate_text

_UNIT_WORDS = r"kg|kgs|kilograms?|bags?|units?|doses?|litres?|liters?|l|g|grams?|packets?|boxes?"

_EXPENSE_KEYWORDS = {
    "feed": ExpenseCategory.FEED,
    "medicine": ExpenseCategory.MEDICINES,
    "medicines": ExpenseCategory.MEDICINES,
    "vaccine": ExpenseCategory.VACCINES,
    "vaccines": ExpenseCategory.VACCINES,
    "labor": ExpenseCategory.LABOR,
    "labour": ExpenseCategory.LABOR,
    "wages": ExpenseCategory.LABOR,
    "electricity": ExpenseCategory.ELECTRICITY,
    "power": ExpenseCategory.ELECTRICITY,
    "transport": ExpenseCategory.TRANSPORT,
    "fuel": ExpenseCategory.TRANSPORT,
    "diesel": ExpenseCategory.TRANSPORT,
}


class PoultryAgent:
    """Routes farmer queries to MCP tools and returns natural language responses.

    Beyond answering questions, the agent understands free-form *commands* such as
    "add 50 kg broiler feed", "paid 3000 for electricity", "sold 20 birds for 5000"
    and "set bird count to 500", and writes them to the database automatically.
    """

    def __init__(self, user: User, db: AsyncSession):
        self.user = user
        self.db = db
        self.mcp = MCPRegistry(db, user)

    async def process_message(self, message: str, language: str = "en") -> str:
        msg = message.lower().strip()
        response = await self._try_command(msg) or await self._route_intent(msg)
        if language != "en":
            response = translate_text(response, language)
        return response

    # --- Smart commands: add / update farm data ---------------------------------
    async def _try_command(self, msg: str) -> str | None:
        for handler in (
            self._cmd_update_birds,
            self._cmd_add_revenue,
            self._cmd_add_expense,
            self._cmd_add_inventory,
            self._cmd_calculate,
        ):
            result = await handler(msg)
            if result:
                return result
        return None

    async def _cmd_update_birds(self, msg: str) -> str | None:
        m = re.search(r"(?:set|update|change)\s+(?:the\s+)?(?:current\s+)?bird\s*count\s*(?:to|=|as)?\s*(\d+)", msg)
        if not m:
            m = re.search(r"(?:i\s+(?:now\s+)?have|there\s+are)\s+(\d+)\s+birds", msg)
        if not m:
            return None
        count = int(m.group(1))
        self.user.current_bird_count = count
        await self.db.flush()
        return f"Updated current bird count to {count:,}."

    async def _cmd_add_revenue(self, msg: str) -> str | None:
        if not any(k in msg for k in ("sold", "sale", "sales", "earned", "received", "income", "revenue")):
            return None
        amount = self._extract_amount(msg)
        if amount is None:
            return None
        category = RevenueCategory.EGG_SALES if "egg" in msg else (
            RevenueCategory.BIRD_SALES if any(k in msg for k in ("bird", "chicken", "broiler", "sold")) else RevenueCategory.OTHER_INCOME
        )
        self.db.add(
            Transaction(
                user_id=self.user.id,
                transaction_type=TransactionType.REVENUE,
                revenue_category=category,
                amount=amount,
                description=msg[:200],
                transaction_date=date.today(),
            )
        )
        await self.db.flush()
        return f"Recorded revenue of ₹{amount:,.2f} under {category.value.replace('_', ' ')}."

    async def _cmd_add_expense(self, msg: str) -> str | None:
        if not any(k in msg for k in ("spent", "paid", "expense", "cost", "bought", "purchased", "bill")):
            return None
        if any(k in msg for k in ("sold", "sale", "revenue", "income")):
            return None
        amount = self._extract_amount(msg)
        if amount is None:
            return None
        category = ExpenseCategory.MISCELLANEOUS
        for word, cat in _EXPENSE_KEYWORDS.items():
            if re.search(rf"\b{word}\b", msg):
                category = cat
                break
        self.db.add(
            Transaction(
                user_id=self.user.id,
                transaction_type=TransactionType.EXPENSE,
                expense_category=category,
                amount=amount,
                description=msg[:200],
                transaction_date=date.today(),
            )
        )
        await self.db.flush()
        return f"Added {category.value} expense of ₹{amount:,.2f}."

    async def _cmd_add_inventory(self, msg: str) -> str | None:
        if not any(k in msg for k in ("add", "added", "buy", "bought", "purchase", "received", "got", "stock")):
            return None
        m = re.search(
            rf"(\d+(?:\.\d+)?)\s*({_UNIT_WORDS})?\s+(?:of\s+)?([a-z0-9 \-]+)",
            msg,
        )
        if not m:
            return None
        quantity = float(m.group(1))
        unit = (m.group(2) or "kg").strip()
        product = m.group(3).strip()
        # Trim trailing filler words.
        product = re.sub(r"\b(to|into|in|the|my|inventory|stock|please)\b", "", product).strip()
        if not product:
            return None
        category = "feed"
        for cat in ("medicine", "vaccine", "feed"):
            if cat in product or cat in msg:
                category = cat
                product = re.sub(rf"\b{cat}\b", "", product, flags=re.I).strip() or product
                break
        product = product.title()
        item = InventoryItem(
            user_id=self.user.id,
            category=InventoryCategory(category),
            product_name=product,
            quantity=quantity,
            unit=unit,
        )
        self.db.add(item)
        await self.db.flush()
        self.db.add(StockMovement(item_id=item.id, change_amount=quantity, reason="Added via AI assistant"))
        await self.db.flush()
        return f"Added {quantity:g} {unit} of {product} to {category} inventory."

    async def _cmd_calculate(self, msg: str) -> str | None:
        if "fcr" in msg:
            nums = self._extract_numbers(msg)
            if len(nums) >= 2:
                return self._format_calc("fcr", {"feed_consumed": nums[0], "weight_gain": nums[1]})
            return (
                "To calculate FCR, tell me feed consumed and weight gain, e.g. "
                "'Calculate FCR feed 100 gain 50'. Formula: FCR = Feed Consumed / Weight Gain."
            )
        if "mortality" in msg:
            nums = self._extract_numbers(msg)
            if len(nums) >= 2:
                return self._format_calc("mortality_percentage", {"dead_birds": nums[0], "total_birds": nums[1]})
            return (
                "To calculate mortality, tell me dead birds and total birds, e.g. "
                "'Calculate mortality 10 dead of 500'. Formula: (Dead / Total) × 100."
            )
        return None

    def _format_calc(self, calc_type: str, inputs: dict) -> str:
        calc = CALCULATORS[calc_type]
        result = calc["fn"](inputs)
        steps = "\n".join(f"  {s}" for s in result["steps"])
        return f"{calc['formula']}\n{steps}\nResult: {result['value']}\n{result['explanation']}"

    @staticmethod
    def _extract_amount(msg: str) -> float | None:
        # Prefer an amount that follows a currency marker or "for/at/@".
        m = re.search(r"(?:rs\.?|₹|inr|for|at|@|=)\s*([\d,]+(?:\.\d{1,2})?)", msg)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                pass
        # Otherwise use the largest number mentioned (the amount, not the count).
        nums = PoultryAgent._extract_numbers(msg)
        return max(nums) if nums else None

    @staticmethod
    def _extract_numbers(msg: str) -> list[float]:
        return [float(n.replace(",", "")) for n in re.findall(r"[\d,]+(?:\.\d+)?", msg)]

    # --- Query intents ----------------------------------------------------------
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
        if any(kw in msg for kw in ["low stock", "running low", "what stock"]):
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
        if "monthly expense" in msg or "show expense" in msg or "monthly summary" in msg:
            summary = await self.mcp.execute("get_monthly_summary")
            return (
                f"Monthly summary ({summary['month']}/{summary['year']}): "
                f"Revenue ₹{summary['revenue']:,.2f}, Expenses ₹{summary['expenses']:,.2f}, "
                f"Profit/Loss ₹{summary['profit_loss']:,.2f}"
            )
        if "feed bill" in msg or "invoice" in msg or "document" in msg or "bill" in msg:
            query = msg.replace("show", "").replace("find", "").strip()
            docs = await self.mcp.execute("search_documents", {"query": query})
            if not docs:
                return "No matching documents found."
            lines = ["Matching documents:"] + [
                f"- {d['filename']} | {d.get('company') or 'Unknown'} | ₹{d.get('cost') or 0}"
                for d in docs[:5]
            ]
            return "\n".join(lines)
        if "report" in msg or ("generate" in msg and "pdf" in msg):
            return (
                "I can generate reports: Feed Expense, Medicine Expense, Inventory, "
                "Profit & Loss, Vaccination, Sales, and Batch. "
                "Open the Reports page to preview, review and download as PDF or Excel."
            )
        if "dashboard" in msg or "farm status" in msg:
            stats = await self.mcp.execute("get_dashboard_stats")
            return (
                f"Farm: {stats['farm_name']} | Birds: {stats['total_birds']} | "
                f"Feed stock: {stats['feed_stock']} kg"
            )
        return (
            "I'm your Poultry ERP assistant. I can answer questions and also update your farm. "
            "Try: 'How much feed stock remains?', 'Show overall profit', "
            "'Add 50 kg broiler feed', 'Paid 3000 for electricity', or upload a bill and say 'add this'."
        )

    def _format_stock(self, label: str, items: list[dict]) -> str:
        if not items:
            return f"No {label.lower()} items in inventory."
        lines = [f"{label} Inventory:"] + [
            f"- {i['product_name']}: {i['quantity']} {i['unit']}" for i in items
        ]
        return "\n".join(lines)
