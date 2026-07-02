import json
import logging
from typing import Any


class StructuredLogger(logging.LoggerAdapter):
    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        extra = kwargs.pop("extra", {}) or {}
        if extra:
            return f"{msg} | {json.dumps(extra, default=str)}", kwargs
        return msg, kwargs


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(logging.getLogger(name), {})


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
