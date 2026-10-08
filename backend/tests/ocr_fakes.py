"""Deterministic test-only OCR and repository doubles. Never used by the app."""
from dataclasses import replace
from datetime import UTC, datetime
from io import BytesIO
from uuid import uuid4

from app.application.errors import ApplicationError
from app.domain.documents import DocumentStatus, transition
from app.domain.ocr import BoundingBox, OCRLine, OCRPage, OCRResult
from app.domain.processing import DocumentResults, PipelineSpec, ProcessingRun

TEST_SPEC = PipelineSpec("test-ocr-v1", "test-config-1", {"provider": "TEST ONLY synthetic fake"})


class FakeOCRProvider:
    """Scores below are fixed test fixtures, never measured AI confidence."""
    def __init__(self, storage):
        self.storage = storage
        self.calls = 0
        self.fail = False
        self.seen_pages = []

    def recognize(self, pages, context):
        self.calls += 1
        if self.fail:
            raise RuntimeError("SECRET C:/private/ocr.png")
        results = []
        for page in pages:
            self.seen_pages.append((page.number, page.width, page.height))
            line = OCRLine(1, f"SYNTHETIC PAGE {page.number}", 0.875, BoundingBox(0.1, 0.1, 0.7, 0.2))
            results.append(OCRPage(page.number, page.width, page.height, line.text, (line,), 0.0, page.image_reference))
        reference = self.storage.store(BytesIO(b'{"test_only": true}'))
        return OCRResult(context.document_id, context.run_id, "TEST ONLY", "fixture-v1", "none",
                         "fake-det", "fake-rec", "fixture-v1", "synthetic test fixture",
                         tuple(results), reference)


class MemoryProcessingRepository:
    def __init__(self, documents):
        self.documents = documents
        self.runs = {}

    def _get(self, document_id):
        document = self.documents.get(document_id)
        if document is None:
            raise ApplicationError("DOCUMENT_NOT_FOUND", "Document not found.")
        return document

    def _move(self, document_id, target):
        doc = self._get(document_id)
        doc = replace(doc, status=transition(doc.status, target), updated_at=datetime.now(UTC))
        self.documents.documents[doc.id] = doc
        return doc

    def reserve(self, document_id, spec, *, reprocess):
        document = self._get(document_id)
        if document.status in {DocumentStatus.QUEUED, DocumentStatus.PROCESSING}:
            raise ApplicationError("INVALID_PROCESSING_TRANSITION", "Document is not available for processing.")
        current = self.results(document_id).current_run
        if (not reprocess and document.status in {DocumentStatus.COMPLETED, DocumentStatus.NEEDS_REVIEW} and current
                and current.pipeline_version == spec.version and current.config_version == spec.config_version):
            return current, False
        attempt = 1 + max((r.attempt for r in self.runs.values()
                           if r.document_id == document_id and r.pipeline_version == spec.version), default=0)
        self._move(document_id, DocumentStatus.QUEUED)
        run = ProcessingRun(uuid4(), document_id, spec.version, spec.config_version, spec.config,
                            attempt, DocumentStatus.QUEUED, datetime.now(UTC))
        self.runs[run.id] = run
        return run, True

    def claim(self, run_id):
        run = self.runs.get(run_id)
        if run is None or run.status != DocumentStatus.QUEUED:
            return None
        document = self._move(run.document_id, DocumentStatus.PROCESSING)
        run = replace(run, status=DocumentStatus.PROCESSING, started_at=datetime.now(UTC))
        self.runs[run.id] = run
        return document, run

    def save_ocr(self, run_id, result):
        self.runs[run_id] = replace(self.runs[run_id], result=result)

    def complete(self, run_id, result, seconds, classification, classification_seconds,
                 extraction=None, extraction_seconds=None):
        run = self.runs[run_id]
        self._move(run.document_id, classification.document_status)
        for old in tuple(self.runs.values()):
            if old.document_id == run.document_id and old.is_current:
                self.runs[old.id] = replace(old, is_current=False)
        self.runs[run.id] = replace(run, status=DocumentStatus.COMPLETED, finished_at=datetime.now(UTC),
                                    total_seconds=seconds, result=result, is_current=True,
                                    classification=classification, classification_seconds=classification_seconds,
                                    extraction=extraction, extraction_seconds=extraction_seconds)

    def fail(self, run_id, code, message, seconds=None):
        run = self.runs[run_id]
        if run.status not in {DocumentStatus.QUEUED, DocumentStatus.PROCESSING}:
            return
        self._move(run.document_id, DocumentStatus.FAILED)
        self.runs[run.id] = replace(run, status=DocumentStatus.FAILED, finished_at=datetime.now(UTC),
                                    total_seconds=seconds, error_code=code, error_message=message)

    def results(self, document_id):
        document = self._get(document_id)
        runs = [r for r in self.runs.values() if r.document_id == document_id]
        return DocumentResults(document_id, document.status, runs[-1] if runs else None,
                               next((r for r in runs if r.is_current), None))


class ManualDispatcher:
    def __init__(self):
        self.pending = []
        self.fail = False

    def enqueue(self, run_id):
        if self.fail:
            raise RuntimeError("SECRET scheduling error")
        self.pending.append(run_id)
