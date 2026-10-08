from datetime import UTC, datetime, timedelta
import pytest
from uuid import uuid4

from app.domain.classification import DocumentType
from app.domain.documents import Document, DocumentStatus, InvalidTransition, transition
from app.domain.review import ReviewedField, ReviewRecord, ReviewStatus


def test_transition_rules_for_phase_6() -> None:
    # Review allows transitioning NEEDS_REVIEW to COMPLETED or FAILED
    assert transition(DocumentStatus.NEEDS_REVIEW, DocumentStatus.COMPLETED) == DocumentStatus.COMPLETED
    assert transition(DocumentStatus.NEEDS_REVIEW, DocumentStatus.FAILED) == DocumentStatus.FAILED
    assert transition(DocumentStatus.NEEDS_REVIEW, DocumentStatus.PROCESSING) == DocumentStatus.PROCESSING

    # COMPLETED allows transitioning to FAILED (rejection after completion)
    assert transition(DocumentStatus.COMPLETED, DocumentStatus.FAILED) == DocumentStatus.FAILED

    # Same-state transition is invalid
    with pytest.raises(InvalidTransition):
        transition(DocumentStatus.COMPLETED, DocumentStatus.COMPLETED)

    # Invalid transitions
    with pytest.raises(InvalidTransition):
        transition(DocumentStatus.UPLOADED, DocumentStatus.COMPLETED)


def test_reviewed_field_validation() -> None:
    field = ReviewedField(
        field_name="total",
        original_value="100.00",
        corrected_value="120.00",
        original_confidence=0.85,
        is_modified=True,
    )
    assert field.field_name == "total"
    assert field.is_modified is True

    # Empty field name
    with pytest.raises(ValueError, match="Field name must be a non-empty string"):
        ReviewedField(field_name="", original_value="100", corrected_value="100")

    # Invalid confidence
    with pytest.raises(ValueError, match="Original confidence must be between 0.0 and 1.0"):
        ReviewedField(field_name="total", original_value="100", corrected_value="100", original_confidence=1.5)


def test_review_record_validation() -> None:
    now = datetime.now(UTC)
    doc_id = uuid4()
    review_id = uuid4()

    record = ReviewRecord(
        id=review_id,
        document_id=doc_id,
        revision=1,
        status=ReviewStatus.APPROVED,
        reviewer_id="reviewer@documind.ai",
        created_at=now,
        document_type=DocumentType.INVOICE,
    )
    assert record.id == review_id
    assert record.revision == 1
    assert record.status == ReviewStatus.APPROVED

    # Revision must be positive
    with pytest.raises(ValueError, match="Revision must be positive"):
        ReviewRecord(
            id=review_id, document_id=doc_id, revision=0,
            status=ReviewStatus.APPROVED, reviewer_id="user1", created_at=now,
        )

    # Empty reviewer
    with pytest.raises(ValueError, match="Reviewer ID must contain 1 to 128 characters"):
        ReviewRecord(
            id=review_id, document_id=doc_id, revision=1,
            status=ReviewStatus.APPROVED, reviewer_id="", created_at=now,
        )

    # Rejection requires rejection_reason
    with pytest.raises(ValueError, match="Rejection reason is required when rejecting a document"):
        ReviewRecord(
            id=review_id, document_id=doc_id, revision=1,
            status=ReviewStatus.REJECTED, reviewer_id="user1", created_at=now,
            rejection_reason=None,
        )

    # Timezone-aware UTC requirement
    naive_time = datetime.now()
    with pytest.raises(ValueError, match="Review timestamp must be timezone-aware UTC"):
        ReviewRecord(
            id=review_id, document_id=doc_id, revision=1,
            status=ReviewStatus.APPROVED, reviewer_id="user1", created_at=naive_time,
        )


def test_document_revision_validation() -> None:
    now = datetime.now(UTC)
    doc = Document(
        id=uuid4(),
        original_filename="invoice.pdf",
        storage_key="a" * 32,
        media_type="application/pdf",
        size_bytes=1024,
        checksum="b" * 64,
        status=DocumentStatus.UPLOADED,
        created_at=now,
        updated_at=now,
        revision=1,
    )
    assert doc.revision == 1

    with pytest.raises(ValueError, match="Revision must be positive"):
        Document(
            id=uuid4(),
            original_filename="invoice.pdf",
            storage_key="a" * 32,
            media_type="application/pdf",
            size_bytes=1024,
            checksum="b" * 64,
            status=DocumentStatus.UPLOADED,
            created_at=now,
            updated_at=now,
            revision=0,
        )
