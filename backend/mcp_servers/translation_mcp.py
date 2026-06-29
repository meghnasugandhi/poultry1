"""Translation MCP Server — multi-language support."""

SUPPORTED_LANGUAGES = ["en", "kn", "hi", "te", "ta", "ml", "mr"]

TOOLS = [
    {
        "name": "translate_text",
        "description": "Translate text to target language",
        "parameters": {"text": "string", "target_language": "string"},
    },
    {
        "name": "translate_ui",
        "description": "Translate UI labels for dashboard, reports, notifications",
        "parameters": {"keys": "array", "target_language": "string"},
    },
]
