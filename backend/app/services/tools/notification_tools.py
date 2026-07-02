import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType
from app.models.user import User


class NotificationToolService:
    def __init__(self, db: AsyncSession, user: User, logger: logging.Logger | None = None):
        self.db = db
        self.user = user
        self.logger = logger or logging.getLogger("poultry.mcp.notifications")

    async def email(self, recipient: str, subject: str, body: str) -> dict[str, Any]:
        self.logger.info("notification.email", extra={"recipient": recipient, "subject": subject})
        return {"channel": "email", "recipient": recipient, "subject": subject, "body": body, "status": "queued"}

    async def sms(self, recipient: str, body: str) -> dict[str, Any]:
        self.logger.info("notification.sms", extra={"recipient": recipient})
        return {"channel": "sms", "recipient": recipient, "body": body, "status": "queued"}

    async def whatsapp(self, recipient: str, body: str) -> dict[str, Any]:
        self.logger.info("notification.whatsapp", extra={"recipient": recipient})
        return {"channel": "whatsapp", "recipient": recipient, "body": body, "status": "queued"}

    async def push_notification(self, title: str, body: str) -> dict[str, Any]:
        self.logger.info("notification.push", extra={"title": title})
        return {"channel": "push", "title": title, "body": body, "status": "queued"}
