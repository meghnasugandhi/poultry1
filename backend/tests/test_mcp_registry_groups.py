from types import SimpleNamespace

from app.mcp.registry import MCPRegistry


def test_registry_exposes_grouped_tool_catalog():
    registry = MCPRegistry(db=object(), user=SimpleNamespace(id=1))
    catalog = registry.get_tool_catalog()

    assert "inventory" in catalog
    assert "finance" in catalog
    assert "reports" in catalog
    assert "add_stock" in catalog["inventory"]
    assert "create_expense" in catalog["finance"]
    assert "daily_report" in catalog["reports"]
