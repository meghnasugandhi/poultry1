"""Database MCP Server — direct data access for the AI agent."""

TOOLS = [
    {
        "name": "query",
        "description": "Execute a read-only database query",
        "parameters": {"table": "string", "filters": "object", "limit": "number"},
    },
    {
        "name": "get_user_profile",
        "description": "Get farmer profile and farm information",
        "parameters": {"user_id": "number"},
    },
    {
        "name": "get_dashboard_stats",
        "description": "Get dashboard summary statistics",
        "parameters": {"user_id": "number"},
    },
]
