from dataclasses import replace
from datetime import UTC, datetime
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.api.dependencies import document_service, processing_service, review_service
from app.application.errors import ApplicationError
from app.application.process_document import ProcessDocument, ProcessingService
from app.application.review_document import ReviewDocumentCommand, ReviewDocumentService
from app.domain.classification import DocumentType
from app.domain.documents import DocumentStatus, transition
from app.domain.review import ReviewedField, ReviewRecord, ReviewStatus
from app.infrastructure.imaging.pages import DocumentPagePreparer
from app.main import create_app
from conftest import make_image, make_pdf
from ocr_fakes import FakeOCRProvider, MemoryProcessingRepository, ManualDispatcher, TEST_SPEC
from classification_fakes import FakeClassifier
from extraction_fakes import FakeFieldExtractor


class MemoryReviewRepository:
    def __init__(self, doc_repo):
        self.doc_repo = doc_repo
        self.reviews = {}

    def save_review(self, review: ReviewRecord, expected_revision: int):
        doc = self.doc_repo.get(review.document_id)
        if doc is None:
            raise ApplicationError("DOCUMENT_NOT_FOUND", "Document not found.")
        if doc.revision != expected_revision:
            raise ApplicationError(
                "STALE_REVISION_CONFLICT",
                f"Stale revision conflict: document is at {doc.revision}, expected {expected_revision}.",
            )
        new_rev = doc.revision + 1
        target_status = (
            DocumentStatus.COMPLETED
            if review.status in (ReviewStatus.APPROVED, ReviewStatus.CORRECTED)
            else DocumentStatus.FAILED
        )
        if doc.status != target_status:
            new_status = transition(doc.status, target_status)
        else:
            new_status = doc.status
        updated_doc = replace(doc, revision=new_rev, status=new_status, updated_at=datetime.now(UTC))
        self.doc_repo.documents[doc.id] = updated_doc

        final_review = replace(review, revision=new_rev)
        self.reviews.setdefault(review.document_id, []).append(final_review)
        return updated_doc, final_review

    def get_latest(self, document_id):
        revs = self.reviews.get(document_id, [])
        return revs[-1] if revs else None

    def list_history(self, document_id):
        revs = self.reviews.get(document_id, [])
        return list(reversed(revs))


@pytest.fixture
def review_env(service, settings):
    processing_repo = MemoryProcessingRepository(service.repository)
    review_repo = MemoryReviewRepository(service.repository)
    provider = FakeOCRProvider(service.storage)
    dispatcher = ManualDispatcher()
    preparer = DocumentPagePreparer(
        service.storage,
        max_upload_bytes=settings.max_upload_bytes,
        max_pdf_pages=settings.max_pdf_pages,
        max_image_pixels=settings.max_image_pixels,
        dpi=72,
    )
    classifier = FakeClassifier()
    extractor = FakeFieldExtractor()
    worker = ProcessDocument(processing_repo, service.storage, preparer, provider, classifier, extractor)
    processing_svc = ProcessingService(processing_repo, dispatcher, TEST_SPEC)
    review_svc = ReviewDocumentService(review_repo)

    app = create_app(settings)
    app.dependency_overrides[document_service] = lambda: service
    app.dependency_overrides[processing_service] = lambda: processing_svc
    app.dependency_overrides[review_service] = lambda: review_svc

    with TestClient(app, raise_server_exceptions=False) as client:
        yield SimpleNamespace(
            service=service,
            processing_repo=processing_repo,
            review_repo=review_repo,
            worker=worker,
            scheduling=processing_svc,
            client=client,
        )


def test_submit_review_approved(review_env):
    env = review_env
    # 1. Create and process document
    doc = env.service.create(BytesIO(make_pdf()), "invoice.pdf")
    run = env.scheduling.schedule(doc.id)
    env.worker.execute(run.id)

    # 2. Verify initially no review exists
    res = env.client.get(f"/api/v1/documents/{doc.id}/review")
    assert res.status_code == 404

    # 3. Submit review with status APPROVED
    review_payload = {
        "expected_revision": 1,
        "status": "APPROVED",
        "reviewer_id": "qa_tester",
        "document_type": "invoice",
        "fields": [
            {
                "field_name": "total",
                "original_value": "100.00",
                "corrected_value": "100.00",
                "original_confidence": 0.95,
                "is_modified": False,
            }
        ],
    }
    submit_res = env.client.put(f"/api/v1/documents/{doc.id}/review", json=review_payload)
    assert submit_res.status_code == 200, submit_res.text
    body = submit_res.json()
    assert body["status"] == "APPROVED"
    assert body["revision"] == 2
    assert body["reviewer_id"] == "qa_tester"

    # 4. Document status is now COMPLETED and revision is 2
    doc_after = env.client.get(f"/api/v1/documents/{doc.id}").json()
    assert doc_after["status"] == "COMPLETED"
    assert doc_after["revision"] == 2

    # 5. Review endpoint returns latest review
    review_res = env.client.get(f"/api/v1/documents/{doc.id}/review").json()
    assert review_res["status"] == "APPROVED"
    assert review_res["revision"] == 2


def test_stale_revision_conflict(review_env):
    env = review_env
    doc = env.service.create(BytesIO(make_pdf()), "contract.pdf")
    run = env.scheduling.schedule(doc.id)
    env.worker.execute(run.id)

    # Submit first review at revision 1 -> document revision becomes 2
    res1 = env.client.put(
        f"/api/v1/documents/{doc.id}/review",
        json={"expected_revision": 1, "status": "APPROVED", "reviewer_id": "user1"},
    )
    assert res1.status_code == 200

    # Submitting with stale expected_revision=1 must return 409 Conflict
    res2 = env.client.put(
        f"/api/v1/documents/{doc.id}/review",
        json={"expected_revision": 1, "status": "APPROVED", "reviewer_id": "user2"},
    )
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "STALE_REVISION_CONFLICT"


def test_review_rejection_and_audit_history(review_env):
    env = review_env
    doc = env.service.create(BytesIO(make_pdf()), "form.pdf")
    run = env.scheduling.schedule(doc.id)
    env.worker.execute(run.id)

    # Rejection requires reason
    bad_reject = env.client.put(
        f"/api/v1/documents/{doc.id}/review",
        json={"expected_revision": 1, "status": "REJECTED", "reviewer_id": "auditor"},
    )
    assert bad_reject.status_code == 422

    # Valid rejection
    reject_res = env.client.put(
        f"/api/v1/documents/{doc.id}/review",
        json={
            "expected_revision": 1,
            "status": "REJECTED",
            "reviewer_id": "auditor",
            "rejection_reason": "Damaged and illegible seal",
        },
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "REJECTED"

    doc_after = env.client.get(f"/api/v1/documents/{doc.id}").json()
    assert doc_after["status"] == "FAILED"
    assert doc_after["revision"] == 2

    # Check reviews audit history
    history = env.client.get(f"/api/v1/documents/{doc.id}/reviews").json()
    assert len(history) == 1
    assert history[0]["status"] == "REJECTED"


def test_page_image_endpoint(review_env):
    env = review_env
    # Single page PNG
    doc = env.service.create(BytesIO(make_image("PNG")), "photo.png")
    run = env.scheduling.schedule(doc.id)
    env.worker.execute(run.id)

    # Valid page 1
    img_res = env.client.get(f"/api/v1/documents/{doc.id}/pages/1/image")
    assert img_res.status_code == 200
    assert img_res.headers["content-type"] in ("image/png", "image/jpeg")
    assert len(img_res.content) > 0

    # Invalid page number (e.g. 5)
    not_found = env.client.get(f"/api/v1/documents/{doc.id}/pages/5/image")
    assert not_found.status_code == 404
