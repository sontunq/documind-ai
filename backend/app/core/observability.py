"""Structured logging, correlation ID propagation, and observability helpers."""
from collections.abc import Callable
from contextvars import ContextVar
from datetime import UTC, datetime
import json
import logging
import re
import sys
import time
from typing import Any
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable tracking correlation ID across async tasks and processing threads
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")

CORRELATION_HEADER = "X-Correlation-ID"
REQUEST_HEADER = "X-Request-ID"

SENSITIVE_PATTERNS = [
    re.compile(r"(password=)[^&;\s]+", re.IGNORECASE),
    re.compile(r"(secret=)[^&;\s]+", re.IGNORECASE),
    re.compile(r"(token=)[^&;\s]+", re.IGNORECASE),
    re.compile(r"(://[^:]+:)[^@]+(@)", re.IGNORECASE),  # URI passwords
]


def redact_sensitive_text(text: str) -> str:
    """Mask credentials, passwords, and tokens from log strings."""
    redacted = text
    for pattern in SENSITIVE_PATTERNS:
        if "://" in pattern.pattern:
            redacted = pattern.sub(r"\1***\2", redacted)
        else:
            redacted = pattern.sub(r"\1***", redacted)
    return redacted


def get_correlation_id() -> str:
    """Return the active correlation ID or empty string."""
    return correlation_id_ctx.get()


class JSONLogFormatter(logging.Formatter):
    """Format logs as structured JSON with correlation ID and UTC timestamp."""

    def format(self, record: logging.LogRecord) -> str:
        cid = getattr(record, "correlation_id", None) or get_correlation_id()
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_sensitive_text(record.getMessage()),
            "correlation_id": cid or None,
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Assign or propagate X-Correlation-ID / X-Request-ID across HTTP lifecycle."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        # Extract existing or generate new correlation ID
        incoming_id = (
            request.headers.get(CORRELATION_HEADER)
            or request.headers.get(REQUEST_HEADER)
            or ""
        ).strip()

        # Sanitize to alphanumeric + dashes, or generate UUID4
        if incoming_id and re.match(r"^[A-Za-z0-9\-_]{1,64}$", incoming_id):
            cid = incoming_id
        else:
            cid = str(uuid4())

        token = correlation_id_ctx.set(cid)
        start_time = time.perf_counter()

        try:
            response: Response = await call_next(request)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            # Attach tracing headers to response
            response.headers[CORRELATION_HEADER] = cid
            response.headers[REQUEST_HEADER] = cid
            response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
            return response
        finally:
            correlation_id_ctx.reset(token)


def setup_structured_logging(level: int = logging.INFO) -> None:
    """Configure root handler with JSON structured formatting."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers on reload
    for handler in list(root_logger.handlers):
        if isinstance(handler.formatter, JSONLogFormatter):
            return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONLogFormatter())
    root_logger.handlers = [handler]
