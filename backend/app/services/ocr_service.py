import re
from datetime import date, datetime
import os
import httpx

from app.core.config import settings


def _extract_text_from_file(file_path: str) -> str:
    lower = file_path.lower()
    if lower.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
        try:
            from PIL import Image

            img = Image.open(file_path)
            # Basic metadata fallback when OCR engine unavailable
            return f"Image document {img.size[0]}x{img.size[1]}"
        except Exception:
            return ""
    if lower.endswith((".txt", ".csv")):
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    return ""


def _normalize_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_date(text: str) -> date | None:
    patterns = [
        r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
        r"(\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2})",
    ]
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            raw = match.group(1).replace(".", "/").replace("-", "/")
            for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d/%m/%y"):
                try:
                    return datetime.strptime(raw, fmt).date()
                except ValueError:
                    continue
    return None


def _parse_fields(text: str) -> dict:
    normalized = _normalize_text(text)
    fields: dict = {
        "company_name": None,
        "product_name": None,
        "quantity": None,
        "number_of_bags": None,
        "cost": None,
        "invoice_date": None,
        "invoice_number": None,
        "supplier_name": None,
    }

    invoice_match = re.search(
        r"(?:invoice|bill|inv)(?:\s*(?:no|number|#))?\s*[:\-]?\s*([A-Z0-9\-/]+)",
        normalized,
        re.I,
    )
    if invoice_match:
        fields["invoice_number"] = invoice_match.group(1).strip()

    cost_matches = re.findall(r"(?:total|grand total|amount|net amount|cost|rs\.?|₹)\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", normalized, re.I)
    if cost_matches:
        fields["cost"] = float(cost_matches[-1].replace(",", ""))

    qty_match = re.search(r"(?:qty|quantity|weight)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)\s*(?:kg|bags|units|pcs|pack)?", normalized, re.I)
    if qty_match:
        fields["quantity"] = float(qty_match.group(1).replace(",", ""))

    bags_match = re.search(r"(\d+)\s*bags?", normalized, re.I)
    if bags_match:
        fields["number_of_bags"] = int(bags_match.group(1))

    supplier_match = re.search(r"(?:supplier|vendor|from|sold by)\s*[:\-]?\s*([A-Za-z0-9 &.\-]+)", normalized, re.I)
    if supplier_match:
        fields["supplier_name"] = supplier_match.group(1).strip()[:255]

    product_match = re.search(r"(?:product|item|description|name)\s*[:\-]?\s*([A-Za-z0-9 \-/]+)", normalized, re.I)
    if product_match:
        fields["product_name"] = product_match.group(1).strip()[:255]

    lines = [ln.strip() for ln in normalized.splitlines() if ln.strip()]
    if lines and not fields["company_name"]:
        fields["company_name"] = lines[0][:255]

    fields["invoice_date"] = _parse_date(normalized)
    return fields


def _compute_confidence(fields: dict) -> float:
    keys = ["company_name", "product_name", "quantity", "cost", "invoice_date", "invoice_number", "supplier_name"]
    filled = sum(1 for k in keys if fields.get(k) is not None)
    base = round(filled / len(keys), 2)
    if fields.get("cost") is not None and fields.get("supplier_name") is not None:
        base = min(1.0, round(base + 0.1, 2))
    return base


async def process_document_ocr(file_path: str) -> dict:
    raw_text = ""

    # Prefer cloud OCR (OCR.Space) if configured
    if settings.OCR_SPACE_API_KEY:
        try:
            url = "https://api.ocr.space/parse/image"
            with open(file_path, "rb") as f:
                files = {"file": f}
                data = {"apikey": settings.OCR_SPACE_API_KEY, "language": "eng", "isOverlayRequired": False}
                async with httpx.AsyncClient(timeout=60.0) as client:
                    r = await client.post(url, data=data, files=files)
            r.raise_for_status()
            j = r.json()
            parsed = j.get("ParsedResults")
            if parsed and len(parsed) > 0:
                raw_text = parsed[0].get("ParsedText", "")
        except Exception:
            raw_text = ""

    # Fallback to local Tesseract if available
    if not raw_text:
        try:
            import pytesseract
            from PIL import Image

            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                raw_text = pytesseract.image_to_string(Image.open(file_path))
            elif file_path.lower().endswith('.pdf'):
                # try converting first page via pypdf if available
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                texts = [page.extract_text() or "" for page in reader.pages]
                raw_text = "\n".join(texts)
        except Exception:
            # last fallback: basic extractor
            raw_text = _extract_text_from_file(file_path)
    fields = _parse_fields(raw_text)
    confidence = _compute_confidence(fields)
    return {
        **fields,
        "confidence": confidence,
        "raw_text": raw_text[:5000] if raw_text else "",
    }
