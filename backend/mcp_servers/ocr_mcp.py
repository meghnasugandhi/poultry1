"""OCR MCP Server — extract data from invoices and images."""

TOOLS = [
    {
        "name": "extract_invoice",
        "description": "OCR extraction from invoice/bill image or PDF",
        "parameters": {"file_path": "string"},
    },
    {
        "name": "validate_extraction",
        "description": "AI validation of OCR extracted fields",
        "parameters": {"extracted_data": "object"},
    },
]

CONFIDENCE_THRESHOLD = 0.90
