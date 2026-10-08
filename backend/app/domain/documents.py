"""Framework-independent document metadata and lifecycle rules."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
import re
from uuid import UUID


class DocumentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class InvalidTransition(ValueError):
    pass


def transition(current: DocumentStatus, target: DocumentStatus) -> DocumentStatus:
    # Phase 6 human review can move NEEDS_REVIEW to COMPLETED or FAILED, and allow re-review.
    allowed = {
        DocumentStatus.UPLOADED: {DocumentStatus.QUEUED, DocumentStatus.PROCESSING},
        DocumentStatus.QUEUED: {DocumentStatus.PROCESSING, DocumentStatus.FAILED},
        DocumentStatus.PROCESSING: {DocumentStatus.COMPLETED, DocumentStatus.NEEDS_REVIEW, DocumentStatus.FAILED},
        DocumentStatus.NEEDS_REVIEW: {DocumentStatus.QUEUED, DocumentStatus.PROCESSING, DocumentStatus.COMPLETED, DocumentStatus.FAILED},
        DocumentStatus.COMPLETED: {DocumentStatus.QUEUED, DocumentStatus.PROCESSING, DocumentStatus.FAILED},
        DocumentStatus.FAILED: {DocumentStatus.QUEUED, DocumentStatus.PROCESSING},
    }
    if target not in allowed.get(current, set()):
        raise InvalidTransition("Document cannot transition to the requested state.")
    return target


@dataclass(frozen=True)
class Document:
    id: UUID
    original_filename: str
    storage_key: str
    media_type: str
    size_bytes: int
    checksum: str
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime
    page_count: int | None = None
    revision: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise ValueError("Document ID must be a UUID")
        if not self.original_filename or len(self.original_filename) > 255:
            raise ValueError("Filename must contain 1 to 255 characters")
        if any(c in self.original_filename for c in '/\\') or any(
            ord(c) < 32 or ord(c) == 127 for c in self.original_filename
        ):
            raise ValueError("Filename must be a safe display name")
        if not re.fullmatch(r"[a-f0-9]{32}", self.storage_key):
            raise ValueError("Invalid storage key")
        if self.media_type not in {"application/pdf", "image/png", "image/jpeg"}:
            raise ValueError("Unsupported media type")
        if self.size_bytes <= 0:
            raise ValueError("Document must not be empty")
        if not re.fullmatch(r"[a-f0-9]{64}", self.checksum):
            raise ValueError("Checksum must be SHA-256")
        if not isinstance(self.status, DocumentStatus):
            raise ValueError("Status must be a canonical DocumentStatus")
        for timestamp in (self.created_at, self.updated_at):
            if timestamp.utcoffset() != timedelta(0):
                raise ValueError("Timestamps must be timezone-aware UTC")
        if self.updated_at < self.created_at:
            raise ValueError("Updated timestamp precedes creation")
        if self.page_count is not None and self.page_count <= 0:
            raise ValueError("Page count must be positive")
        if self.revision < 1:
            raise ValueError("Revision must be positive")
