import re

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.inventory import InventoryCategory, InventoryItem, StockMovement
from app.models.user import User
from app.schemas.inventory import InventoryCreate, InventoryResponse, InventoryUpdate

router = APIRouter(prefix="/inventory", tags=["Inventory Management"])


class VoiceEntryRequest(BaseModel):
    text: str


def _enrich_item(item: InventoryItem) -> InventoryResponse:
    today = date.today()
    is_low = item.quantity <= item.reorder_level
    is_expiring = item.expiry_date is not None and item.expiry_date <= today + timedelta(days=30)
    return InventoryResponse(
        id=item.id,
        category=item.category,
        product_name=item.product_name,
        quantity=item.quantity,
        unit=item.unit,
        number_of_bags=item.number_of_bags,
        reorder_level=item.reorder_level,
        expiry_date=item.expiry_date,
        supplier_name=item.supplier_name,
        cost_per_unit=item.cost_per_unit,
        is_low_stock=is_low,
        is_expiring_soon=is_expiring,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post("/", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
async def add_stock(
    data: InventoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = InventoryItem(user_id=current_user.id, **data.model_dump())
    db.add(item)
    await db.flush()

    movement = StockMovement(item_id=item.id, change_amount=data.quantity, reason="Initial stock")
    db.add(movement)
    await db.refresh(item)
    return _enrich_item(item)


@router.get("/", response_model=list[InventoryResponse])
async def list_stock(
    category: InventoryCategory | None = None,
    low_stock_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(InventoryItem).where(InventoryItem.user_id == current_user.id)
    if category:
        query = query.where(InventoryItem.category == category)
    result = await db.execute(query.order_by(InventoryItem.product_name))
    items = result.scalars().all()
    enriched = [_enrich_item(i) for i in items]
    if low_stock_only:
        enriched = [i for i in enriched if i.is_low_stock]
    return enriched


@router.get("/{item_id}", response_model=InventoryResponse)
async def get_stock(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == item_id, InventoryItem.user_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return _enrich_item(item)


@router.put("/{item_id}", response_model=InventoryResponse)
async def update_stock(
    item_id: int,
    data: InventoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == item_id, InventoryItem.user_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    old_qty = item.quantity
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    if data.quantity is not None and data.quantity != old_qty:
        movement = StockMovement(
            item_id=item.id,
            change_amount=data.quantity - old_qty,
            reason="Stock update",
        )
        db.add(movement)

    await db.flush()
    await db.refresh(item)
    return _enrich_item(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stock(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == item_id, InventoryItem.user_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)


@router.get("/{item_id}/history")
async def stock_history(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == item_id, InventoryItem.user_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    movements = await db.execute(
        select(StockMovement)
        .where(StockMovement.item_id == item_id)
        .order_by(StockMovement.created_at.desc())
    )
    return [
        {
            "id": m.id,
            "change_amount": m.change_amount,
            "reason": m.reason,
            "notes": m.notes,
            "created_at": m.created_at,
        }
        for m in movements.scalars().all()
    ]


@router.post("/voice-entry", response_model=InventoryResponse)
async def voice_entry(
    body: VoiceEntryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    text = body.text.lower()
    add_match = re.search(
        r"add\s+(\d+(?:\.\d+)?)\s*(kg|bags|units|doses)?\s+(?:of\s+)?(.+)",
        text,
    )
    if not add_match:
        raise HTTPException(status_code=400, detail="Could not parse inventory command. Try: 'Add 50 kg broiler feed'")

    product = add_match.group(3).strip().title()
    category = "feed"
    for cat in ("feed", "medicine", "vaccine"):
        if cat in product.lower():
            category = cat
            product = re.sub(rf"\b{cat}\b", "", product, flags=re.I).strip().title() or product

    data = InventoryCreate(
        category=InventoryCategory(category),
        product_name=product,
        quantity=float(add_match.group(1)),
        unit=add_match.group(2) or "kg",
    )
    item = InventoryItem(user_id=current_user.id, **data.model_dump())
    db.add(item)
    await db.flush()
    db.add(StockMovement(item_id=item.id, change_amount=data.quantity, reason="Voice entry"))
    await db.refresh(item)
    return _enrich_item(item)
