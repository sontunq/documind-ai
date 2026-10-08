from typing import BinaryIO, Protocol
from uuid import UUID

from app.domain.documents import Document
from app.domain.review import ReviewRecord


class DocumentRepository(Protocol):
    def create(self, document: Document) -> None:
        """Persist and commit metadata; raise on failure."""
        ...

    def get(self, document_id: UUID) -> Document | None: ...

    def list(self, *, limit: int, offset: int) -> list[Document]: ...


class DocumentStorage(Protocol):
    def store(self, stream: BinaryIO) -> str:
        """Store bytes under a generated key; remove partial data on failure."""
        ...

    def delete(self, storage_key: str) -> None: ...

    def open(self, storage_key: str) -> BinaryIO: ...


class ReviewRepository(Protocol):
    def save_review(
        self,
        review: ReviewRecord,
        expected_revision: int,
    ) -> tuple[Document, ReviewRecord]:
        """Atomically persist review record, verify expected_revision, and update document."""
        ...

    def get_latest(self, document_id: UUID) -> ReviewRecord | None:
        """Get latest review record for a document."""
        ...

    def list_history(self, document_id: UUID) -> list[ReviewRecord]:
        """List review audit history for a document."""
        ...
