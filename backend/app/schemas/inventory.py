from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class InventoryCategory(str, Enum):
    FEED = "feed"
    MEDICINE = "medicine"
    VACCINE = "vaccine"


class InventoryCreate(BaseModel):
    category: InventoryCategory
    product_name: str
    quantity: float = Field(ge=0)
    unit: str = "kg"
    number_of_bags: int | None = None
    reorder_level: float = 10
    expiry_date: date | None = None
    supplier_name: str | None = None
    cost_per_unit: float | None = None


class InventoryUpdate(BaseModel):
    product_name: str | None = None
    quantity: float | None = Field(default=None, ge=0)
    unit: str | None = None
    number_of_bags: int | None = None
    reorder_level: float | None = None
    expiry_date: date | None = None
    supplier_name: str | None = None
    cost_per_unit: float | None = None


class InventoryResponse(BaseModel):
    id: int
    category: InventoryCategory
    product_name: str
    quantity: float
    unit: str
    number_of_bags: int | None
    reorder_level: float
    expiry_date: date | None
    supplier_name: str | None
    cost_per_unit: float | None
    is_low_stock: bool = False
    is_expiring_soon: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
