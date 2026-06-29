import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TransactionType(str, enum.Enum):
    REVENUE = "revenue"
    EXPENSE = "expense"


class RevenueCategory(str, enum.Enum):
    BIRD_SALES = "bird_sales"
    EGG_SALES = "egg_sales"
    OTHER_INCOME = "other_income"


class ExpenseCategory(str, enum.Enum):
    FEED = "feed"
    MEDICINES = "medicines"
    VACCINES = "vaccines"
    LABOR = "labor"
    ELECTRICITY = "electricity"
    TRANSPORT = "transport"
    MISCELLANEOUS = "miscellaneous"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType))
    revenue_category: Mapped[RevenueCategory | None] = mapped_column(Enum(RevenueCategory), nullable=True)
    expense_category: Mapped[ExpenseCategory | None] = mapped_column(Enum(ExpenseCategory), nullable=True)
    amount: Mapped[float] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    transaction_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="transactions")
