"""Report MCP Server — generate and export reports."""

TOOLS = [
    {
        "name": "generate_report",
        "description": "Generate a report (feed_expense, medicine_expense, inventory, profit_loss, vaccination, sales, batch)",
        "parameters": {"report_type": "string", "format": "pdf|excel"},
    },
    {
        "name": "list_reports",
        "description": "List available report types",
        "parameters": {},
    },
]
