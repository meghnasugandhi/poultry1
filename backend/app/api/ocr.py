from fastapi import APIRouter
import shutil
import httpx
from app.core.config import settings

router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.get("/health")
async def ocr_health():
    result = {"ocr_space": None, "tesseract": None}

    # Check OCR.Space if key configured
    if settings.OCR_SPACE_API_KEY:
        try:
            url = "https://api.ocr.space/parse/image"
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(url, data={"apikey": settings.OCR_SPACE_API_KEY, "language": "eng", "isOverlayRequired": False})
            result["ocr_space"] = {"reachable": True, "status_code": r.status_code}
        except Exception as e:
            result["ocr_space"] = {"reachable": False, "error": str(e)}
    else:
        result["ocr_space"] = {"configured": False}

    # Check local Tesseract
    tesseract_path = shutil.which("tesseract")
    result["tesseract"] = {"installed": bool(tesseract_path), "path": tesseract_path}

    return result
