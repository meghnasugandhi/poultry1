from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel


class DocumentType(str, Enum):
    FEED_BILL = "feed_bill"
    MEDICINE_BILL = "medicine_bill"
    VACCINE_BILL = "vaccine_bill"
    SALES_INVOICE = "sales_invoice"
    PURCHASE_RECEIPT = "purchase_receipt"
    VACCINATION_REPORT = "vaccination_report"
    LAB_REPORT = "lab_report"


class DocumentResponse(BaseModel):
    id: int
    document_type: DocumentType
    file_path: str
    original_filename: str
    company_name: str | None
    product_name: str | None
    quantity: float | None
    number_of_bags: int | None
    cost: float | None
    invoice_date: date | None
    invoice_number: str | None
    supplier_name: str | None
    ocr_confidence: float | None
    needs_clarification: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentClarification(BaseModel):
    company_name: str | None = None
    product_name: str | None = None
    quantity: float | None = None
    number_of_bags: int | None = None
    cost: float | None = None
    invoice_date: date | None = None
    invoice_number: str | None = None
    supplier_name: str | None = None
