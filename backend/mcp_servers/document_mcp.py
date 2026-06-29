"""Document MCP Server — document search and retrieval."""

TOOLS = [
    {
        "name": "search_documents",
        "description": "Search documents by keyword, type, or date range",
        "parameters": {"query": "string", "document_type": "string", "month": "string"},
    },
    {
        "name": "get_document",
        "description": "Get document details by ID",
        "parameters": {"document_id": "number"},
    },
    {
        "name": "download_document",
        "description": "Download original document file",
        "parameters": {"document_id": "number"},
    },
]
