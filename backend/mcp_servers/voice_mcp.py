"""Voice MCP Server — speech-to-text and text-to-speech."""

SUPPORTED_LANGUAGES = ["en", "kn", "hi", "te", "ta", "ml", "mr"]

TOOLS = [
    {
        "name": "speech_to_text",
        "description": "Convert speech audio to text",
        "parameters": {"audio_data": "bytes", "language": "string"},
    },
    {
        "name": "text_to_speech",
        "description": "Convert text to speech audio in farmer's preferred language",
        "parameters": {"text": "string", "language": "string"},
    },
]
