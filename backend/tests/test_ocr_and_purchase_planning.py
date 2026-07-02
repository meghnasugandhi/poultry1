import asyncio

from app.agent.langgraph_orchestrator import LangGraphOrchestrator
from app.agent.poultry_agent import PoultryAgent
from app.services.ocr_service import process_document_ocr


def test_purchase_request_parsing_and_multi_tool_plan():
    agent = object.__new__(PoultryAgent)
    agent.mcp = None
    orchestrator = LangGraphOrchestrator(agent)
    parsed = PoultryAgent.parse_purchase_request(
        object.__new__(PoultryAgent),
        "I bought 50 bags of feed from ABC Feed for ₹35000",
    )

    assert parsed is not None
    assert parsed["product"] == "feed"
    assert parsed["quantity"] == 50.0
    assert parsed["amount"] == 35000.0
    state = {"user_message": "I bought 50 bags of feed from ABC Feed for ₹35000"}
    plan = asyncio.run(orchestrator._plan_execution(state))
    tool_names = [step["tool"] for step in plan["plan"]]
    assert "add_stock" in tool_names
    assert "create_expense" in tool_names
    assert "dashboard_summary" in tool_names
    assert "daily_report" in tool_names


def test_ocr_service_returns_structured_purchase_data(tmp_path):
    sample = tmp_path / "invoice.txt"
    sample.write_text(
        "Suguna Feeds Pvt Ltd\nInvoice No: INV-2024-001\nTotal: Rs. 15,000\nQty: 500 kg\n10 bags\nSupplier: Suguna",
        encoding="utf-8",
    )

    result = asyncio.run(process_document_ocr(str(sample)))

    assert result["supplier_name"] == "Suguna"
    assert result["cost"] == 15000.0
    assert result["quantity"] == 500.0
    assert result["structured_data"]["supplier"] == "Suguna"
    assert result["structured_data"]["suggested_inventory_entry"]["quantity"] == 500.0
