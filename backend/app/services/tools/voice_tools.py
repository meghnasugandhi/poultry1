import logging
from typing import Any


class VoiceToolService:
    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger("poultry.mcp.voice")

    async def speech_to_text(self, audio_path: str) -> dict[str, Any]:
        self.logger.info("voice.speech_to_text", extra={"audio_path": audio_path})
        return {"text": "", "status": "not_implemented"}

    async def text_to_speech(self, text: str, language: str = "en") -> dict[str, Any]:
        self.logger.info("voice.text_to_speech", extra={"language": language})
        return {"audio_path": None, "status": "not_implemented", "text": text}

    async def language_detection(self, text: str) -> dict[str, Any]:
        return {"language": "en", "confidence": 1.0}
