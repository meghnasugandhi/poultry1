"""Inventory MCP Server — stock queries and mutations."""

TOOLS = [
    {
        "name": "get_stock",
        "description": "Get inventory stock by category (feed, medicine, vaccine)",
        "parameters": {"category": "string"},
    },
    {
        "name": "add_stock",
        "description": "Add or update inventory quantity",
        "parameters": {"category": "string", "product_name": "string", "quantity": "number", "unit": "string"},
    },
    {
        "name": "adjust_stock",
        "description": "Adjust inventory quantity up or down",
        "parameters": {"category": "string", "product_name": "string", "quantity_change": "number", "unit": "string"},
    },
    {
        "name": "get_low_stock",
        "description": "Get items below reorder level",
        "parameters": {},
    },
    {
        "name": "get_expiring",
        "description": "Get items expiring within 30 days",
        "parameters": {},
    },
]
