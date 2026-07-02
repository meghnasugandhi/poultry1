import logging
from typing import Any

from app.services.ocr_service import process_document_ocr


class OCRToolService:
    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger("poultry.mcp.ocr")

    async def parse_bill(self, file_path: str) -> dict[str, Any]:
        return await process_document_ocr(file_path)

    async def verify_bill(self, file_path: str) -> dict[str, Any]:
        parsed = await self.parse_bill(file_path)
        confidence = parsed.get("confidence", 0.0)
        is_valid = confidence >= 0.5 and bool(parsed.get("cost"))
        return {"valid": is_valid, "confidence": confidence, "details": parsed}

    async def classify_document(self, file_path: str) -> dict[str, Any]:
        parsed = await self.parse_bill(file_path)
        text = (parsed.get("raw_text") or "").lower()
        if "invoice" in text or "bill" in text:
            return {"document_type": "invoice", "confidence": parsed.get("confidence", 0.0)}
        return {"document_type": "unknown", "confidence": parsed.get("confidence", 0.0)}

    async def extract_items(self, file_path: str) -> dict[str, Any]:
        parsed = await self.parse_bill(file_path)
        return {"items": [{"name": parsed.get("product_name"), "quantity": parsed.get("quantity"), "cost": parsed.get("cost")}]}
