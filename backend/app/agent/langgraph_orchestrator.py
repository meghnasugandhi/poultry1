import logging
from typing import Any, TypedDict

from langgraph.graph import StateGraph, END


class AgentState(TypedDict, total=False):
    user_message: str
    language: str
    intent: str
    plan: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    errors: list[str]
    clarification: str | None
    response: str
    needs_clarification: bool


class LangGraphOrchestrator:
    def __init__(self, agent: Any, logger: logging.Logger | None = None):
        self.agent = agent
        self.logger = logger or logging.getLogger("poultry.agent.orchestrator")
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        builder = StateGraph(AgentState)
        builder.add_node("detect_intent", self._detect_intent)
        builder.add_node("plan_execution", self._plan_execution)
        builder.add_node("execute_tools", self._execute_tools)
        builder.add_node("clarify", self._clarify)
        builder.add_node("finalize", self._finalize)
        builder.set_entry_point("detect_intent")
        builder.add_edge("detect_intent", "plan_execution")
        builder.add_conditional_edges(
            "plan_execution",
            self._route_after_planning,
            {"clarify": "clarify", "execute": "execute_tools"},
        )
        builder.add_edge("execute_tools", "finalize")
        builder.add_edge("clarify", "finalize")
        builder.add_edge("finalize", END)
        return builder.compile()

    async def run(self, message: str, language: str = "en", state: dict[str, Any] | None = None) -> dict[str, Any]:
        initial_state: AgentState = {
            "user_message": message,
            "language": language,
            "plan": [],
            "tool_results": [],
            "errors": [],
            "clarification": None,
            "needs_clarification": False,
            "response": "",
        }
        if state:
            initial_state.update(state)
        result = await self.graph.ainvoke(initial_state)
        return result

    async def _detect_intent(self, state: AgentState) -> dict[str, Any]:
        message = (state.get("user_message") or "").strip()
        lowered = message.lower()
        intent = "general"
        if any(keyword in lowered for keyword in ["feed", "stock", "inventory", "medicine", "vaccine"]):
            intent = "inventory"
        elif any(keyword in lowered for keyword in ["expense", "income", "profit", "loss", "cash", "finance", "monthly"]):
            intent = "finance"
        elif any(keyword in lowered for keyword in ["report", "pdf", "excel", "export"]):
            intent = "reports"
        elif any(keyword in lowered for keyword in ["bill", "invoice", "ocr", "document", "extract"]):
            intent = "ocr"
        elif any(keyword in lowered for keyword in ["dashboard", "analytics", "farm"]):
            intent = "dashboard"
        elif any(keyword in lowered for keyword in ["notification", "email", "sms", "whatsapp", "push"]):
            intent = "notifications"
        elif any(keyword in lowered for keyword in ["voice", "speech", "translate", "language"]):
            intent = "voice"
        self.logger.info("agent.detect_intent", extra={"intent": intent, "user_message": message})
        return {"intent": intent}

    async def _plan_execution(self, state: AgentState) -> dict[str, Any]:
        message = (state.get("user_message") or "").strip()
        lowered = message.lower()
        plan: list[dict[str, Any]] = []
        purchase = None
        if hasattr(self.agent, "parse_purchase_request"):
            purchase = self.agent.parse_purchase_request(message)

        if purchase:
            plan.extend([
                {"tool": "add_stock", "reason": "inventory_update"},
                {"tool": "create_expense", "reason": "finance_entry"},
                {"tool": "dashboard_summary", "reason": "dashboard_update"},
                {"tool": "daily_report", "reason": "report_refresh"},
            ])
        elif any(keyword in lowered for keyword in ["add", "receive", "purchase", "stocked", "bought"]):
            plan.append({"tool": "add_stock", "reason": "inventory_update"})
        elif any(keyword in lowered for keyword in ["remove", "use", "consume", "deduct", "reduce"]):
            plan.append({"tool": "remove_stock", "reason": "inventory_update"})
        elif any(keyword in lowered for keyword in ["profit", "loss", "income", "expense", "cash", "finance", "monthly"]):
            plan.extend([
                {"tool": "profit_loss", "reason": "finance_summary"},
                {"tool": "monthly_finance", "reason": "monthly_finance"},
            ])
        elif any(keyword in lowered for keyword in ["report", "pdf", "excel", "export"]):
            plan.append({"tool": "daily_report", "reason": "report_generation"})
        elif any(keyword in lowered for keyword in ["dashboard", "analytics", "farm"]):
            plan.extend([
                {"tool": "dashboard_summary", "reason": "dashboard"},
                {"tool": "get_low_stock", "reason": "inventory_alerts"},
            ])
        elif any(keyword in lowered for keyword in ["document", "bill", "invoice", "ocr"]):
            plan.append({"tool": "parse_bill", "reason": "ocr"})
        elif self._is_stock_lookup(lowered):
            plan.append({"tool": "get_stock", "reason": "inventory_lookup"})
        elif any(keyword in lowered for keyword in ["low stock", "running low"]):
            plan.append({"tool": "get_low_stock", "reason": "inventory_lookup"})
        elif any(keyword in lowered for keyword in ["search", "find"]):
            plan.append({"tool": "search_documents", "reason": "search"})
        if not plan:
            plan.append({"tool": "dashboard_summary", "reason": "generic"})
        return {"plan": plan}

    async def _execute_tools(self, state: AgentState) -> dict[str, Any]:
        plan = state.get("plan") or []
        tool_results: list[dict[str, Any]] = []
        errors: list[str] = []
        for step in plan:
            tool_name = step.get("tool")
            if not tool_name:
                continue
            attempts = 0
            while attempts < 2:
                try:
                    result = await self._invoke_tool(tool_name, state)
                    tool_results.append({"tool": tool_name, "result": result})
                    break
                except Exception as exc:
                    attempts += 1
                    self.logger.exception("agent.tool_error", extra={"tool": tool_name, "attempt": attempts})
                    if attempts >= 2:
                        errors.append(str(exc))
        return {"tool_results": tool_results, "errors": errors}

    async def _invoke_tool(self, tool_name: str, state: AgentState) -> Any:
        message = (state.get("user_message") or "").strip()
        lowered = message.lower()
        params: dict[str, Any] = {}
        purchase = None
        if hasattr(self.agent, "parse_purchase_request"):
            purchase = self.agent.parse_purchase_request(message)

        if tool_name == "add_stock":
            if purchase:
                params = {
                    "category": purchase["category"],
                    "product_name": purchase["product"],
                    "quantity": purchase["quantity"],
                    "unit": purchase["unit"],
                }
            else:
                parsed = self.agent._parse_inventory_command(message)
                if parsed:
                    params = {
                        "category": parsed["category"],
                        "product_name": parsed["product_name"],
                        "quantity": parsed["quantity"],
                        "unit": parsed["unit"],
                    }
        elif tool_name == "create_expense":
            if purchase:
                params = {
                    "amount": purchase["amount"],
                    "description": f"Purchase from {purchase['supplier']}",
                    "category": purchase["category"],
                }
        elif tool_name == "remove_stock":
            parsed = self.agent._parse_inventory_command(message)
            if parsed:
                params = {
                    "category": parsed["category"],
                    "product_name": parsed["product_name"],
                    "quantity": parsed["quantity"],
                    "unit": parsed["unit"],
                }
        elif tool_name == "profit_loss":
            params = {}
        elif tool_name == "daily_report":
            params = {"report_type": "inventory"}
        elif tool_name == "dashboard_summary":
            params = {}
        elif tool_name == "parse_bill":
            params = {"file_path": "uploads/test_invoice.txt"}
        elif tool_name == "get_stock":
            category = None
            if "medicine" in lowered or "medical" in lowered:
                category = "medicine"
            elif "vaccine" in lowered or "vaccination" in lowered:
                category = "vaccine"
            elif "feed" in lowered:
                category = "feed"
            params = {"category": category}
        elif tool_name == "get_low_stock":
            params = {}
        elif tool_name == "search_documents":
            params = {"query": message}
        return await self.agent.mcp.execute(tool_name, params)

    async def _clarify(self, state: AgentState) -> dict[str, Any]:
        message = (state.get("user_message") or "").strip()
        clarification = (
            "I can help with inventory, finance, reports, documents, or dashboard insights. "
            f"Please be more specific about what you want to do with: {message or 'your request'}."
        )
        return {"clarification": clarification, "needs_clarification": True}

    async def _finalize(self, state: AgentState) -> dict[str, Any]:
        if state.get("clarification"):
            return {"response": state["clarification"]}
        tool_results = state.get("tool_results") or []
        errors = state.get("errors") or []
        if errors:
            return {"response": "I hit an issue while processing that request: " + "; ".join(errors)}
        if not tool_results:
            return {"response": "I’m ready to help with inventory, finance, reports, and documents."}
        first = tool_results[0]["result"]
        if isinstance(first, dict) and first.get("error"):
            return {"response": first["error"]}
        if isinstance(first, list):
            return {"response": self._format_list_result(first)}
        if isinstance(first, dict):
            return {"response": self._format_dict_result(first)}
        return {"response": str(first)}

    def _route_after_planning(self, state: AgentState) -> str:
        if state.get("needs_clarification"):
            return "clarify"
        return "execute"

    def _format_list_result(self, result: list[dict[str, Any]]) -> str:
        if not result:
            return "No matching records found."
        if all("product_name" in item and "quantity" in item for item in result):
            lines = ["Inventory:"]
            lines.extend(
                f"- {item['product_name']}: {item['quantity']} {item.get('unit', '')}".strip()
                for item in result[:10]
            )
            return "\n".join(lines)
        return "\n".join(f"- {self._format_dict_result(item)}" for item in result[:5])

    def _format_dict_result(self, result: dict[str, Any]) -> str:
        if "quantity" in result and "product_name" in result:
            return f"Updated {result['product_name']} to {result['quantity']} {result.get('unit', '')}".strip()
        if "profit_loss" in result:
            return f"Profit/Loss: ₹{result['profit_loss']:,.2f}"
        if "path" in result:
            return f"Report generated at {result['path']}"
        if "status" in result and result.get("status") == "not_implemented":
            return "That voice feature is not enabled in the current setup."
        return str(result)

    def _is_stock_lookup(self, message: str) -> bool:
        item_terms = ["feed", "medicine", "medical", "vaccine", "vaccination", "stock", "inventory"]
        stock_terms = ["stock", "inventory", "remain", "remaining", "remains", "left", "available", "balance"]
        return any(term in message for term in item_terms) and any(term in message for term in stock_terms)
