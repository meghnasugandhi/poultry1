"""Finance MCP Server — revenue, expenses, and profit queries."""

TOOLS = [
    {
        "name": "get_expenses",
        "description": "Get expenses by category and date range",
        "parameters": {"category": "string", "start_date": "string", "end_date": "string"},
    },
    {
        "name": "get_revenue",
        "description": "Get revenue by category and date range",
        "parameters": {"category": "string", "start_date": "string", "end_date": "string"},
    },
    {
        "name": "get_profit_loss",
        "description": "Calculate profit or loss for a period",
        "parameters": {"start_date": "string", "end_date": "string"},
    },
    {
        "name": "get_monthly_summary",
        "description": "Get monthly financial summary",
        "parameters": {"month": "string", "year": "number"},
    },
]
