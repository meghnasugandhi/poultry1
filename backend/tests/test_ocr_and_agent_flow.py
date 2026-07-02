import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.agent.langgraph_orchestrator import LangGraphOrchestrator
from app.services import ocr_service


def test_process_document_ocr_returns_structured_data(monkeypatch):
    monkeypatch.setattr(
        ocr_service,
        "_extract_text_from_file",
        lambda path: "Invoice\nSupplier: ABC Feed\nProduct: Broiler Feed\nQuantity: 50 bags\nTotal: ₹35000",
    )

    result = asyncio.run(ocr_service.process_document_ocr("dummy.jpg"))

    assert result["confidence"] >= 0
    assert result["pages"] == [
        "Invoice\nSupplier: ABC Feed\nProduct: Broiler Feed\nQuantity: 50 bags\nTotal: ₹35000"
    ]
    assert result["structured_data"]["supplier"] == "ABC Feed"
    assert result["structured_data"]["quantity"] == 50
    assert result["structured_data"]["amount"] == 35000.0


def test_purchase_intent_plan_executes_multiple_tools():
    class DummyAgent:
        def __init__(self):
            self.mcp = SimpleNamespace(execute=AsyncMock(return_value={"ok": True}))
            self.conversation_state = {}

        def _parse_inventory_command(self, text):
            return None

        def parse_purchase_request(self, text):
            return {
                "product": "feed",
                "quantity": 50,
                "unit": "bags",
                "supplier": "ABC Feed",
                "amount": 35000,
                "category": "feed",
            }

    agent = DummyAgent()
    orchestrator = LangGraphOrchestrator(agent)

    state = asyncio.run(orchestrator._plan_execution({"user_message": "I bought 50 bags of feed from ABC Feed for ₹35,000."}))

    tool_names = [step["tool"] for step in state["plan"]]
    assert "add_stock" in tool_names
    assert "create_expense" in tool_names
    assert "dashboard_summary" in tool_names
    assert "daily_report" in tool_names
