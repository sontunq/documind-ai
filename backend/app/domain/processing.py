from collections.abc import Iterator
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO, Protocol
from uuid import UUID

from app.domain.documents import Document, DocumentStatus
from app.domain.classification import ClassificationResult
from app.domain.extraction import ExtractionResult
from app.domain.ocr import OCRResult, PreparedPage


@dataclass(frozen=True)
class PipelineSpec:
    version: str
    config_version: str
    config: dict[str, str | int | float | bool]


@dataclass(frozen=True)
class ProcessingRun:
    id: UUID
    document_id: UUID
    pipeline_version: str
    config_version: str
    config: dict[str, str | int | float | bool]
    attempt: int
    status: DocumentStatus
    queued_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    total_seconds: float | None = None
    error_code: str | None = None
    error_message: str | None = None
    is_current: bool = False
    result: OCRResult | None = None
    classification: ClassificationResult | None = None
    classification_seconds: float | None = None
    extraction: ExtractionResult | None = None
    extraction_seconds: float | None = None


@dataclass(frozen=True)
class DocumentResults:
    document_id: UUID
    status: DocumentStatus
    latest_run: ProcessingRun | None
    current_run: ProcessingRun | None


class PagePreparer(Protocol):
    def prepare(self, stream: BinaryIO, document: Document) -> AbstractContextManager[Iterator[PreparedPage]]: ...


class ProcessingRepository(Protocol):
    def reserve(self, document_id: UUID, spec: PipelineSpec, *, reprocess: bool) -> tuple[ProcessingRun, bool]: ...
    def claim(self, run_id: UUID) -> tuple[Document, ProcessingRun] | None: ...
    def save_ocr(self, run_id: UUID, result: OCRResult) -> None: ...
    def complete(self, run_id: UUID, result: OCRResult, seconds: float,
                 classification: ClassificationResult, classification_seconds: float,
                 extraction: ExtractionResult | None = None, extraction_seconds: float | None = None) -> None: ...
    def fail(self, run_id: UUID, code: str, message: str, seconds: float | None = None) -> None: ...
    def results(self, document_id: UUID) -> DocumentResults: ...


class ProcessingJobDispatcher(Protocol):
    def enqueue(self, run_id: UUID) -> None: ...
