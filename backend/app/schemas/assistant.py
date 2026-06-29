from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class ReportType(str, Enum):
    FEED_EXPENSE = "feed_expense"
    MEDICINE_EXPENSE = "medicine_expense"
    INVENTORY = "inventory"
    PROFIT_LOSS = "profit_loss"
    VACCINATION = "vaccination"
    SALES = "sales"
    BATCH = "batch"


class ExportFormat(str, Enum):
    PDF = "pdf"
    EXCEL = "excel"


class ReportRequest(BaseModel):
    report_type: ReportType
    export_format: ExportFormat = ExportFormat.PDF
    start_date: datetime | None = None
    end_date: datetime | None = None
    # Optional reviewed/corrected table from the preview screen.
    columns: list[str] | None = None
    rows: list[list[str]] | None = None


class ReportPreviewRequest(BaseModel):
    report_type: ReportType


class CalculatorRequest(BaseModel):
    calculation_type: str
    inputs: dict[str, float]


class CalculatorResponse(BaseModel):
    calculation_type: str
    formula: str
    steps: list[str]
    result: float
    explanation: str


class ChatRequest(BaseModel):
    message: str
    session_id: int | None = None
    language: str = "en"


class ChatResponse(BaseModel):
    session_id: int
    message: str
    suggested_questions: list[str] = []
    voice_enabled: bool = False
