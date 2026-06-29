import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InventoryCategory(str, enum.Enum):
    FEED = "feed"
    MEDICINE = "medicine"
    VACCINE = "vaccine"


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[InventoryCategory] = mapped_column(Enum(InventoryCategory))
    product_name: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(50), default="kg")
    number_of_bags: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reorder_level: Mapped[float] = mapped_column(Float, default=10)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cost_per_unit: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="inventory_items")
    movements: Mapped[list["StockMovement"]] = relationship(back_populates="item")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id"))
    change_amount: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    item: Mapped["InventoryItem"] = relationship(back_populates="movements")
