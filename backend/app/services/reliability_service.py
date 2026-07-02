import asyncio
from typing import Any, Callable

from app.core.logging import get_logger

logger = get_logger("poultry.reliability")


class RetryPolicy:
    def __init__(self, max_attempts: int = 3, delay_seconds: float = 0.5) -> None:
        self.max_attempts = max_attempts
        self.delay_seconds = delay_seconds

    async def run(self, operation: Callable[[], Any], *, context: dict[str, Any] | None = None) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return await operation() if asyncio.iscoroutinefunction(operation) else operation()
            except Exception as exc:
                last_error = exc
                logger.warning("retry.failed", extra={"attempt": attempt, "error": str(exc), **(context or {})})
                if attempt >= self.max_attempts:
                    raise
                await asyncio.sleep(self.delay_seconds * attempt)
        if last_error is not None:
            raise last_error
        raise RuntimeError("Retry policy completed without running the operation")
