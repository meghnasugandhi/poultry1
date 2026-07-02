import logging
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.langgraph_orchestrator import LangGraphOrchestrator
from app.core.config import settings
from app.mcp.registry import MCPRegistry
from app.models.user import User
from app.services.rag_service import RAGService
from app.services.translation_service import translate_text
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
        self.logger = logging.getLogger("poultry.agent")
        self.orchestrator = LangGraphOrchestrator(self, self.logger)
        self.rag_service = RAGService()
        self.conversation_state: dict[Any, dict[str, Any]] = {}

    async def process_message(self, message: str, language: str = "en", session_id: int | None = None) -> str:
        msg = (message or "").strip()
        if not msg:
            return "Please share a request so I can help."
        state_key = session_id if session_id is not None else "default"
        history = self.conversation_state.setdefault(state_key, {"history": []})
        history["history"].append({"role": "user", "content": msg})

        prompt = await self.rag_service.augment_prompt(self.db, self.user.id, msg)
        response = await self._route_intent(msg.lower())
        if response == self._default_response():
            orchestrator_state = await self.orchestrator.run(msg, language=language, state={"session_id": state_key})
            response = (orchestrator_state.get("response") or "").strip()

        if not response:
            response = self._default_response()

        if settings.OPENAI_API_KEY and response == self._default_response():
            try:
                llm_resp = await self._call_llm(message, language)
                response = llm_resp or response
            except Exception:
                self.logger.exception("agent.llm_fallback_error")

        if language != "en":
            response = translate_text(response, language)

        history["history"].append({"role": "assistant", "content": response})
        return response

    async def process_message_stream(self, message: str, language: str = "en", session_id: int | None = None):
        msg = (message or "").strip()
        if not msg:
            yield "Please share a request so I can help."
            return
        state_key = session_id if session_id is not None else "default"
        history = self.conversation_state.setdefault(state_key, {"history": []})
        history["history"].append({"role": "user", "content": msg})

        response_text = ""
        try:
            response = await self._route_intent(msg.lower())
            if response == self._default_response():
                orchestrator_state = await self.orchestrator.run(msg, language=language, state={"session_id": state_key})
                response = (orchestrator_state.get("response") or "").strip()
            if not response:
                response = self._default_response()

            if settings.OPENAI_API_KEY and response == self._default_response():
                try:
                    llm_resp = await self._call_llm(message, language)
                    response = llm_resp or response
                except Exception:
                    self.logger.exception("agent.llm_fallback_error")

            if language != "en":
                response = translate_text(response, language)

            for word in response.split():
                response_text += word + " "
                yield word + " "
        except Exception as e:
            yield f"Error: {str(e)}"
        finally:
            history["history"].append({"role": "assistant", "content": response_text.strip()})

    async def _call_llm(self, message: str, language: str = "en") -> str | None:
        if not settings.OPENAI_API_KEY:
            return None
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
        system = (
            "You are a helpful assistant specialized for a poultry farm management app. "
            f"Answer concisely in {language} and, when appropriate, suggest actions like creating transactions or linking to reports."
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
        msg = self._normalize_query(msg)
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
                    "remove_stock",
                    {
                        "category": intent["category"],
                        "product_name": intent["product_name"],
                        "quantity": intent["quantity"],
                        "unit": intent["unit"],
                    },
                )
                if isinstance(result, dict) and result.get("error"):
                    return result["error"]
                return (
                    f"Removed {result['removed']} {result['unit']} from {result['product_name']} "
                    f"({result['category']}) inventory. Remaining {result['quantity']} {result['unit']}."
                )
        if self._is_stock_query(msg, "feed"):
            items = await self.mcp.execute("get_stock", {"category": "feed"})
            return self._format_stock("Feed", items)
        if self._is_stock_query(msg, "medicine"):
            items = await self.mcp.execute("get_stock", {"category": "medicine"})
            return self._format_stock("Medicine", items)
        if self._is_stock_query(msg, "vaccine"):
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
        if self._is_expense_query(msg, "feed"):
            data = await self.mcp.execute("get_expenses", {"category": "feed"})
            return f"Total feed expense: Rs. {data['total']:,.2f}"
        if self._is_expense_query(msg, "medicine"):
            data = await self.mcp.execute("get_expenses", {"category": "medicines"})
            return f"Total medicine expense: Rs. {data['total']:,.2f}"
        if self._is_profit_query(msg):
            data = await self.mcp.execute("get_profit_loss")
            pl = data["profit_loss"]
            status = "profit" if pl >= 0 else "loss"
            return (
                f"Overall {status}: Rs. {abs(pl):,.2f}\n"
                f"Revenue: Rs. {data['revenue']:,.2f}\n"
                f"Expenses: Rs. {data['expenses']:,.2f}"
            )
        if self._is_expense_query(msg):
            summary = await self.mcp.execute("get_monthly_summary")
            return (
                f"Monthly summary ({summary['month']}/{summary['year']}): "
                f"Revenue Rs. {summary['revenue']:,.2f}, Expenses Rs. {summary['expenses']:,.2f}, "
                f"Profit/Loss Rs. {summary['profit_loss']:,.2f}"
            )
        if "feed bill" in msg or "invoice" in msg or "document" in msg:
            query = msg.replace("show", "").replace("find", "").strip()
            docs = await self.mcp.execute("search_documents", {"query": query})
            if not docs:
                return "No matching documents found."
            lines = ["Matching documents:"] + [
                f"- {d['filename']} | {d.get('company') or 'Unknown'} | Rs. {d.get('cost') or 0}"
                for d in docs[:5]
            ]
            return "\n".join(lines)
        if self._is_fcr_query(msg):
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
        return self._default_response()

    def _is_stock_query(self, msg: str, category: str) -> bool:
        aliases = {
            "feed": ["feed", "feeds", "ration", "pellet"],
            "medicine": ["medicine", "medicines", "medical", "drug", "drugs", "tablet", "tablets"],
            "vaccine": ["vaccine", "vaccines", "vaccination"],
        }
        stock_terms = [
            "stock",
            "inventory",
            "remaining",
            "remain",
            "remains",
            "left",
            "available",
            "balance",
            "how much",
            "how many",
        ]
        return any(alias in msg for alias in aliases[category]) and any(term in msg for term in stock_terms)

    def _normalize_query(self, msg: str) -> str:
        replacements = {
            "meddince": "medicine",
            "meddicine": "medicine",
            "medcine": "medicine",
            "medicne": "medicine",
            "medince": "medicine",
            "medicin": "medicine",
            "stcok": "stock",
            "stok": "stock",
            "stck": "stock",
            "remaning": "remaining",
            "remianing": "remaining",
            "uch": "much",
        }
        normalized = msg
        for typo, correction in replacements.items():
            normalized = re.sub(rf"\b{re.escape(typo)}\b", correction, normalized)
        return normalized

    def _is_expense_query(self, msg: str, category: str | None = None) -> bool:
        expense_terms = ["expense", "expenses", "cost", "costs", "spent", "spend", "paid", "payment"]
        if not any(term in msg for term in expense_terms):
            return False
        if category is None:
            return True
        category_terms = {
            "feed": ["feed", "feeds", "ration", "pellet"],
            "medicine": ["medicine", "medicines", "medical", "drug", "drugs"],
        }
        return any(term in msg for term in category_terms[category])

    def _is_profit_query(self, msg: str) -> bool:
        return any(term in msg for term in ["profit", "loss", "p&l", "income summary", "overall profit"])

    def _is_fcr_query(self, msg: str) -> bool:
        return "fcr" in msg or "feed conversion" in msg

    def _default_response(self) -> str:
        return (
            "I'm your Poultry ERP assistant. Ask about inventory, finances, documents, "
            "calculations, or reports. Examples: 'How much feed stock remains?', "
            "'Show overall profit.', 'Show feed bills from May.'"
        )

    def parse_purchase_request(self, text: str) -> dict[str, Any] | None:
        lowered = text.lower()
        if not any(keyword in lowered for keyword in ["bought", "bought", "purchase", "purchased", "from", "for"]):
            return None
        quantity_match = re.search(r"(\d+(?:\.\d+)?)\s*(bags?|kg|kgs|units?|doses?|pcs|packs?)", text, re.I)
        amount_match = re.search(r"(?:for|₹|rs\.?)\s*([\d,]+(?:\.\d{1,2})?)", text, re.I)
        supplier_match = re.search(r"(?:from|by)\s+([A-Za-z0-9 .&-]+)", text, re.I)
        product = "feed"
        if "medicine" in lowered:
            product = "medicine"
        elif "vaccine" in lowered:
            product = "vaccine"
        elif "feed" in lowered:
            product = "feed"
        elif re.search(r"\b(egg|broiler|layer)\b", lowered):
            product = "feed"

        quantity = float(quantity_match.group(1)) if quantity_match else 1.0
        unit = (quantity_match.group(2) or "bags").lower() if quantity_match else "bags"
        if unit.startswith("bag"):
            unit = "bags"
        elif unit in {"kg", "kgs"}:
            unit = "kg"
        amount = float(amount_match.group(1).replace(",", "")) if amount_match else 0.0
        supplier = supplier_match.group(1).strip() if supplier_match else "Unknown Supplier"
        category = "feed"
        if product == "medicine":
            category = "medicine"
        elif product == "vaccine":
            category = "vaccine"
        return {
            "product": product,
            "quantity": quantity,
            "unit": unit,
            "supplier": supplier,
            "amount": amount,
            "category": category,
        }

    def _parse_inventory_command(self, text: str) -> dict[str, Any] | None:
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

    def _format_stock(self, label: str, items: list[dict[str, Any]]) -> str:
        if not items:
            return f"No {label.lower()} items in inventory."
        totals_by_unit: dict[str, float] = {}
        for item in items:
            unit = str(item.get("unit") or "units")
            totals_by_unit[unit] = totals_by_unit.get(unit, 0) + float(item.get("quantity") or 0)
        totals = ", ".join(f"{quantity:g} {unit}" for unit, quantity in totals_by_unit.items())
        lines = [f"{label} Inventory", f"Total stock: {totals} across {len(items)} item(s)."]
        lines.extend(
            f"- {i['product_name']}: {float(i['quantity']):g} {i['unit']}"
            for i in items
        )
        return "\n".join(lines)
