import asyncio
from typing import Any

from app.core.logging import get_logger

logger = get_logger("poultry.background")


class BackgroundJobRunner:
    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[Any]] = set()

    def run(self, coro: Any) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def shutdown(self) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def run_ocr_job(self, file_path: str, callback: Any | None = None) -> None:
        from app.services.ocr_service import process_document_ocr

        result = await process_document_ocr(file_path)
        if callback:
            await callback(result)
