import base64
import os
import re
import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel

from app.core.config import settings
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/voice", tags=["Voice Assistant"])

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
    """Parse natural language voice commands for inventory updates."""
    text = data.text.lower()
    result = {"action": None, "parsed": {}}

    add_match = re.search(
        r"(?:add|receive|received|purchase|purchased|got|bought|stocked)\s+(\d+(?:\.\d+)?)\s*(kg|g|grams|bags|units|doses|ml|l)?\s+(?:of\s+)?(.+)",
        text,
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
        text,
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
    return result
