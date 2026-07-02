"""Unified MCP tool registry with modular tool groups and backward-compatible aliases."""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.assistant import ExportFormat, ReportType
from app.services.calculator_service import CALCULATORS
from app.services.tools.dashboard_tools import DashboardToolService
from app.services.tools.finance_tools import FinanceToolService
from app.services.tools.inventory_tools import InventoryToolService
from app.services.tools.notification_tools import NotificationToolService
from app.services.tools.ocr_tools import OCRToolService
from app.services.tools.reports_tools import ReportToolService
from app.services.tools.search_tools import SearchToolService
from app.services.tools.voice_tools import VoiceToolService
from app.services.translation_service import get_ui_bundle, translate_text


class MCPRegistry:
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
        self.logger = logging.getLogger("poultry.mcp.registry")
        self.inventory_tools = InventoryToolService(db, user, self.logger)
        self.finance_tools = FinanceToolService(db, user, self.logger)
        self.report_tools = ReportToolService(db, user, self.logger)
        self.ocr_tools = OCRToolService(self.logger)
        self.dashboard_tools = DashboardToolService(db, user, self.logger)
        self.notification_tools = NotificationToolService(db, user, self.logger)
        self.voice_tools = VoiceToolService(self.logger)
        self.search_tools = SearchToolService(db, user, self.logger)

    def get_tool_catalog(self) -> dict[str, list[str]]:
        return {
            "inventory": [
                "add_stock",
                "remove_stock",
                "adjust_stock",
                "transfer_stock",
                "get_stock",
                "get_low_stock",
                "predict_stock_shortage",
            ],
            "finance": [
                "create_expense",
                "create_income",
                "supplier_summary",
                "cash_flow",
                "profit_loss",
                "monthly_finance",
            ],
            "reports": [
                "daily_report",
                "weekly_report",
                "monthly_report",
                "yearly_report",
                "export_pdf",
                "export_excel",
            ],
            "ocr": ["parse_bill", "verify_bill", "classify_document", "extract_items"],
            "dashboard": ["dashboard_summary", "analytics_summary", "farm_summary"],
            "notifications": ["email", "sms", "whatsapp", "push_notification"],
            "voice": ["speech_to_text", "text_to_speech", "language_detection"],
            "search": ["search_documents", "search_inventory", "search_finance", "search_reports"],
        }

    async def execute(self, tool: str, params: dict[str, Any] | None = None) -> Any:
        params = params or {}
        self.logger.info("mcp.execute", extra={"tool": tool, "params": params})
        handlers: dict[str, Any] = {
            "get_stock": self.inventory_tools.get_stock,
            "add_stock": self.inventory_tools.add_stock,
            "remove_stock": self.inventory_tools.remove_stock,
            "adjust_stock": self.inventory_tools.adjust_stock,
            "transfer_stock": self.inventory_tools.transfer_stock,
            "get_low_stock": self.inventory_tools.get_low_stock,
            "predict_stock_shortage": self.inventory_tools.predict_stock_shortage,
            "get_expiring": self.inventory_tools.get_low_stock,
            "search_documents": self.search_tools.search_documents,
            "search_inventory": self.search_tools.search_inventory,
            "search_finance": self.search_tools.search_finance,
            "search_reports": self.search_tools.search_reports,
            "parse_bill": self.ocr_tools.parse_bill,
            "verify_bill": self.ocr_tools.verify_bill,
            "classify_document": self.ocr_tools.classify_document,
            "extract_items": self.ocr_tools.extract_items,
            "create_expense": self.finance_tools.create_expense,
            "create_income": self.finance_tools.create_income,
            "supplier_summary": self.finance_tools.supplier_summary,
            "cash_flow": self.finance_tools.cash_flow,
            "profit_loss": self.finance_tools.profit_loss,
            "monthly_finance": self.finance_tools.monthly_finance,
            "daily_report": self.report_tools.daily_report,
            "weekly_report": self.report_tools.weekly_report,
            "monthly_report": self.report_tools.monthly_report,
            "yearly_report": self.report_tools.yearly_report,
            "export_pdf": self.report_tools.export_pdf,
            "export_excel": self.report_tools.export_excel,
            "dashboard_summary": self.dashboard_tools.dashboard_summary,
            "analytics_summary": self.dashboard_tools.analytics_summary,
            "farm_summary": self.dashboard_tools.farm_summary,
            "email": self.notification_tools.email,
            "sms": self.notification_tools.sms,
            "whatsapp": self.notification_tools.whatsapp,
            "push_notification": self.notification_tools.push_notification,
            "speech_to_text": self.voice_tools.speech_to_text,
            "text_to_speech": self.voice_tools.text_to_speech,
            "language_detection": self.voice_tools.language_detection,
            "get_expenses": self.finance_tools.get_expenses,
            "get_revenue": self.finance_tools.get_revenue,
            "get_profit_loss": self.finance_tools.get_profit_loss,
            "get_monthly_summary": self.finance_tools.get_monthly_summary,
            "generate_report": self.report_tools.export_pdf,
            "mcp_generate_report": self.report_tools.export_pdf,
            "calculate": self.calculate,
            "translate_text": self.mcp_translate,
            "translate_ui": self.mcp_translate_ui,
            "get_dashboard_stats": self.get_dashboard_stats,
            "get_user_profile": self.get_user_profile,
        }
        handler = handlers.get(tool)
        if not handler:
            raise ValueError(f"Unknown MCP tool: {tool}")
        return await handler(**params)

    async def calculate(self, calculation_type: str, inputs: dict[str, float]) -> dict[str, Any]:
        calc = CALCULATORS.get(calculation_type)
        if not calc:
            raise ValueError(f"Unknown calculation: {calculation_type}")
        result = calc["fn"](inputs)
        return {"formula": calc["formula"], **result}

    async def mcp_translate(self, text: str, target_language: str) -> str:
        return translate_text(text, target_language)

    async def mcp_translate_ui(self, target_language: str) -> dict[str, str]:
        return get_ui_bundle(target_language)

    async def get_dashboard_stats(self) -> dict[str, Any]:
        return await self.dashboard_tools.dashboard_summary()

    async def get_user_profile(self) -> dict[str, Any]:
        return {
            "owner_name": self.user.owner_name,
            "farm_name": self.user.farm_name,
            "email": self.user.email,
            "mobile": self.user.mobile_number,
            "language": self.user.preferred_language.value,
        }
