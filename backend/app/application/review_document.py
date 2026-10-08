"""Application use cases for visual review and human correction (Phase 6)."""
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.application.errors import ApplicationError
from app.domain.classification import DocumentType
from app.domain.documents import Document
from app.domain.ports import ReviewRepository
from app.domain.review import ReviewedField, ReviewRecord, ReviewStatus


@dataclass(frozen=True)
class ReviewDocumentCommand:
    document_id: UUID
    expected_revision: int
    status: ReviewStatus
    reviewer_id: str
    document_type: DocumentType | None = None
    fields: tuple[ReviewedField, ...] = ()
    rejection_reason: str | None = None
    notes: str | None = None


class ReviewDocumentService:
    def __init__(self, repository: ReviewRepository) -> None:
        self.repository = repository

    def submit_review(self, command: ReviewDocumentCommand) -> tuple[Document, ReviewRecord]:
        if command.expected_revision < 1:
            raise ApplicationError("INVALID_REVIEW_DATA", "Expected revision must be positive.")
        if not command.reviewer_id or len(command.reviewer_id) > 128:
            raise ApplicationError("INVALID_REVIEW_DATA", "Reviewer ID must be between 1 and 128 characters.")
        if command.status == ReviewStatus.REJECTED and not command.rejection_reason:
            raise ApplicationError("INVALID_REVIEW_DATA", "Rejection reason is required when rejecting a document.")

        now = datetime.now(UTC)
        review = ReviewRecord(
            id=uuid4(),
            document_id=command.document_id,
            revision=command.expected_revision + 1,
            status=command.status,
            reviewer_id=command.reviewer_id,
            created_at=now,
            document_type=command.document_type,
            fields=command.fields,
            rejection_reason=command.rejection_reason,
            notes=command.notes,
        )

        return self.repository.save_review(review, expected_revision=command.expected_revision)

    def get_latest(self, document_id: UUID) -> ReviewRecord | None:
        return self.repository.get_latest(document_id)

    def list_history(self, document_id: UUID) -> list[ReviewRecord]:
        return self.repository.list_history(document_id)
