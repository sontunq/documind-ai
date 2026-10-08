"""PostgreSQL review persistence adapter (Phase 6)."""
from dataclasses import asdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.errors import ApplicationError
from app.domain.classification import DocumentType
from app.domain.documents import Document, DocumentStatus, transition
from app.domain.review import ReviewedField, ReviewRecord, ReviewStatus
from app.infrastructure.db.models import DocumentRow, ReviewRow
from app.infrastructure.db.repository import to_document


def to_review(row: ReviewRow) -> ReviewRecord:
    fields = tuple(
        ReviewedField(
            field_name=item["field_name"],
            original_value=item.get("original_value"),
            corrected_value=item.get("corrected_value"),
            original_confidence=item.get("original_confidence"),
            is_modified=item.get("is_modified", False),
        )
        for item in (row.fields or [])
    )
    doc_type = DocumentType(row.document_type) if row.document_type else None
    return ReviewRecord(
        id=row.id,
        document_id=row.document_id,
        revision=row.revision,
        status=ReviewStatus(row.status),
        reviewer_id=row.reviewer_id,
        created_at=row.created_at.astimezone(UTC),
        document_type=doc_type,
        fields=fields,
        rejection_reason=row.rejection_reason,
        notes=row.notes,
    )


class SQLReviewRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_review(
        self,
        review: ReviewRecord,
        expected_revision: int,
    ) -> tuple[Document, ReviewRecord]:
        with self.session.begin():
            # Lock document row to protect concurrent review submissions
            doc_query = select(DocumentRow).where(DocumentRow.id == review.document_id).with_for_update()
            doc_row = self.session.scalar(doc_query.execution_options(populate_existing=True))
            if doc_row is None:
                raise ApplicationError("DOCUMENT_NOT_FOUND", "Document not found.")

            # Optimistic concurrency check
            if doc_row.revision != expected_revision:
                raise ApplicationError(
                    "STALE_REVISION_CONFLICT",
                    f"Stale revision conflict: document is currently at revision {doc_row.revision}, "
                    f"but review expected revision {expected_revision}."
                )

            # Determine lifecycle target status
            if review.status in (ReviewStatus.APPROVED, ReviewStatus.CORRECTED):
                target_status = DocumentStatus.COMPLETED
            elif review.status == ReviewStatus.REJECTED:
                target_status = DocumentStatus.FAILED
            else:
                raise ApplicationError("INVALID_REVIEW_STATE", f"Unsupported review status {review.status}.")

            # Transition document lifecycle if not already at target status
            if doc_row.status != target_status.value:
                doc_row.status = transition(DocumentStatus(doc_row.status), target_status)
            new_revision = doc_row.revision + 1
            doc_row.revision = new_revision
            doc_row.updated_at = datetime.now(UTC)

            # Insert review record
            fields_data = [asdict(f) for f in review.fields]
            row = ReviewRow(
                id=review.id,
                document_id=review.document_id,
                revision=new_revision,
                status=review.status.value,
                reviewer_id=review.reviewer_id,
                document_type=review.document_type.value if review.document_type else None,
                fields=fields_data,
                rejection_reason=review.rejection_reason,
                notes=review.notes,
                created_at=review.created_at,
            )
            self.session.add(row)
            self.session.flush()
            return to_document(doc_row), to_review(row)

    def get_latest(self, document_id: UUID) -> ReviewRecord | None:
        query = (
            select(ReviewRow)
            .where(ReviewRow.document_id == document_id)
            .order_by(ReviewRow.revision.desc())
            .limit(1)
        )
        row = self.session.scalar(query)
        return to_review(row) if row is not None else None

    def list_history(self, document_id: UUID) -> list[ReviewRecord]:
        query = (
            select(ReviewRow)
            .where(ReviewRow.document_id == document_id)
            .order_by(ReviewRow.revision.desc())
        )
        return [to_review(row) for row in self.session.scalars(query)]
