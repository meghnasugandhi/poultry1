import re
from datetime import date, datetime


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
        r"(?:invoice|bill|inv)\s*(?:no|number|#)?\s*[:\-]?\s*([A-Z0-9\-/]+)",
        text,
        re.I,
    )
    if invoice_match:
        fields["invoice_number"] = invoice_match.group(1).strip()

    cost_match = re.search(
        r"(?:total|grand total|amount|net amount|cost|rs\.?|₹)\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)",
        text,
        re.I,
    )
    if cost_match:
        fields["cost"] = float(cost_match.group(1).replace(",", ""))

    qty_match = re.search(
        r"(?:qty|quantity|weight)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)\s*(?:kg|bags|units)?",
        text,
        re.I,
    )
    if qty_match:
        fields["quantity"] = float(qty_match.group(1).replace(",", ""))

    bags_match = re.search(r"(\d+)\s*bags?", text, re.I)
    if bags_match:
        fields["number_of_bags"] = int(bags_match.group(1))

    supplier_match = re.search(
        r"(?:supplier|vendor|from|sold by)\s*[:\-]?\s*([A-Za-z0-9 &.\-]+)",
        text,
        re.I,
    )
    if supplier_match:
        fields["supplier_name"] = supplier_match.group(1).strip()[:255]

    product_match = re.search(
        r"(?:product|item|description)\s*[:\-]?\s*([A-Za-z0-9 \-/]+)",
        text,
        re.I,
    )
    if product_match:
        fields["product_name"] = product_match.group(1).strip()[:255]

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if lines and not fields["company_name"]:
        fields["company_name"] = lines[0][:255]

    fields["invoice_date"] = _parse_date(text)
    return fields


def _compute_confidence(fields: dict) -> float:
    keys = ["company_name", "product_name", "quantity", "cost", "invoice_date", "invoice_number", "supplier_name"]
    filled = sum(1 for k in keys if fields.get(k) is not None)
    return round(filled / len(keys), 2)


async def process_document_ocr(file_path: str) -> dict:
    raw_text = _extract_text_from_file(file_path)
    fields = _parse_fields(raw_text)
    confidence = _compute_confidence(fields)
    return {
        **fields,
        "confidence": confidence,
        "raw_text": raw_text[:5000] if raw_text else "",
    }
