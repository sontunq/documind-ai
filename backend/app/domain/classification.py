"""Machine predictions from OCR text; probabilities are never OCR confidence."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from math import isclose
from typing import Protocol
from uuid import UUID

from app.domain.documents import DocumentStatus
from app.domain.ocr import OCRResult, unit_interval


class DocumentType(StrEnum):
    INVOICE = "invoice"
    CONTRACT = "contract"
    FORM = "form"


@dataclass(frozen=True)
class ClassScores:
    invoice: float
    contract: float
    form: float

    def __post_init__(self) -> None:
        for value in self.as_dict().values():
            unit_interval(value)
        if not isclose(sum(self.as_dict().values()), 1.0, abs_tol=1e-8):
            raise ValueError("Class probabilities must sum to one")

    def as_dict(self) -> dict[str, float]:
        return {"invoice": self.invoice, "contract": self.contract, "form": self.form}


@dataclass(frozen=True)
class ClassificationContext:
    document_id: UUID
    run_id: UUID


@dataclass(frozen=True)
class ClassificationResult:
    document_id: UUID
    run_id: UUID
    predicted_type: DocumentType
    scores: ClassScores
    confidence: float
    threshold: float
    model_identifier: str
    model_version: str
    dataset_version: str
    config_version: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.document_id, UUID) or not isinstance(self.run_id, UUID):
            raise ValueError("Classification identity must use UUIDs")
        if not isinstance(self.predicted_type, DocumentType) or not isinstance(self.scores, ClassScores):
            raise ValueError("Invalid classification label or probability vector")
        unit_interval(self.confidence)
        unit_interval(self.threshold)
        scores = self.scores.as_dict()
        if not isclose(self.confidence, scores[self.predicted_type], abs_tol=1e-8):
            raise ValueError("Selected confidence must equal selected probability")
        if scores[self.predicted_type] != max(scores.values()):
            raise ValueError("Prediction must select a highest-probability class")
        if not all(isinstance(v, str) and v.strip() for v in (
            self.model_identifier, self.model_version, self.dataset_version, self.config_version,
        )):
            raise ValueError("Classification provenance is required")
        if self.created_at.utcoffset() != timedelta(0):
            raise ValueError("Classification timestamp must be UTC")

    @property
    def needs_review(self) -> bool:
        return self.confidence < self.threshold

    @property
    def document_status(self) -> DocumentStatus:
        return DocumentStatus.NEEDS_REVIEW if self.needs_review else DocumentStatus.COMPLETED


class DocumentClassifier(Protocol):
    def predict(self, ocr_result: OCRResult, context: ClassificationContext) -> ClassificationResult: ...
