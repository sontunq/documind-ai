"""Phase 3 PostgreSQL transactions and API checks with a test-only OCR provider."""
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from threading import Barrier
from time import monotonic, sleep
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app.application.documents import DocumentService
from app.application.errors import ApplicationError
from app.application.process_document import ProcessDocument, ProcessingService
from app.core.config import Settings
from app.domain.documents import DocumentStatus as S
from app.infrastructure.db.models import ProcessingRunRow
from app.infrastructure.db.processing import SQLProcessingRepository
from app.infrastructure.db.repository import SQLDocumentRepository
from app.infrastructure.imaging.pages import DocumentPagePreparer
from app.infrastructure.storage.local import LocalDocumentStorage
from app.infrastructure.validation import UploadValidator
from app.main import create_app
from conftest import make_image
from ocr_fakes import FakeOCRProvider, ManualDispatcher, TEST_SPEC
from classification_fakes import FakeClassifier
from test_postgres import database  # Shared isolated-schema fixture, not application data.

pytestmark = pytest.mark.postgres


def create_document(engine, storage):
    with Session(engine) as session:
        return DocumentService(SQLDocumentRepository(session), storage, UploadValidator(2, 10000), 4096).create(
            BytesIO(make_image()), "synthetic.png")


def wait_for_status(client, base, expected):
    deadline = monotonic() + 10
    while monotonic() < deadline:
        result = client.get(base + "/results")
        assert result.status_code == 200, result.text
        if result.json()["status"] == expected:
            return result.json()
        sleep(.02)
    pytest.fail(f"Did not reach {expected}")


@pytest.mark.parametrize("processed", [False, True], ids=["without-ocr-run", "completed-ocr-run"])
def test_listed_document_results_require_exact_uuid(database, tmp_path, monkeypatch, processed):
    engine, _, url = database
    # Reproduce the reported fifth-character d/c mismatch using synthetic IDs,
    # without committing a user's document identifier or accessing their data.
    generated = str(uuid4())
    stored_id = UUID(generated[:4] + "d" + generated[5:])
    mistyped_id = UUID(generated[:4] + "c" + generated[5:])
    monkeypatch.setattr("app.application.documents.uuid4", lambda: stored_id)
    settings = Settings(_env_file=None, database_url=url, document_storage_dir=tmp_path / "uploads",
                        ocr_auto_process=False)
    app = create_app(settings)
    # Use real dependencies and repositories. Both must respect this same
    # session factory/search_path rather than silently connecting to public.
    app.state.sessions = sessionmaker(engine, expire_on_commit=False)
    app.state.ocr_provider = FakeOCRProvider(app.state.storage)
    app.state.classifier = FakeClassifier()
    app.state.pipeline_spec = TEST_SPEC
    with TestClient(app) as client:
        uploaded = client.post("/api/v1/documents", files={"file": ("synthetic.png", make_image())})
        assert uploaded.status_code == 201, uploaded.text
        listed = client.get("/api/v1/documents").json()
        assert [item["id"] for item in listed] == [str(stored_id)]
        base = f"/api/v1/documents/{listed[0]['id']}"
        if processed:
            assert client.post(base + "/process").status_code == 202
            wait_for_status(client, base, "COMPLETED")
        expected_status = "COMPLETED" if processed else "UPLOADED"
        for spelling in (str(stored_id), str(stored_id).upper()):
            metadata = client.get(f"/api/v1/documents/{spelling}")
            results = client.get(f"/api/v1/documents/{spelling}/results")
            assert metadata.status_code == results.status_code == 200
            assert metadata.json()["id"] == results.json()["document_id"] == str(stored_id)
            assert results.json()["status"] == expected_status
            if not processed:
                assert results.json()["latest_run"] is None
                assert results.json()["current_run"] is None
        for suffix in ("", "/results"):
            missing = client.get(f"/api/v1/documents/{mistyped_id}{suffix}")
            assert missing.status_code == 404
            assert missing.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"
            assert client.get(f"/api/v1/documents/not-a-uuid{suffix}").status_code == 422
    # Check PostgreSQL UUID round trips and both repository lookup paths directly.
    with Session(engine) as session:
        found = SQLDocumentRepository(session).get(stored_id)
        assert isinstance(found.id, UUID) and found.id == stored_id
        assert SQLDocumentRepository(session).get(mistyped_id) is None
    with Session(engine) as session:
        assert SQLProcessingRepository(session).results(stored_id).document_id == stored_id
        with pytest.raises(ApplicationError) as error:
            SQLProcessingRepository(session).results(mistyped_id)
        assert error.value.code == "DOCUMENT_NOT_FOUND"


def test_postgres_background_api_retry_failure_and_restart(database, tmp_path):
    engine, _, url = database
    settings = Settings(_env_file=None, database_url=url, document_storage_dir=tmp_path / "uploads")
    app = create_app(settings)
    app.state.sessions = sessionmaker(engine, expire_on_commit=False)
    provider = FakeOCRProvider(app.state.storage)
    app.state.ocr_provider = provider
    app.state.classifier = FakeClassifier()
    app.state.pipeline_spec = TEST_SPEC
    with TestClient(app) as client:
        uploaded = client.post("/api/v1/documents", files={"file": ("test.png", make_image())})
        assert uploaded.status_code == 201, uploaded.text
        id = uploaded.json()["id"]
        base = f"/api/v1/documents/{id}"
        first = wait_for_status(client, base, "COMPLETED")
        run = first["current_run"]
        assert run["started_at"].endswith("Z") and run["finished_at"].endswith("Z")
        assert run["result"]["pages"][0]["lines"][0]["confidence"] == .875
        assert client.post(base + "/process").json()["id"] == run["id"]
        assert provider.calls == 1
        provider.fail = True
        assert client.post(base + "/process?reprocess=true").status_code == 202
        failed = wait_for_status(client, base, "FAILED")
        assert failed["current_run"]["id"] == run["id"]
        assert failed["latest_run"]["error_code"] == "OCR_FAILED"
        assert "SECRET" not in str(failed) and "private" not in str(failed)
        with Session(engine) as session:
            doc = SQLDocumentRepository(session).get(UUID(id))
            with app.state.storage.open(doc.storage_key) as original:
                assert original.read() == make_image()
        provider.fail = False
        assert client.post(base + "/process").status_code == 202
        completed = wait_for_status(client, base, "COMPLETED")
        assert completed["current_run"]["attempt"] == 3
    engine.dispose()
    second = create_app(settings)
    second.state.sessions = sessionmaker(engine, expire_on_commit=False)
    with TestClient(second) as client:
        assert client.get(base + "/results").json() == completed
    with Session(engine) as session:
        rows = list(session.scalars(select(ProcessingRunRow).where(ProcessingRunRow.document_id == UUID(id))))
        assert len(rows) == 3
        assert sum(r.is_current for r in rows) == 1
        assert sum(r.result is not None for r in rows) == 2


def test_concurrent_reservation_duplicate_delivery_and_recovery(database, tmp_path):
    engine, _, _ = database
    storage = LocalDocumentStorage(tmp_path)
    doc = create_document(engine, storage)
    barrier = Barrier(2)
    def reserve():
        with Session(engine) as session:
            barrier.wait(timeout=5)
            try:
                return SQLProcessingRepository(session).reserve(doc.id, TEST_SPEC, reprocess=False)[0]
            except ApplicationError as error:
                return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: reserve(), range(2)))
    assert outcomes.count("INVALID_PROCESSING_TRANSITION") == 1
    run = next(item for item in outcomes if not isinstance(item, str))
    with Session(engine) as session:
        repo = SQLProcessingRepository(session)
        assert repo.claim(run.id) is not None
        assert repo.claim(run.id) is None
        assert repo.recover_interrupted() == 1
        assert repo.recover_interrupted() == 0
        assert repo.results(doc.id).latest_run.error_code == "PROCESSING_INTERRUPTED"
        retried, created = repo.reserve(doc.id, TEST_SPEC, reprocess=False)
        assert created and retried.attempt == 2


def test_completion_transaction_rollback_keeps_original_and_previous_result(database, tmp_path):
    engine, _, _ = database
    storage = LocalDocumentStorage(tmp_path)
    doc = create_document(engine, storage)
    provider = FakeOCRProvider(storage)
    preparer = DocumentPagePreparer(storage, max_upload_bytes=4096, max_pdf_pages=2, max_image_pixels=10000)
    with Session(engine) as session:
        repository = SQLProcessingRepository(session)
        scheduling = ProcessingService(repository, ManualDispatcher(), TEST_SPEC)
        worker = ProcessDocument(repository, storage, preparer, provider, FakeClassifier())
        first = scheduling.schedule(doc.id)
        worker.execute(first.id)
        second = scheduling.schedule(doc.id, reprocess=True)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE processing_runs ADD CONSTRAINT reject_test_result CHECK (attempt = 1 OR result IS NULL)"))
    with Session(engine) as session:
        repository = SQLProcessingRepository(session)
        ProcessDocument(repository, storage, preparer, provider, FakeClassifier()).execute(second.id)
        results = repository.results(doc.id)
        assert results.status == S.FAILED
        assert results.latest_run.error_code == "RESULT_PERSISTENCE_FAILED"
        assert results.current_run.id == first.id
    with storage.open(doc.storage_key) as original:
        assert original.read() == make_image()
