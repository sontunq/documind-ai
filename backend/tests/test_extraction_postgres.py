"""Real PostgreSQL checks for Phase 5 extraction persistence and roundtrips."""
from uuid import UUID

from alembic import command
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.infrastructure.db.models import ProcessingRunRow
from app.main import create_app
from classification_fakes import FakeClassifier
from conftest import make_image
from extraction_fakes import FakeFieldExtractor
from ocr_fakes import FakeOCRProvider, TEST_SPEC
from test_postgres import database
from test_processing_postgres import wait_for_status

pytestmark = pytest.mark.postgres


def test_extraction_migration_and_postgres_roundtrip(database, tmp_path):
    engine, config, url = database

    # 1. Verify migration upgrade/downgrade/re-upgrade
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "0003_classification")
        command.upgrade(config, "head")

    settings = Settings(_env_file=None, database_url=url, document_storage_dir=tmp_path / "uploads")
    app = create_app(settings)
    app.state.sessions = sessionmaker(engine, expire_on_commit=False)
    app.state.ocr_provider = FakeOCRProvider(app.state.storage)
    app.state.classifier = FakeClassifier({"invoice": 0.8, "contract": 0.1, "form": 0.1})
    extractor = FakeFieldExtractor()
    app.state.extractor = extractor
    app.state.pipeline_spec = TEST_SPEC

    with TestClient(app) as client:
        uploaded = client.post("/api/v1/documents", files={"file": ("synthetic.png", make_image())})
        assert uploaded.status_code == 201
        doc_id = uploaded.json()["id"]
        base = f"/api/v1/documents/{doc_id}"

        res = wait_for_status(client, base, "COMPLETED")
        curr_run = res["current_run"]
        assert curr_run["status"] == "COMPLETED"
        assert curr_run["extraction"] is not None
        ext = curr_run["extraction"]
        assert ext["document_type"] == "invoice"
        assert ext["invoice"]["invoice_number"]["value"] == "INV-100"
        assert ext["created_at"].endswith("Z")

        # Directly query PostgreSQL ProcessingRunRow to ensure persistence is real
        with sessionmaker(engine)() as session:
            row = session.scalar(select(ProcessingRunRow).where(ProcessingRunRow.id == UUID(curr_run["id"])))
            assert row is not None
            assert row.extraction is not None
            assert row.extraction["invoice"]["invoice_number"]["value"] == "INV-100"
            assert row.extraction_seconds is not None
            assert row.extraction_seconds >= 0

        # Reprocessing with failure keeps previous run's extraction current
        extractor.fail = True
        client.post(base + "/process?reprocess=true")
        failed = wait_for_status(client, base, "FAILED")
        assert failed["current_run"]["extraction"]["invoice"]["invoice_number"]["value"] == "INV-100"
        assert failed["latest_run"]["extraction"] is None
        assert failed["latest_run"]["error_code"] == "EXTRACTION_FAILED"
