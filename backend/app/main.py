from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.logging import configure_logging
from app.models import *  # noqa: F401, F403 — register all models


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)

if os.path.isdir(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/health")
async def health():
    return {"status": "healthy", "app": settings.APP_NAME}
