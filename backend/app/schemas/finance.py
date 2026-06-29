from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    REVENUE = "revenue"
    EXPENSE = "expense"


class RevenueCategory(str, Enum):
    BIRD_SALES = "bird_sales"
    EGG_SALES = "egg_sales"
    OTHER_INCOME = "other_income"


class ExpenseCategory(str, Enum):
    FEED = "feed"
    MEDICINES = "medicines"
    VACCINES = "vaccines"
    LABOR = "labor"
    ELECTRICITY = "electricity"
    TRANSPORT = "transport"
    MISCELLANEOUS = "miscellaneous"


class TransactionCreate(BaseModel):
    transaction_type: TransactionType
    revenue_category: RevenueCategory | None = None
    expense_category: ExpenseCategory | None = None
    amount: float = Field(gt=0)
    description: str | None = None
    transaction_date: date | None = None


class TransactionResponse(BaseModel):
    id: int
    transaction_type: TransactionType
    revenue_category: RevenueCategory | None
    expense_category: ExpenseCategory | None
    amount: float
    description: str | None
    transaction_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class FinancialSummary(BaseModel):
    monthly_revenue: float
    monthly_expenses: float
    profit_loss: float
    revenue_breakdown: dict[str, float]
    expense_breakdown: dict[str, float]
