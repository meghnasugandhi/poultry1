import logging
from datetime import date, timedelta
from typing import Any

from app.core.config import settings
from app.schemas.assistant import ExportFormat, ReportType
from app.services.report_service import generate_report
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession


class ReportToolService:
    def __init__(self, db: AsyncSession, user: User, logger: logging.Logger | None = None):
        self.db = db
        self.user = user
        self.logger = logger or logging.getLogger("poultry.mcp.reports")

    async def daily_report(self) -> dict[str, Any]:
        return {"report_type": "daily", "status": "generated", "path": await self._export(ReportType.INVENTORY)}

    async def weekly_report(self) -> dict[str, Any]:
        return {"report_type": "weekly", "status": "generated", "path": await self._export(ReportType.PROFIT_LOSS)}

    async def monthly_report(self) -> dict[str, Any]:
        return {"report_type": "monthly", "status": "generated", "path": await self._export(ReportType.PROFIT_LOSS)}

    async def yearly_report(self) -> dict[str, Any]:
        return {"report_type": "yearly", "status": "generated", "path": await self._export(ReportType.PROFIT_LOSS)}

    async def export_pdf(self, report_type: str) -> dict[str, Any]:
        return {"report_type": report_type, "status": "generated", "path": await self._export(ReportType(report_type), ExportFormat.PDF)}

    async def export_excel(self, report_type: str) -> dict[str, Any]:
        return {"report_type": report_type, "status": "generated", "path": await self._export(ReportType(report_type), ExportFormat.EXCEL)}

    async def _export(self, report_type: ReportType, export_format: ExportFormat = ExportFormat.PDF) -> str:
        path = await generate_report(user=self.user, report_type=report_type, export_format=export_format, db=self.db)
        self.logger.info("reports.export", extra={"path": path, "report_type": report_type.value, "format": export_format.value})
        return path
