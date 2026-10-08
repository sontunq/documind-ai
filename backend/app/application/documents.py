from datetime import UTC, datetime
from hashlib import sha256
from typing import BinaryIO, Callable
from uuid import UUID, uuid4

from app.application.errors import ApplicationError
from app.domain.documents import Document, DocumentStatus
from app.domain.ports import DocumentRepository, DocumentStorage


def safe_filename(filename: str | None) -> str:
    # The name is display metadata only, never a path.
    name = (filename or "document").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(c for c in name if ord(c) >= 32 and ord(c) != 127).strip()
    return name[:255] if name not in {"", ".", ".."} else "document"


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
        storage: DocumentStorage,
        validate: Callable[[BinaryIO], tuple[str, int]],
        max_upload_bytes: int,
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.validate = validate
        self.max_upload_bytes = max_upload_bytes

    def create(self, stream: BinaryIO, filename: str | None) -> Document:
        stream.seek(0)
        checksum = sha256()
        size = 0
        while chunk := stream.read(64 * 1024):
            size += len(chunk)
            if size > self.max_upload_bytes:
                raise ApplicationError("UPLOAD_TOO_LARGE", "Upload exceeds the configured size limit.")
            checksum.update(chunk)
        if not size:
            raise ApplicationError("EMPTY_UPLOAD", "The uploaded file is empty.")
        stream.seek(0)
        media_type, page_count = self.validate(stream)
        stream.seek(0)
        try:
            key = self.storage.store(stream)
        except Exception as exc:
            raise ApplicationError("STORAGE_UNAVAILABLE", "Document storage is unavailable.") from exc
        try:
            now = datetime.now(UTC)
            document = Document(
                id=uuid4(), original_filename=safe_filename(filename), storage_key=key,
                media_type=media_type, size_bytes=size, checksum=checksum.hexdigest(),
                status=DocumentStatus.UPLOADED, created_at=now, updated_at=now,
                page_count=page_count,
            )
            self.repository.create(document)
        except Exception as exc:
            try:
                self.storage.delete(key)
            except Exception as cleanup_error:
                # Never pretend rollback cleanup succeeded. Operational intervention
                # is needed if disk permissions/hardware prevent deletion.
                raise ApplicationError(
                    "UPLOAD_CLEANUP_FAILED", "Upload failed and storage cleanup requires attention."
                ) from cleanup_error
            raise ApplicationError("PERSISTENCE_UNAVAILABLE", "Document metadata could not be saved.") from exc
        return document

    def get(self, document_id: UUID) -> Document:
        document = self.repository.get(document_id)
        if document is None:
            raise ApplicationError("DOCUMENT_NOT_FOUND", "Document not found.")
        return document

    def list(self, *, limit: int = 50, offset: int = 0) -> list[Document]:
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("Invalid pagination")
        return self.repository.list(limit=limit, offset=offset)
