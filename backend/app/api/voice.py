import re

from fastapi import APIRouter, Depends, Form
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.voice_service import VoiceCommandService

router = APIRouter(prefix="/voice", tags=["Voice Assistant"])


def _get_voice_service(current_user: User, db) -> VoiceCommandService:
    from app.agent.poultry_agent import PoultryAgent

    return VoiceCommandService(PoultryAgent(user=current_user, db=db))

LANG_MAP = {
    "en": "en-US",
    "kn": "kn-IN",
    "hi": "hi-IN",
    "te": "te-IN",
    "ta": "ta-IN",
    "ml": "ml-IN",
    "mr": "mr-IN",
}


class SpeechTextRequest(BaseModel):
    text: str
    language: str | None = None


@router.get("/language-code")
async def get_language_code(current_user: User = Depends(get_current_user)):
    lang = current_user.preferred_language.value
    return {"code": lang, "speech_code": LANG_MAP.get(lang, "en-US")}


@router.post("/speech-to-text")
async def speech_to_text(
    transcript: str = Form(...),
    language: str = Form("en"),
    current_user: User = Depends(get_current_user),
):
    """Accept transcript from client-side Web Speech API."""
    return {
        "text": transcript.strip(),
        "language": language or current_user.preferred_language.value,
    }


@router.post("/text-to-speech")
async def text_to_speech(
    data: SpeechTextRequest,
    current_user: User = Depends(get_current_user),
):
    """Return text for client-side speechSynthesis (browser TTS)."""
    lang = data.language or current_user.preferred_language.value
    return {
        "text": data.text,
        "language": lang,
        "speech_code": LANG_MAP.get(lang, "en-US"),
        "use_browser_tts": True,
    }


@router.post("/parse-command")
async def parse_voice_command(
    data: SpeechTextRequest,
    current_user: User = Depends(get_current_user),
):
    """Parse natural language voice commands for ERP actions and return a structured result."""
    text = data.text or ""
    lowered = text.lower()
    result = {"action": None, "parsed": {}}

    add_match = re.search(
        r"(?:add|receive|received|purchase|purchased|got|bought|stocked)\s+(\d+(?:\.\d+)?)\s*(kg|g|grams|bags|units|doses|ml|l)?\s+(?:of\s+)?(.+)",
        lowered,
    )
    if add_match:
        product = add_match.group(3).strip().title()
        category = "feed"
        for cat in ("feed", "medicine", "vaccine"):
            if cat in product.lower():
                category = cat
                product = re.sub(rf"\b{cat}\b", "", product, flags=re.I).strip().title() or product
        return {
            "action": "add_stock",
            "parsed": {
                "quantity": float(add_match.group(1)),
                "unit": add_match.group(2) or "kg",
                "product_name": product,
                "category": category,
            },
        }

    remove_match = re.search(
        r"(?:remove|use|used|consume|consumed|deduct|delete|discard|reduce|take)\s+(\d+(?:\.\d+)?)\s*(kg|g|grams|bags|units|doses|ml|l)?\s+(?:of\s+)?(.+)",
        lowered,
    )
    if remove_match:
        product = remove_match.group(3).strip().title()
        category = "feed"
        for cat in ("feed", "medicine", "vaccine"):
            if cat in product.lower():
                category = cat
                product = re.sub(rf"\b{cat}\b", "", product, flags=re.I).strip().title() or product
        return {
            "action": "remove_stock",
            "parsed": {
                "quantity": float(remove_match.group(1)),
                "unit": remove_match.group(2) or "kg",
                "product_name": product,
                "category": category,
            },
        }

    if "expense" in lowered or "charges" in lowered or "cost" in lowered:
        amount_match = re.search(r"(?:₹|rs\.?)\s*([\d,]+(?:\.\d{1,2})?)", lowered)
        if amount_match:
            result = {
                "action": "record_expense",
                "parsed": {"amount": float(amount_match.group(1).replace(",", ""))},
            }
            return result

    if any(keyword in lowered for keyword in ["dashboard", "summary", "status"]):
        return {"action": "dashboard_summary", "parsed": {}}
    if any(keyword in lowered for keyword in ["document", "bill", "invoice", "search"]):
        return {"action": "search_documents", "parsed": {"query": text}}
    if "notification" in lowered or "notify" in lowered:
        return {"action": "notifications", "parsed": {}}
    if any(keyword in lowered for keyword in ["report", "generate"]):
        return {"action": "generate_report", "parsed": {}}
    return result


@router.post("/command")
async def handle_voice_command(
    data: SpeechTextRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    from app.core.database import get_db

    service = _get_voice_service(current_user, db)
    response = await service.handle_voice_command(data.text, language=data.language or current_user.preferred_language.value)
    return response
