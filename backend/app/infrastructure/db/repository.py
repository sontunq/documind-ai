from dataclasses import asdict
from datetime import UTC
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.documents import Document, DocumentStatus
from app.infrastructure.db.models import DocumentRow


def to_document(row: DocumentRow) -> Document:
    return Document(
        id=row.id, original_filename=row.original_filename,
        storage_key=row.storage_key, media_type=row.media_type,
        size_bytes=row.size_bytes, checksum=row.checksum,
        status=DocumentStatus(row.status), page_count=row.page_count,
        created_at=row.created_at.astimezone(UTC), updated_at=row.updated_at.astimezone(UTC),
        revision=getattr(row, "revision", 1),
    )


class SQLDocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, document: Document) -> None:
        try:
            self.session.add(DocumentRow(**asdict(document)))
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def get(self, document_id: UUID) -> Document | None:
        row = self.session.get(DocumentRow, document_id)
        return to_document(row) if row is not None else None

    def list(self, *, limit: int, offset: int) -> list[Document]:
        query = select(DocumentRow).order_by(
            DocumentRow.created_at.desc(), DocumentRow.id.desc()
        ).limit(limit).offset(offset)
        return [to_document(row) for row in self.session.scalars(query)]
