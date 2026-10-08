"""Unit tests for operational health endpoints (/health, /health/live, /health/ready)."""
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoints() -> None:
    app = create_app()
    client = TestClient(app)

    # 1. Base /health
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

    # 2. Liveness probe /health/live
    res_live = client.get("/health/live")
    assert res_live.status_code == 200
    assert res_live.json() == {"status": "live"}


def test_health_ready_connected() -> None:
    app = create_app()
    # Mock engine connection to succeed
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    app.state.engine = mock_engine

    client = TestClient(app)
    res_ready = client.get("/health/ready")
    assert res_ready.status_code == 200
    data = res_ready.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"


def test_health_ready_disconnected() -> None:
    app = create_app()
    # Mock engine connection failure (e.g. database down)
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = ConnectionRefusedError("Database unreachable")
    app.state.engine = mock_engine

    client = TestClient(app)
    res_ready = client.get("/health/ready")
    assert res_ready.status_code == 503
    data = res_ready.json()
    assert data["status"] == "unavailable"
    assert data["database"] == "disconnected"
