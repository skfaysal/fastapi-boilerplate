"""Structured JSON logging with per-request correlation IDs."""
import json
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Callable

from fastapi import Request, Response

# Stored in context so every log record within the same request carries the ID.
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get(""),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def setup_logging(level: str = "INFO") -> None:
    """Replace root handler with a JSON formatter. Call once at startup."""
    handler = logging.StreamHandler()
    handler.setFormatter(_JSONFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # Quiet noisy third-party loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


_access_log = logging.getLogger("access")


async def correlation_id_middleware(request: Request, call_next: Callable) -> Response:
    """
    Reads X-Request-ID from incoming headers (or generates a UUID),
    stores it in a ContextVar so all log calls within this request include it,
    and echoes it back in the response header.
    """
    cid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = correlation_id_var.set(cid)

    start = time.perf_counter()
    try:
        response: Response = await call_next(request)
    finally:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        _access_log.info(
            "%s %s → %s (%.2f ms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        correlation_id_var.reset(token)

    response.headers["X-Request-ID"] = cid
    return response
