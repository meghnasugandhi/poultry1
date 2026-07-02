import asyncio
import re
from typing import Any

from app.agent.poultry_agent import PoultryAgent
from app.core.logging import get_logger

logger = get_logger("poultry.voice")


class VoiceCommandService:
    def __init__(self, agent: PoultryAgent) -> None:
        self.agent = agent
        self.logger = logger

    async def handle_voice_command(self, text: str, language: str = "en", session_id: int | None = None) -> dict[str, Any]:
        normalized = (text or "").strip()
        if not normalized:
            return {"action": "none", "response": "Please say what you want to do.", "followUp": []}

        lowered = normalized.lower()
        action = "general"

        if any(keyword in lowered for keyword in ["add", "remove", "record", "generate", "summary", "search", "notify", "follow-up", "show", "calculate"]):
            action = "assistant"
            if "feed stock" in lowered or "feed remain" in lowered:
                action = "feed_query"
            elif "medicine" in lowered:
                action = "medicine_query"
            elif "expense" in lowered or "cost" in lowered:
                action = "expense_query"

        response_text = await self.agent.process_message(normalized, language=language, session_id=session_id)
        self.logger.info("voice.command_processed", extra={"action": action, "session_id": session_id})
        state = getattr(self.agent, "conversation_state", None)
        context = []
        if isinstance(state, dict):
            context = state.get(session_id if session_id is not None else "default", {}).get("history", [])[-4:]

        followUp = self._suggest_follow_up(action, response_text)
        return {
            "action": action,
            "response": response_text,
            "conversation_context": context,
            "followUp": followUp,
        }

    def _suggest_follow_up(self, action: str, response: str) -> list[str]:
        suggestions = []
        if "Feed stock:" in response or "feed" in action:
            suggestions = ["Add more feed", "View feed expenses", "Generate feed report"]
        elif "Medicine" in response or "medicine" in action:
            suggestions = ["Buy medicine", "Check expiry dates", "View medicine expenses"]
        elif "expense" in action or "₹" in response:
            suggestions = ["View all expenses", "Generate expense report", "Add expense manually"]
        elif "profit" in response.lower() or "revenue" in response.lower():
            suggestions = ["View monthly summary", "Generate profit report", "Add revenue entry"]
        elif "document" in action:
            suggestions = ["Upload another bill", "Search by date", "View all documents"]
        else:
            suggestions = ["Check feed stock", "View expenses", "Generate report"]
        return suggestions[:3]