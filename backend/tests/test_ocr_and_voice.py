from app.services.background_jobs import BackgroundJobRunner
from app.services.voice_service import VoiceCommandService


class DummyAgent:
    def __init__(self):
        self.conversation_state = {"default": {"history": []}}

    async def process_message(self, message, language="en", session_id=None):
        return f"reply:{message}:{language}"


def test_voice_service_returns_action_and_response():
    service = VoiceCommandService(DummyAgent())
    response = __import__("asyncio").run(service.handle_voice_command("show summary", language="hi"))
    assert response["action"] == "assistant"
    assert response["response"].startswith("reply")


def test_background_job_runner_can_run_ocr_job_callback():
    runner = BackgroundJobRunner()
    observed = {}

    async def callback(result):
        observed["result"] = result

    __import__("asyncio").run(runner.run_ocr_job("dummy.pdf", callback))
    assert "result" in observed
