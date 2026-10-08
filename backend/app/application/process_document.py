"""Use cases callable by HTTP wiring, the in-process runner, or a future worker."""
import logging
from time import perf_counter
from uuid import UUID

from app.application.errors import ApplicationError
from app.application.classify_document import ClassifyDocument
from app.application.extract_fields import ExtractFields
from app.domain.classification import ClassificationContext, DocumentClassifier
from app.domain.extraction import ExtractionContext, FieldExtractor
from app.domain.ocr import OCRContext, OCRProvider
from app.domain.ports import DocumentStorage
from app.domain.processing import (
    DocumentResults, PagePreparer, PipelineSpec, ProcessingJobDispatcher,
    ProcessingRepository, ProcessingRun,
)

logger = logging.getLogger(__name__)


class ProcessDocument:
    def __init__(self, repository: ProcessingRepository, storage: DocumentStorage,
                 preparer: PagePreparer, provider: OCRProvider, classifier: DocumentClassifier,
                 extractor: FieldExtractor | None = None) -> None:
        self.repository = repository
        self.storage = storage
        self.preparer = preparer
        self.provider = provider
        self.classification = ClassifyDocument(classifier)
        self.extraction = ExtractFields(extractor) if extractor is not None else None

    def execute(self, run_id: UUID) -> None:
        claimed = self.repository.claim(run_id)
        if claimed is None:
            return  # Duplicate delivery never executes or overwrites a finished run.
        document, run = claimed
        start = perf_counter()
        stage = "STORAGE"
        result = None
        retain_ocr = False
        try:
            with self.storage.open(document.storage_key) as stream:
                stage = "PAGE_PREPARATION"
                with self.preparer.prepare(stream, document) as pages:
                    stage = "OCR"
                    result = self.provider.recognize(
                        pages, OCRContext(document.id, run.id, run.pipeline_version)
                    )
                    if result.document_id != document.id or result.run_id != run.id:
                        raise ValueError("Provider returned mismatched provenance")
                    if len(result.pages) != document.page_count:
                        raise ValueError("Provider returned an incomplete document")
            # Finish artifact preparation before the database transaction. A
            # connection loss during COMMIT can have an unknown outcome; never
            # delete artifacts which a committed result might already reference.
            stage = "RESULT_PERSISTENCE"
            # Retain artifacts even if this COMMIT's acknowledgment is lost.
            retain_ocr = True
            self.repository.save_ocr(run.id, result)
            stage = "CLASSIFICATION"
            classification_start = perf_counter()
            classification = self.classification.execute(result, ClassificationContext(document.id, run.id))
            classification_seconds = perf_counter() - classification_start

            extraction = None
            extraction_seconds = None
            if self.extraction is not None:
                stage = "EXTRACTION"
                extraction_start = perf_counter()
                extraction = self.extraction.execute(
                    classification.predicted_type, result, ExtractionContext(document.id, run.id)
                )
                extraction_seconds = perf_counter() - extraction_start

            stage = "RESULT_PERSISTENCE"
            self.repository.complete(
                run.id, result, perf_counter() - start,
                classification, classification_seconds,
                extraction, extraction_seconds,
            )
        except Exception as error:
            # Never copy an exception string: parsers/providers may include text,
            # credentials or paths. Failure is visible in persisted state and logs.
            code = f"{stage}_FAILED"
            message = "Processing failed; the original upload is available for retry."
            if isinstance(error, ApplicationError) and error.code in ("CLASSIFICATION_EMPTY_TEXT", "EXTRACTION_EMPTY_TEXT"):
                code, message = error.code, "OCR contains no usable text for processing."
            self.repository.fail(run.id, code, message,
                                 perf_counter() - start)
            if result is not None and not retain_ocr:
                try:
                    self.storage.delete(result.raw_output_reference)
                except Exception:
                    logger.warning("Raw OCR artifact cleanup failed for run %s", run.id)
            logger.warning("Processing run %s failed at %s", run.id, stage)


class ProcessingService:
    def __init__(self, repository: ProcessingRepository, dispatcher: ProcessingJobDispatcher,
                 spec: PipelineSpec) -> None:
        self.repository = repository
        self.dispatcher = dispatcher
        self.spec = spec

    def schedule(self, document_id: UUID, *, reprocess: bool = False) -> ProcessingRun:
        run, created = self.repository.reserve(document_id, self.spec, reprocess=reprocess)
        if created:
            try:
                self.dispatcher.enqueue(run.id)
            except Exception as exc:
                self.repository.fail(run.id, "SCHEDULING_FAILED", "OCR could not be scheduled. Retry processing.")
                raise ApplicationError("SCHEDULING_FAILED", "OCR could not be scheduled. Retry processing.") from exc
        return run

    def after_upload(self, document_id: UUID) -> None:
        try:
            self.schedule(document_id)
        except Exception:
            # Document creation has already committed; never roll back or delete it.
            logger.warning("Automatic OCR scheduling failed for document %s; retry is available", document_id)

    def results(self, document_id: UUID) -> DocumentResults:
        return self.repository.results(document_id)
