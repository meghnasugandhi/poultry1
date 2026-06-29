import os
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import ExpenseCategory, Transaction, TransactionType
from app.models.inventory import InventoryItem
from app.models.user import User
from app.schemas.assistant import ExportFormat, ReportType


async def _fetch_report_rows(
    db: AsyncSession, user: User, report_type: ReportType
) -> list[list[str]]:
    rows: list[list[str]] = []

    if report_type in (ReportType.FEED_EXPENSE, ReportType.MEDICINE_EXPENSE):
        cat = ExpenseCategory.FEED if report_type == ReportType.FEED_EXPENSE else ExpenseCategory.MEDICINES
        result = await db.execute(
            select(Transaction).where(
                Transaction.user_id == user.id,
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.expense_category == cat,
            ).order_by(Transaction.transaction_date.desc())
        )
        rows.append(["Date", "Amount", "Description"])
        for t in result.scalars().all():
            rows.append([str(t.transaction_date), f"₹{t.amount:,.2f}", t.description or ""])

    elif report_type == ReportType.INVENTORY:
        result = await db.execute(
            select(InventoryItem).where(InventoryItem.user_id == user.id)
        )
        rows.append(["Product", "Category", "Quantity", "Unit", "Reorder Level"])
        for i in result.scalars().all():
            rows.append([i.product_name, i.category.value, str(i.quantity), i.unit, str(i.reorder_level)])

    elif report_type == ReportType.PROFIT_LOSS:
        rev = float(
            (await db.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.user_id == user.id,
                    Transaction.transaction_type == TransactionType.REVENUE,
                )
            )).scalar()
            or 0
        )
        exp = float(
            (await db.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.user_id == user.id,
                    Transaction.transaction_type == TransactionType.EXPENSE,
                )
            )).scalar()
            or 0
        )
        rows = [
            ["Metric", "Amount"],
            ["Total Revenue", f"₹{rev:,.2f}"],
            ["Total Expenses", f"₹{exp:,.2f}"],
            ["Profit/Loss", f"₹{rev - exp:,.2f}"],
        ]

    elif report_type == ReportType.SALES:
        result = await db.execute(
            select(Transaction).where(
                Transaction.user_id == user.id,
                Transaction.transaction_type == TransactionType.REVENUE,
            ).order_by(Transaction.transaction_date.desc())
        )
        rows.append(["Date", "Category", "Amount", "Description"])
        for t in result.scalars().all():
            rows.append([
                str(t.transaction_date),
                t.revenue_category.value if t.revenue_category else "",
                f"₹{t.amount:,.2f}",
                t.description or "",
            ])

    else:
        rows = [["Info", "Value"], ["Report", report_type.value], ["Status", "No detailed data yet"]]

    return rows


async def build_report_preview(
    db: AsyncSession, user: User, report_type: ReportType
) -> dict:
    """Return structured report data for on-screen review before download."""
    rows = await _fetch_report_rows(db, user, report_type)
    columns = rows[0] if rows else []
    data = rows[1:] if len(rows) > 1 else []
    return {
        "report_type": report_type.value,
        "title": f"{report_type.value.replace('_', ' ').title()} Report",
        "farm_name": user.farm_name,
        "owner_name": user.owner_name,
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "columns": columns,
        "rows": data,
    }


async def generate_report(
    user: User,
    report_type: ReportType,
    export_format: ExportFormat,
    db: AsyncSession,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    rows: list[list[str]] | None = None,
) -> str:
    os.makedirs("reports", exist_ok=True)
    ext = "pdf" if export_format == ExportFormat.PDF else "xlsx"
    filename = f"reports/{report_type.value}_{uuid.uuid4().hex[:8]}.{ext}"
    if rows is None:
        rows = await _fetch_report_rows(db, user, report_type)
    title = report_type.value.replace("_", " ").title()
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    if export_format == ExportFormat.PDF:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(filename, pagesize=A4)
        y = 800
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, f"{title} Report")
        y -= 25
        c.setFont("Helvetica", 11)
        c.drawString(50, y, f"Farm: {user.farm_name} | Owner: {user.owner_name}")
        y -= 18
        c.drawString(50, y, f"Generated: {generated}")
        y -= 30
        c.setFont("Helvetica", 10)
        for row in rows:
            line = " | ".join(str(cell) for cell in row)
            c.drawString(50, y, line[:110])
            y -= 16
            if y < 60:
                c.showPage()
                y = 800
        c.save()
    else:
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = report_type.value[:31]
        ws.append([title])
        ws.append(["Farm", user.farm_name])
        ws.append(["Owner", user.owner_name])
        ws.append(["Generated", generated])
        ws.append([])
        for row in rows:
            ws.append(row)
        wb.save(filename)

    return filename
