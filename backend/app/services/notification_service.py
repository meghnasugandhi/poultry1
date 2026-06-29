from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import InventoryCategory, InventoryItem
from app.models.notification import Notification, NotificationType
from app.models.user import User


async def sync_alerts(db: AsyncSession, user: User) -> list[Notification]:
    """Create notifications for low stock and expiring items."""
    today = date.today()
    created: list[Notification] = []

    result = await db.execute(
        select(InventoryItem).where(InventoryItem.user_id == user.id)
    )
    items = result.scalars().all()

    type_map = {
        InventoryCategory.FEED: NotificationType.LOW_FEED,
        InventoryCategory.MEDICINE: NotificationType.LOW_MEDICINE,
        InventoryCategory.VACCINE: NotificationType.LOW_VACCINE,
    }

    for item in items:
        if item.quantity <= item.reorder_level:
            ntype = type_map[item.category]
            title = f"Low {item.category.value} stock"
            message = f"{item.product_name} is low: {item.quantity} {item.unit} remaining."
            if not await _alert_exists(db, user.id, ntype, message):
                n = Notification(user_id=user.id, notification_type=ntype, title=title, message=message)
                db.add(n)
                created.append(n)

        if item.expiry_date and item.expiry_date <= today + timedelta(days=30):
            ntype = (
                NotificationType.MEDICINE_EXPIRY
                if item.category == InventoryCategory.MEDICINE
                else NotificationType.VACCINE_EXPIRY
            )
            title = f"{item.category.value.title()} expiring soon"
            message = f"{item.product_name} expires on {item.expiry_date}."
            if not await _alert_exists(db, user.id, ntype, message):
                n = Notification(user_id=user.id, notification_type=ntype, title=title, message=message)
                db.add(n)
                created.append(n)

    if created:
        await db.flush()
    return created


async def _alert_exists(db: AsyncSession, user_id: int, ntype: NotificationType, message: str) -> bool:
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.notification_type == ntype,
            Notification.message == message,
            Notification.is_read == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none() is not None
