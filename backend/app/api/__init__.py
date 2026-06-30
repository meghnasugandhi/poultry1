from fastapi import APIRouter

from app.api import assistant, auth, calculator, dashboard, documents, finance, inventory, notifications, reports, translations, voice, suggested_transactions
from . import ocr

api_router = APIRouter()
api_router.include_router(ocr.router)
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(inventory.router)
api_router.include_router(documents.router)
api_router.include_router(finance.router)
api_router.include_router(calculator.router)
api_router.include_router(reports.router)
api_router.include_router(assistant.router)
api_router.include_router(suggested_transactions.router)
api_router.include_router(notifications.router)
api_router.include_router(voice.router)
api_router.include_router(translations.router)
