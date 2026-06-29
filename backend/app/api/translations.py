from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.models.user import User
from app.services.translation_service import get_ui_bundle, translate_text

router = APIRouter(prefix="/translations", tags=["Multi-Language"])


@router.get("/ui")
async def get_translations(current_user: User = Depends(get_current_user)):
    lang = current_user.preferred_language.value
    return {"language": lang, "labels": get_ui_bundle(lang)}


@router.post("/translate")
async def translate(
    text: str,
    target_language: str | None = None,
    current_user: User = Depends(get_current_user),
):
    lang = target_language or current_user.preferred_language.value
    return {"original": text, "translated": translate_text(text, lang), "language": lang}
