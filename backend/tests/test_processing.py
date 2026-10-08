from dataclasses import replace
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.api.dependencies import document_service, processing_service
from app.application.errors import ApplicationError
from app.application.process_document import ProcessDocument, ProcessingService
from app.domain.documents import DocumentStatus as S
from app.infrastructure.imaging.pages import DocumentPagePreparer
from app.main import create_app
from conftest import make_image, make_pdf
from ocr_fakes import FakeOCRProvider, MemoryProcessingRepository, ManualDispatcher, TEST_SPEC
from classification_fakes import FakeClassifier


@pytest.fixture
def processing(service, settings):
    repository = MemoryProcessingRepository(service.repository)
    provider = FakeOCRProvider(service.storage)
    dispatcher = ManualDispatcher()
    preparer = DocumentPagePreparer(service.storage, max_upload_bytes=settings.max_upload_bytes,
                                    max_pdf_pages=settings.max_pdf_pages, max_image_pixels=settings.max_image_pixels,
                                    dpi=72)
    classifier = FakeClassifier()
    worker = ProcessDocument(repository, service.storage, preparer, provider, classifier)
    scheduling = ProcessingService(repository, dispatcher, TEST_SPEC)
    return SimpleNamespace(repository=repository, provider=provider, dispatcher=dispatcher,
                           preparer=preparer, worker=worker, scheduling=scheduling, classifier=classifier)


@pytest.mark.parametrize("data", [make_pdf(2), make_image(), make_image("JPEG")], ids=["pdf", "png", "jpeg"])
def test_process_retry_current_result_and_original_preservation(service, processing, data):
    document = service.create(BytesIO(data), "synthetic")
    p = processing
    assert p.repository.results(document.id).current_run is None
    first = p.scheduling.schedule(document.id)
    assert service.get(document.id).status == S.QUEUED
    with pytest.raises(ApplicationError) as error:
        p.scheduling.schedule(document.id)
    assert error.value.code == "INVALID_PROCESSING_TRANSITION"
    p.worker.execute(first.id)
    results = p.repository.results(document.id)
    assert results.status == S.COMPLETED
    assert results.current_run.result.pages[-1].number == document.page_count
    assert p.scheduling.schedule(document.id).id == first.id
    p.worker.execute(first.id)
    assert p.provider.calls == 1
    second = p.scheduling.schedule(document.id, reprocess=True)
    p.provider.fail = True
    p.worker.execute(second.id)
    results = p.repository.results(document.id)
    assert results.status == S.FAILED
    assert results.latest_run.error_code == "OCR_FAILED"
    assert "SECRET" not in results.latest_run.error_message
    assert results.current_run.id == first.id
    with service.storage.open(document.storage_key) as original:
        assert original.read() == data
    p.provider.fail = False
    third = p.scheduling.schedule(document.id)
    p.worker.execute(third.id)
    assert p.repository.results(document.id).current_run.id == third.id
    assert p.repository.runs[first.id].result == results.current_run.result
    assert third.attempt == 3
    assert sum(r.is_current for r in p.repository.runs.values()) == 1


def test_config_change_creates_new_attempt(service, processing):
    doc = service.create(BytesIO(make_image()), "test.png")
    run = processing.scheduling.schedule(doc.id)
    processing.worker.execute(run.id)
    processing.scheduling.spec = replace(TEST_SPEC, config_version="changed")
    assert processing.scheduling.schedule(doc.id).id != run.id


def test_scheduling_failure_and_unknown_document(service, processing):
    with pytest.raises(ApplicationError) as error:
        processing.scheduling.schedule(uuid4())
    assert error.value.code == "DOCUMENT_NOT_FOUND"
    doc = service.create(BytesIO(make_image()), "test.png")
    processing.dispatcher.fail = True
    with pytest.raises(ApplicationError) as error:
        processing.scheduling.schedule(doc.id)
    assert error.value.code == "SCHEDULING_FAILED"
    assert service.get(doc.id).status == S.FAILED
    with service.storage.open(doc.storage_key) as original:
        assert original.read() == make_image()


def test_result_persistence_failure_is_failed(service, processing, monkeypatch):
    doc = service.create(BytesIO(make_image()), "test.png")
    run = processing.scheduling.schedule(doc.id)
    def fail(*args):
        raise RuntimeError("SECRET database failure")
    monkeypatch.setattr(processing.repository, "complete", fail)
    processing.worker.execute(run.id)
    result = processing.repository.results(doc.id)
    assert result.status == S.FAILED
    assert result.latest_run.error_code == "RESULT_PERSISTENCE_FAILED"
    assert result.current_run is None
    # Persistence errors retain artifacts because COMMIT outcome can be unknown.
    # The original stays intact; these unreferenced attempt artifacts can be
    # reconciled offline without risking a successfully committed result.
    assert len(list(service.storage.root.iterdir())) == 3


def test_uncertain_commit_does_not_delete_referenced_artifacts(service, processing, monkeypatch):
    doc = service.create(BytesIO(make_image()), "test.png")
    run = processing.scheduling.schedule(doc.id)
    complete = processing.repository.complete
    def commit_then_disconnect(*args):
        complete(*args)
        raise ConnectionError("simulated lost COMMIT acknowledgment")
    monkeypatch.setattr(processing.repository, "complete", commit_then_disconnect)
    processing.worker.execute(run.id)
    results = processing.repository.results(doc.id)
    assert results.status == S.COMPLETED
    result = results.current_run.result
    for key in (doc.storage_key, result.raw_output_reference, result.pages[0].image_reference):
        with service.storage.open(key) as source:
            assert source.read()


def test_processing_state_visible_and_rejects_concurrent_request(service, processing):
    doc = service.create(BytesIO(make_image()), "test.png")
    run = processing.scheduling.schedule(doc.id)
    processing.repository.claim(run.id)
    assert service.get(doc.id).status == S.PROCESSING
    with pytest.raises(ApplicationError):
        processing.scheduling.schedule(doc.id, reprocess=True)
    processing.worker.execute(run.id)
    assert processing.provider.calls == 0


@pytest.fixture
def processing_client(settings, service, processing):
    app = create_app(settings)
    app.dependency_overrides[document_service] = lambda: service
    app.dependency_overrides[processing_service] = lambda: processing.scheduling
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def test_process_results_api_and_retry(processing_client, processing):
    client, p = processing_client, processing
    id = client.post("/api/v1/documents", files={"file": ("test.png", make_image())}).json()["id"]
    base = f"/api/v1/documents/{id}"
    assert client.get(base + "/results").json()["current_run"] is None
    response = client.post(base + "/process")
    assert response.status_code == 202
    assert response.json()["status"] == "QUEUED"
    assert client.post(base + "/process").status_code == 409
    p.worker.execute(p.dispatcher.pending[-1])
    result = client.get(base + "/results")
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["status"] == "COMPLETED"
    assert body["current_run"]["result"]["pages"][0]["lines"][0]["box"]["x"] == .1
    assert "reference" not in result.text and "storage_key" not in result.text
    assert client.post(base + "/process").json()["id"] == response.json()["id"]
    assert client.post(base + "/process?reprocess=true").status_code == 202
    p.provider.fail = True
    p.worker.execute(p.dispatcher.pending[-1])
    failed = client.get(base + "/results")
    assert failed.json()["status"] == "FAILED"
    assert "SECRET" not in failed.text and "private" not in failed.text
    assert client.get(base).status_code == 200
    p.provider.fail = False
    assert client.post(base + "/process").status_code == 202
    p.worker.execute(p.dispatcher.pending[-1])
    assert client.get(base + "/results").json()["status"] == "COMPLETED"
    assert client.post(f"/api/v1/documents/{uuid4()}/process").status_code == 404
    assert client.get(f"/api/v1/documents/{uuid4()}/results").status_code == 404


@pytest.mark.parametrize("scheduling_failure", [False, True])
def test_automatic_upload_flow_preserves_file(settings, service, processing, scheduling_failure):
    settings.ocr_auto_process = True
    p = processing
    p.dispatcher.fail = scheduling_failure
    app = create_app(settings)
    app.dependency_overrides[document_service] = lambda: service
    app.dependency_overrides[processing_service] = lambda: p.scheduling
    with TestClient(app) as client:
        response = client.post("/api/v1/documents", files={"file": ("test.png", make_image())})
        assert response.status_code == 201
        base = f"/api/v1/documents/{response.json()['id']}"
        assert client.get(base).json()["status"] == ("FAILED" if scheduling_failure else "QUEUED")
        if not scheduling_failure:
            p.worker.execute(p.dispatcher.pending[-1])
            assert client.get(base).json()["status"] == "COMPLETED"
    doc = service.list()[0]
    with service.storage.open(doc.storage_key) as original:
        assert original.read() == make_image()


def test_reservation_failure_after_committed_upload_does_not_undo_creation(settings, service, processing, monkeypatch):
    settings.ocr_auto_process = True
    def fail(*args, **kwargs):
        raise RuntimeError("SECRET database outage after creation")
    monkeypatch.setattr(processing.repository, "reserve", fail)
    app = create_app(settings)
    app.dependency_overrides[document_service] = lambda: service
    app.dependency_overrides[processing_service] = lambda: processing.scheduling
    with TestClient(app) as client:
        response = client.post("/api/v1/documents", files={"file": ("test.png", make_image())})
        assert response.status_code == 201
        assert "SECRET" not in response.text
        assert client.get(f"/api/v1/documents/{response.json()['id']}").json()["status"] == "UPLOADED"
    with service.storage.open(service.list()[0].storage_key) as original:
        assert original.read() == make_image()
