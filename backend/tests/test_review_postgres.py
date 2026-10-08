"""Real PostgreSQL checks for Phase 6 review persistence, concurrency, and audit history."""
from uuid import UUID

from alembic import command
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.infrastructure.db.models import DocumentRow, ProcessingRunRow, ReviewRow
from app.main import create_app
from classification_fakes import FakeClassifier
from conftest import make_image
from extraction_fakes import FakeFieldExtractor
from ocr_fakes import FakeOCRProvider, TEST_SPEC
from test_postgres import database
from test_processing_postgres import wait_for_status

pytestmark = pytest.mark.postgres


def test_review_migration_and_postgres_roundtrip(database, tmp_path):
    engine, config, url = database

    # 1. Verify migration upgrade/downgrade/re-upgrade
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "0004_extraction")
        command.upgrade(config, "head")

    settings = Settings(_env_file=None, database_url=url, document_storage_dir=tmp_path / "uploads")
    app = create_app(settings)
    app.state.sessions = sessionmaker(engine, expire_on_commit=False)
    app.state.ocr_provider = FakeOCRProvider(app.state.storage)
    app.state.classifier = FakeClassifier({"invoice": 0.8, "contract": 0.1, "form": 0.1})
    app.state.extractor = FakeFieldExtractor()
    app.state.pipeline_spec = TEST_SPEC

    with TestClient(app) as client:
        # Upload and process
        uploaded = client.post("/api/v1/documents", files={"file": ("invoice_sample.png", make_image())})
        assert uploaded.status_code == 201
        doc_id = uploaded.json()["id"]
        base = f"/api/v1/documents/{doc_id}"

        res = wait_for_status(client, base, "COMPLETED")
        curr_run = res["current_run"]
        raw_extraction = curr_run["extraction"]
        assert raw_extraction is not None

        # Check initial document revision in PostgreSQL
        with sessionmaker(engine)() as session:
            doc_row = session.scalar(select(DocumentRow).where(DocumentRow.id == UUID(doc_id)))
            assert doc_row.revision == 1

        # Submit review: Correction of invoice_number
        review_payload = {
            "expected_revision": 1,
            "status": "CORRECTED",
            "reviewer_id": "auditor_1",
            "document_type": "invoice",
            "fields": [
                {
                    "field_name": "invoice_number",
                    "original_value": "INV-100",
                    "corrected_value": "INV-100-CORRECTED",
                    "original_confidence": 0.95,
                    "is_modified": True,
                }
            ],
            "notes": "Fixed suffix from invoice stamp",
        }
        submit_res = client.put(f"{base}/review", json=review_payload)
        assert submit_res.status_code == 200, submit_res.text
        review_data = submit_res.json()
        assert review_data["revision"] == 2
        assert review_data["status"] == "CORRECTED"

        # Verify PostgreSQL database rows
        with sessionmaker(engine)() as session:
            doc_row = session.scalar(select(DocumentRow).where(DocumentRow.id == UUID(doc_id)))
            assert doc_row.revision == 2
            assert doc_row.status == "COMPLETED"

            # Check reviews table
            review_row = session.scalar(select(ReviewRow).where(ReviewRow.document_id == UUID(doc_id)))
            assert review_row is not None
            assert review_row.revision == 2
            assert review_row.status == "CORRECTED"
            assert review_row.notes == "Fixed suffix from invoice stamp"
            assert len(review_row.fields) == 1
            assert review_row.fields[0]["corrected_value"] == "INV-100-CORRECTED"

            # CRITICAL RULE: Verify raw AI predictions in ProcessingRunRow were NOT mutated
            run_row = session.scalar(select(ProcessingRunRow).where(ProcessingRunRow.id == UUID(curr_run["id"])))
            assert run_row.extraction["invoice"]["invoice_number"]["value"] == "INV-100"

        # Stale revision conflict check on PostgreSQL
        conflict_res = client.put(f"{base}/review", json=review_payload)
        assert conflict_res.status_code == 409
        assert conflict_res.json()["error"]["code"] == "STALE_REVISION_CONFLICT"

        # Next review at revision 2 succeeds
        review_payload_2 = {
            "expected_revision": 2,
            "status": "APPROVED",
            "reviewer_id": "lead_reviewer",
        }
        submit_res_2 = client.put(f"{base}/review", json=review_payload_2)
        assert submit_res_2.status_code == 200
        assert submit_res_2.json()["revision"] == 3

        # List review history
        hist = client.get(f"{base}/reviews").json()
        assert len(hist) == 2
        assert hist[0]["revision"] == 3
        assert hist[1]["revision"] == 2
