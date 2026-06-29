import os
import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.assistant import ExportFormat, ReportRequest
from app.services.report_service import generate_report

router = APIRouter(prefix="/reports", tags=["Report Generation"])


@router.post("/generate")
async def create_report(
    data: ReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    file_path = await generate_report(
        user=current_user,
        report_type=data.report_type,
        export_format=data.export_format,
        db=db,
        start_date=data.start_date,
        end_date=data.end_date,
    )
    media_type = (
        "application/pdf"
        if data.export_format == ExportFormat.PDF
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    basename = os.path.basename(file_path.replace("\\", "/"))
    return FileResponse(file_path, media_type=media_type, filename=basename)
