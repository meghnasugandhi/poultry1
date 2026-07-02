import os
import re
from datetime import date, datetime
from typing import Any

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


def _parse_fields(text: str) -> dict[str, Any]:
    normalized = _normalize_text(text)
    fields: dict[str, Any] = {
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

    qty_match = re.search(r"(?:qty|quantity|weight)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)\s*(?:kg|bags|units|pcs|pack|packs)?", normalized, re.I)
    if qty_match:
        fields["quantity"] = float(qty_match.group(1).replace(",", ""))

    bags_match = re.search(r"(\d+)\s*bags?", normalized, re.I)
    if bags_match:
        fields["number_of_bags"] = int(bags_match.group(1))

    supplier_match = re.search(r"(?:supplier|vendor|from|sold by)\s*[:\-]?\s*([A-Za-z0-9 &.\-]+)", normalized, re.I)
    if supplier_match:
        # Trim common OCR spillover like "ABC Feed Product" when Product line follows.
        supplier_value = supplier_match.group(1).strip()
        supplier_value = re.split(r"\bproduct\b\s*[:\-]?", supplier_value, flags=re.I)[0].strip()
        supplier_value = re.split(r"\bquantity\b\s*[:\-]?", supplier_value, flags=re.I)[0].strip()
        supplier_value = re.split(r"\btotal\b\s*[:\-]?", supplier_value, flags=re.I)[0].strip()
        fields["supplier_name"] = supplier_value[:255]


    product_match = re.search(r"(?:product|item|description|name)\s*[:\-]?\s*([A-Za-z0-9 \-/]+)", normalized, re.I)
    if product_match:
        fields["product_name"] = product_match.group(1).strip()[:255]

    if not fields["product_name"]:
        for keyword in ["feed", "medicine", "vaccine", "broiler", "layer"]:
            if keyword in normalized.lower():
                fields["product_name"] = keyword.title()
                break

    lines = [ln.strip() for ln in normalized.splitlines() if ln.strip()]
    if lines and not fields["company_name"]:
        fields["company_name"] = lines[0][:255]

    fields["invoice_date"] = _parse_date(normalized)
    return fields


def _compute_confidence(fields: dict[str, Any]) -> float:
    keys = ["company_name", "product_name", "quantity", "cost", "invoice_date", "invoice_number", "supplier_name"]
    filled = sum(1 for k in keys if fields.get(k) is not None)
    base = round(filled / len(keys), 2)
    if fields.get("cost") is not None and fields.get("supplier_name") is not None:
        base = min(1.0, round(base + 0.1, 2))
    return base


def _build_structured_data(fields: dict[str, Any], raw_text: str) -> dict[str, Any]:
    normalized = _normalize_text(raw_text).lower()
    document_type = "purchase_receipt"
    if "invoice" in normalized or "sales" in normalized:
        document_type = "sales_invoice"
    elif "medicine" in normalized:
        document_type = "medicine_bill"
    elif "vaccine" in normalized:
        document_type = "vaccine_bill"
    elif "feed" in normalized:
        document_type = "feed_bill"

    quantity = fields.get("quantity")
    if quantity is None and fields.get("number_of_bags") is not None:
        quantity = float(fields["number_of_bags"])

    return {
        "supplier": fields.get("supplier_name"),
        "product": fields.get("product_name"),
        "quantity": quantity,
        "amount": fields.get("cost"),
        "document_type": document_type,
        "invoice_date": fields.get("invoice_date"),
        "invoice_number": fields.get("invoice_number"),
        "suggested_inventory_entry": {
            "product_name": fields.get("product_name"),
            "quantity": quantity,
            "unit": "bags" if fields.get("number_of_bags") is not None else "kg",
            "supplier": fields.get("supplier_name"),
        },
        "suggested_finance_entry": {
            "amount": fields.get("cost"),
            "description": f"Parsed from OCR for {fields.get('product_name') or 'document'}",
            "supplier": fields.get("supplier_name"),
        },
    }


def _preprocess_image(image):
    try:
        from PIL import ImageFilter, ImageOps
    except Exception:
        return image

    img = image.convert("L")
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.MedianFilter(size=3))
    return img


async def _ocr_image_file(file_path: str) -> str:
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        return ""

    image = Image.open(file_path)
    image = image.copy()
    variants = [image, _preprocess_image(image)]
    texts: list[str] = []
    for variant in variants:
        try:
            text = pytesseract.image_to_string(variant)
            if text.strip():
                texts.append(text.strip())
        except Exception:
            continue
    return "\n".join(texts)


async def process_document_ocr(file_path: str) -> dict[str, Any]:
    pages: list[str] = []
    raw_text = ""

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

    if not raw_text:
        lower = file_path.lower()
        if lower.endswith(".pdf"):
            try:
                from pypdf import PdfReader

                reader = PdfReader(file_path)
                pages = [page.extract_text() or "" for page in reader.pages]
                raw_text = "\n\n".join(pages)
            except Exception:
                if not hasattr(file_path, "read") and not os.path.exists(file_path):
                    raw_text = ""
                else:
                    raw_text = _extract_text_from_file(file_path)
        elif lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
            text = await _ocr_image_file(file_path)
            if text:
                pages = [text]
                raw_text = text
            else:
                raw_text = _extract_text_from_file(file_path)
        else:
            raw_text = _extract_text_from_file(file_path)

    if not pages and raw_text:
        pages = [raw_text]

    fields = _parse_fields(raw_text)
    confidence = _compute_confidence(fields)
    if confidence < 0.6 and file_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
        retry_text = await _ocr_image_file(file_path)
        if retry_text:
            retry_fields = _parse_fields(retry_text)
            retry_confidence = _compute_confidence(retry_fields)
            if retry_confidence > confidence:
                fields = retry_fields
                confidence = retry_confidence
                raw_text = retry_text
                pages = [retry_text]

    structured_data = _build_structured_data(fields, raw_text)
    return {
        **fields,
        "confidence": confidence,
        "raw_text": raw_text[:10000] if raw_text else "",
        "pages": pages,
        "page_count": len(pages),
        "structured_data": structured_data,
        "needs_review": confidence < 0.8,
    }
