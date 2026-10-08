"""Unit tests for request correlation IDs and structured logging."""
import json
import logging
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.observability import (
    CORRELATION_HEADER,
    REQUEST_HEADER,
    CorrelationIdMiddleware,
    JSONLogFormatter,
    get_correlation_id,
    redact_sensitive_text,
)


def test_correlation_id_generated_automatically() -> None:
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/test")
    def endpoint() -> dict:
        return {"cid": get_correlation_id()}

    client = TestClient(app)
    res = client.get("/test")
    assert res.status_code == 200
    assert CORRELATION_HEADER in res.headers
    assert REQUEST_HEADER in res.headers

    cid_header = res.headers[CORRELATION_HEADER]
    # Verify it is a valid UUID
    parsed_uuid = UUID(cid_header)
    assert str(parsed_uuid) == cid_header

    # Verify context variable matched
    assert res.json()["cid"] == cid_header
    assert "X-Response-Time-Ms" in res.headers


def test_correlation_id_propagated_from_client() -> None:
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/test")
    def endpoint() -> dict:
        return {"cid": get_correlation_id()}

    client = TestClient(app)
    custom_cid = "client-trace-abc-123"
    res = client.get("/test", headers={CORRELATION_HEADER: custom_cid})
    assert res.status_code == 200
    assert res.headers[CORRELATION_HEADER] == custom_cid
    assert res.headers[REQUEST_HEADER] == custom_cid
    assert res.json()["cid"] == custom_cid


def test_redact_sensitive_text() -> None:
    raw1 = "postgresql+psycopg://postgres:super_secret_pw@127.0.0.1:5432/documind"
    redacted1 = redact_sensitive_text(raw1)
    assert "super_secret_pw" not in redacted1
    assert "postgres:***@" in redacted1

    raw2 = "Failed auth with password=my_secret_password"
    redacted2 = redact_sensitive_text(raw2)
    assert "my_secret_password" not in redacted2
    assert "password=***" in redacted2


def test_json_log_formatter() -> None:
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Processing document with token=abc123xyz",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    data = json.loads(formatted)
    assert data["level"] == "INFO"
    assert data["logger"] == "test_logger"
    assert "abc123xyz" not in data["message"]
    assert "token=***" in data["message"]
    assert "timestamp" in data
