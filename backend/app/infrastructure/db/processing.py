from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import TypeAdapter
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.application.errors import ApplicationError
from app.domain.documents import Document, DocumentStatus, transition
from app.domain.ocr import OCRResult
from app.domain.classification import ClassificationResult
from app.domain.extraction import ExtractionResult
from app.domain.processing import DocumentResults, PipelineSpec, ProcessingRun
from app.infrastructure.db.models import DocumentRow, ProcessingRunRow
from app.infrastructure.db.repository import to_document

RESULT = TypeAdapter(OCRResult)
CLASSIFICATION = TypeAdapter(ClassificationResult)
EXTRACTION = TypeAdapter(ExtractionResult)
ACTIVE = (DocumentStatus.QUEUED, DocumentStatus.PROCESSING)


def to_run(row: ProcessingRunRow) -> ProcessingRun:
    return ProcessingRun(
        id=row.id, document_id=row.document_id, pipeline_version=row.pipeline_version,
        config_version=row.config_version, config=row.config, attempt=row.attempt,
        status=DocumentStatus(row.status), queued_at=row.queued_at.astimezone(UTC),
        started_at=row.started_at.astimezone(UTC) if row.started_at else None,
        finished_at=row.finished_at.astimezone(UTC) if row.finished_at else None,
        total_seconds=row.total_seconds, error_code=row.error_code, error_message=row.error_message,
        is_current=row.is_current, result=RESULT.validate_python(row.result) if row.result else None,
        classification=CLASSIFICATION.validate_python(row.classification) if row.classification else None,
        classification_seconds=row.classification_seconds,
        extraction=EXTRACTION.validate_python(row.extraction) if row.extraction else None,
        extraction_seconds=row.extraction_seconds,
    )


class SQLProcessingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _document(self, document_id: UUID, *, lock: bool = False) -> DocumentRow:
        query = select(DocumentRow).where(DocumentRow.id == document_id)
        if lock:
            query = query.with_for_update()
        row = self.session.scalar(query.execution_options(populate_existing=True))
        if row is None:
            raise ApplicationError("DOCUMENT_NOT_FOUND", "Document not found.")
        return row

    def _move(self, document: DocumentRow, target: DocumentStatus) -> None:
        document.status = transition(DocumentStatus(document.status), target)
        document.updated_at = datetime.now(UTC)

    def reserve(self, document_id: UUID, spec: PipelineSpec, *, reprocess: bool) -> tuple[ProcessingRun, bool]:
        with self.session.begin():
            document = self._document(document_id, lock=True)
            if document.status in ACTIVE:
                raise ApplicationError("INVALID_PROCESSING_TRANSITION", "Document is not available for processing.")
            current = self.session.scalar(select(ProcessingRunRow).where(
                ProcessingRunRow.document_id == document_id, ProcessingRunRow.is_current,
            ))
            if (not reprocess and document.status in (DocumentStatus.COMPLETED, DocumentStatus.NEEDS_REVIEW) and current
                    and current.pipeline_version == spec.version and current.config_version == spec.config_version):
                return to_run(current), False
            attempt = self.session.scalar(select(func.coalesce(func.max(ProcessingRunRow.attempt), 0)).where(
                ProcessingRunRow.document_id == document_id, ProcessingRunRow.pipeline_version == spec.version,
            )) + 1
            self._move(document, DocumentStatus.QUEUED)
            row = ProcessingRunRow(
                id=uuid4(), document_id=document_id, pipeline_version=spec.version,
                config_version=spec.config_version, config=spec.config, attempt=attempt,
                status=DocumentStatus.QUEUED, queued_at=datetime.now(UTC), is_current=False,
            )
            self.session.add(row)
            self.session.flush()
            return to_run(row), True

    def _locked_run(self, run_id: UUID) -> tuple[DocumentRow, ProcessingRunRow] | None:
        document_id = self.session.scalar(select(ProcessingRunRow.document_id).where(ProcessingRunRow.id == run_id))
        if document_id is None:
            return None
        # Always lock the document first, including completion/failure, to avoid
        # deadlocks with scheduling. Locks are never held during model inference.
        document = self._document(document_id, lock=True)
        row = self.session.scalar(select(ProcessingRunRow).where(ProcessingRunRow.id == run_id)
                                  .with_for_update().execution_options(populate_existing=True))
        return document, row

    def claim(self, run_id: UUID) -> tuple[Document, ProcessingRun] | None:
        with self.session.begin():
            locked = self._locked_run(run_id)
            if locked is None or locked[1].status != DocumentStatus.QUEUED:
                return None
            document, row = locked
            self._move(document, DocumentStatus.PROCESSING)
            row.status = DocumentStatus.PROCESSING
            row.started_at = datetime.now(UTC)
            return to_document(document), to_run(row)

    def save_ocr(self, run_id: UUID, result: OCRResult) -> None:
        with self.session.begin():
            locked = self._locked_run(run_id)
            if locked is None or locked[1].status != DocumentStatus.PROCESSING:
                raise ApplicationError("INVALID_PROCESSING_TRANSITION", "Run is not processing.")
            document, row = locked
            if (result.document_id, result.run_id) != (document.id, row.id):
                raise ValueError("OCR identity mismatch")
            if row.result is not None:
                raise ValueError("OCR output is immutable")
            row.result = RESULT.dump_python(result, mode="json")

    def complete(self, run_id: UUID, result: OCRResult, seconds: float,
                 classification: ClassificationResult, classification_seconds: float,
                 extraction: ExtractionResult | None = None, extraction_seconds: float | None = None) -> None:
        with self.session.begin():
            locked = self._locked_run(run_id)
            if locked is None or locked[1].status != DocumentStatus.PROCESSING:
                raise ApplicationError("INVALID_PROCESSING_TRANSITION", "Run is not processing.")
            document, row = locked
            if result.document_id != document.id or result.run_id != row.id:
                raise ValueError("Result identity mismatch")
            if (classification.document_id, classification.run_id) != (document.id, row.id):
                raise ValueError("Classification identity mismatch")
            if extraction is not None and (extraction.document_id, extraction.run_id) != (document.id, row.id):
                raise ValueError("Extraction identity mismatch")
            if row.result != RESULT.dump_python(result, mode="json"):
                raise ValueError("Completion must use the saved OCR result")
            # Clear the previous pointer before setting the new one. The partial
            # unique index guarantees at most one current result per document.
            self.session.execute(update(ProcessingRunRow).where(
                ProcessingRunRow.document_id == document.id, ProcessingRunRow.is_current,
            ).values(is_current=False))
            self._move(document, classification.document_status)
            row.classification = CLASSIFICATION.dump_python(classification, mode="json")
            row.classification_seconds = classification_seconds
            if extraction is not None:
                row.extraction = EXTRACTION.dump_python(extraction, mode="json")
                row.extraction_seconds = extraction_seconds
            row.status = DocumentStatus.COMPLETED
            row.finished_at = datetime.now(UTC)
            row.total_seconds = seconds
            row.is_current = True

    def fail(self, run_id: UUID, code: str, message: str, seconds: float | None = None) -> None:
        with self.session.begin():
            locked = self._locked_run(run_id)
            if locked is None or locked[1].status not in ACTIVE:
                return
            document, row = locked
            self._move(document, DocumentStatus.FAILED)
            row.status = DocumentStatus.FAILED
            row.finished_at = datetime.now(UTC)
            row.total_seconds = seconds
            row.error_code, row.error_message = code, message

    def results(self, document_id: UUID) -> DocumentResults:
        with self.session.begin():
            # Lock briefly for a coherent document/latest/current snapshot.
            document = self._document(document_id, lock=True)
            latest = self.session.scalar(select(ProcessingRunRow).where(
                ProcessingRunRow.document_id == document_id,
            ).order_by(ProcessingRunRow.queued_at.desc(), ProcessingRunRow.id.desc()).limit(1))
            current = self.session.scalar(select(ProcessingRunRow).where(
                ProcessingRunRow.document_id == document_id, ProcessingRunRow.is_current,
            ))
            return DocumentResults(document_id, DocumentStatus(document.status),
                                   to_run(latest) if latest else None, to_run(current) if current else None)

    def recover_interrupted(self) -> int:
        """Offline operator command only: stop all app instances before calling."""
        with self.session.begin():
            ids = list(self.session.scalars(select(ProcessingRunRow.id).where(ProcessingRunRow.status.in_(ACTIVE))))
        for run_id in ids:
            self.fail(run_id, "PROCESSING_INTERRUPTED", "Processing was interrupted. Retry processing.")
        return len(ids)
