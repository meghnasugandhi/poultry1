"""Inventory MCP Server — stock queries and mutations."""

TOOLS = [
    {
        "name": "get_stock",
        "description": "Get inventory stock by category (feed, medicine, vaccine)",
        "parameters": {"category": "string"},
    },
    {
        "name": "add_stock",
        "description": "Add new inventory item",
        "parameters": {"category": "string", "product_name": "string", "quantity": "number"},
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
