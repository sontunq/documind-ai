"""Framework-independent domain models for visual review and correction (Phase 6)."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from app.domain.classification import DocumentType


class ReviewStatus(StrEnum):
    APPROVED = "APPROVED"
    CORRECTED = "CORRECTED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class ReviewedField:
    field_name: str
    original_value: str | int | float | bool | None
    corrected_value: str | int | float | bool | None
    original_confidence: float | None = None
    is_modified: bool = False

    def __post_init__(self) -> None:
        if not self.field_name or not isinstance(self.field_name, str):
            raise ValueError("Field name must be a non-empty string")
        if self.original_confidence is not None:
            if not 0.0 <= self.original_confidence <= 1.0:
                raise ValueError("Original confidence must be between 0.0 and 1.0")


@dataclass(frozen=True)
class ReviewRecord:
    id: UUID
    document_id: UUID
    revision: int
    status: ReviewStatus
    reviewer_id: str
    created_at: datetime
    document_type: DocumentType | None = None
    fields: tuple[ReviewedField, ...] = ()
    rejection_reason: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise ValueError("Review ID must be a UUID")
        if not isinstance(self.document_id, UUID):
            raise ValueError("Document ID must be a UUID")
        if self.revision < 1:
            raise ValueError("Revision must be positive")
        if not isinstance(self.status, ReviewStatus):
            raise ValueError("Status must be a canonical ReviewStatus")
        if not self.reviewer_id or len(self.reviewer_id) > 128:
            raise ValueError("Reviewer ID must contain 1 to 128 characters")
        if self.created_at.utcoffset() != timedelta(0):
            raise ValueError("Review timestamp must be timezone-aware UTC")
        if self.status == ReviewStatus.REJECTED and not self.rejection_reason:
            raise ValueError("Rejection reason is required when rejecting a document")
