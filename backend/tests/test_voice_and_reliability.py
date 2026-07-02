from app.services.dashboard_cache import DashboardCache
from app.services.reliability_service import RetryPolicy
from app.services.voice_service import VoiceCommandService


class DummyAgent:
    def __init__(self):
        self.conversation_state = {"default": {"history": []}}

    async def process_message(self, message, language="en", session_id=None):
        return f"Handled: {message}"


def test_dashboard_cache_stores_and_reuses_values():
    cache = DashboardCache(ttl_seconds=60)
    cache.set("dashboard", {"summary": "ok"})
    assert cache.get("dashboard") == {"summary": "ok"}


def test_retry_policy_retries_then_returns():
    attempts = {"count": 0}

    async def flaky():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise RuntimeError("temporary")
        return "done"

    policy = RetryPolicy(max_attempts=3, delay_seconds=0)
    result = __import__("asyncio").run(policy.run(flaky))
    assert result == "done"


def test_voice_service_returns_conversational_response():
    service = VoiceCommandService(DummyAgent())
    response = __import__("asyncio").run(service.handle_voice_command("Add 20 bags of starter feed."))
    assert response["action"] == "assistant"
    assert "Handled" in response["response"]
