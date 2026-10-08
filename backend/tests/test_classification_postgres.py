"""Classification is persisted with its source run, independently of app memory."""
from uuid import UUID

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.infrastructure.db.models import ProcessingRunRow
from app.main import create_app
from classification_fakes import FakeClassifier
from conftest import make_image
from ocr_fakes import FakeOCRProvider, TEST_SPEC
from test_postgres import database
from test_processing_postgres import wait_for_status

pytestmark = pytest.mark.postgres


@pytest.mark.parametrize("low", [False, True])
def test_classification_roundtrip_failure_reprocess_and_restart(database, tmp_path, low):
    engine, _, url = database
    settings = Settings(_env_file=None, database_url=url, document_storage_dir=tmp_path / "uploads")
    app = create_app(settings)
    app.state.sessions = sessionmaker(engine, expire_on_commit=False)
    app.state.ocr_provider = FakeOCRProvider(app.state.storage)
    classifier = FakeClassifier({"invoice": .4, "contract": .35, "form": .25} if low else None)
    app.state.classifier = classifier
    app.state.pipeline_spec = TEST_SPEC
    with TestClient(app) as client:
        uploaded = client.post("/api/v1/documents", files={"file": ("synthetic.png", make_image())})
        assert uploaded.status_code == 201
        base = f"/api/v1/documents/{uploaded.json()['id']}"
        first = wait_for_status(client, base, "NEEDS_REVIEW" if low else "COMPLETED")
        first_run = first["current_run"]
        prediction = first_run["classification"]
        assert prediction["needs_review"] == low
        assert prediction["scores"] == classifier.scores
        assert prediction["created_at"].endswith("Z")
        assert client.post(base + "/process").json()["id"] == first_run["id"]
        assert classifier.calls == 1
        # A failure after OCR preserves both that OCR and the prior current result.
        classifier.fail = True
        assert client.post(base + "/process?reprocess=true").status_code == 202
        failed = wait_for_status(client, base, "FAILED")
        assert failed["current_run"]["classification"] == prediction
        assert failed["latest_run"]["result"] is not None
        assert failed["latest_run"]["classification"] is None
        assert failed["latest_run"]["error_code"] == "CLASSIFICATION_FAILED"
        assert "SECRET" not in str(failed)
        classifier.fail = False
        classifier.scores = {"invoice": .1, "contract": .1, "form": .8}
        client.post(base + "/process")
        latest = wait_for_status(client, base, "COMPLETED")
        assert latest["current_run"]["classification"]["predicted_type"] == "form"
    engine.dispose()
    fresh = create_app(settings)
    fresh.state.sessions = sessionmaker(engine, expire_on_commit=False)
    with TestClient(fresh) as client:
        assert client.get(base + "/results").json() == latest
    with Session(engine) as session:
        rows = list(session.scalars(select(ProcessingRunRow).where(
            ProcessingRunRow.document_id == UUID(uploaded.json()["id"]))))
        assert len(rows) == 3 and sum(r.is_current for r in rows) == 1
        assert all(r.result for r in rows)
        assert sum(r.classification is not None for r in rows) == 2
        original = session.get(ProcessingRunRow, UUID(first_run["id"]))
        assert original.classification["scores"] == prediction["scores"]
        assert original.classification["run_id"] == original.result["run_id"]


def test_classification_commit_rollback_keeps_previous_current(database, tmp_path):
    engine, _, url = database
    app = create_app(Settings(_env_file=None, database_url=url, document_storage_dir=tmp_path))
    app.state.sessions = sessionmaker(engine, expire_on_commit=False)
    app.state.ocr_provider = FakeOCRProvider(app.state.storage)
    app.state.classifier = FakeClassifier()
    app.state.pipeline_spec = TEST_SPEC
    with TestClient(app) as client:
        uploaded = client.post("/api/v1/documents", files={"file": ("synthetic.png", make_image())})
        base = f"/api/v1/documents/{uploaded.json()['id']}"
        first = wait_for_status(client, base, "COMPLETED")
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE processing_runs ADD CONSTRAINT reject_classification "
                                    "CHECK (attempt = 1 OR classification IS NULL)"))
        client.post(base + "/process?reprocess=true")
        failed = wait_for_status(client, base, "FAILED")
        assert failed["latest_run"]["error_code"] == "RESULT_PERSISTENCE_FAILED"
        assert failed["latest_run"]["result"] is not None
        assert failed["current_run"] == first["current_run"]
