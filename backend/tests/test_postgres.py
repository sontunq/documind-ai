"""Real PostgreSQL checks. Each test owns an isolated, randomly named schema."""
from pathlib import Path
import os
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.infrastructure.db.models import Base
from app.main import create_app

pytestmark = pytest.mark.postgres


@pytest.fixture
def database():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to run real PostgreSQL migration/persistence tests")
    assert make_url(url).drivername == "postgresql+psycopg"
    schema = "test_documind_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    # Prove UTC API timestamps do not depend on the database session's timezone.
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema} -cTimeZone=Asia/Bangkok"})
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        yield engine, config, url
    finally:
        engine.dispose()
        # Only this fixture's freshly generated schema is ever removed.
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_migration_schema_and_roundtrip(database):
    engine, config, _ = database
    with engine.connect() as connection:
        assert set(inspect(connection).get_table_names()) == {"documents", "processing_runs", "reviews", "alembic_version"}
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "base")
        assert "documents" not in inspect(connection).get_table_names()
        command.upgrade(config, "head")
        assert "documents" in inspect(connection).get_table_names()


def test_persistence_across_app_restart(database, tmp_path, pdf_bytes):
    engine, _, url = database
    settings = Settings(_env_file=None, database_url=url, document_storage_dir=tmp_path / "uploads", ocr_auto_process=False)
    first = create_app(settings)
    first.state.sessions = sessionmaker(engine, expire_on_commit=False)
    with TestClient(first) as client:
        response = client.post("/api/v1/documents", files={"file": ("synthetic.pdf", pdf_bytes)})
        assert response.status_code == 201, response.text
        metadata = response.json()
    engine.dispose()  # New connections and a new application; no in-memory repository.
    second = create_app(settings)
    second.state.sessions = sessionmaker(engine, expire_on_commit=False)
    with TestClient(second) as client:
        assert client.get(f"/api/v1/documents/{metadata['id']}").json() == metadata
        assert client.get("/api/v1/documents").json() == [metadata]
    assert len(list(settings.document_storage_dir.iterdir())) == 1


def test_failed_database_insert_cleans_binary(database, tmp_path, pdf_bytes):
    engine, _, url = database
    # Deliberately reject the insert through a constraint in this isolated schema.
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE documents ADD CONSTRAINT reject_test CHECK (size_bytes < 1)"))
    settings = Settings(_env_file=None, database_url=url, document_storage_dir=tmp_path / "uploads", ocr_auto_process=False)
    app = create_app(settings)
    app.state.sessions = sessionmaker(engine, expire_on_commit=False)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/v1/documents", files={"file": ("synthetic.pdf", pdf_bytes)})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "PERSISTENCE_UNAVAILABLE"
        assert client.get("/api/v1/documents").json() == []
    assert list(settings.document_storage_dir.iterdir()) == []
