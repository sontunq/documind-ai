"""Typed structured extraction contracts linked to OCR evidence."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

from app.domain.classification import DocumentType
from app.domain.ocr import BoundingBox, OCRResult, unit_interval


@dataclass(frozen=True)
class ExtractedField:
    name: str
    value: Any  # Normalized value: str, float, int, bool, or None if not found
    raw_value: str | None
    confidence: float
    page: int | None = None
    box: BoundingBox | None = None
    is_derived: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Field name must be a non-empty string")
        unit_interval(self.confidence)
        if self.value is not None and not self.is_derived:
            if self.page is None or self.page < 1:
                raise ValueError("Source-backed extracted field must have a valid 1-based page number")
            if self.box is None or not isinstance(self.box, BoundingBox):
                raise ValueError("Source-backed extracted field must have a valid bounding box")
        if self.page is not None and self.page < 1:
            raise ValueError("Page number must be one-based")


@dataclass(frozen=True)
class InvoiceExtraction:
    invoice_number: ExtractedField | None = None
    issue_date: ExtractedField | None = None
    due_date: ExtractedField | None = None
    supplier: ExtractedField | None = None
    customer: ExtractedField | None = None
    subtotal: ExtractedField | None = None
    tax: ExtractedField | None = None
    total: ExtractedField | None = None
    currency: ExtractedField | None = None

    def as_dict(self) -> dict[str, ExtractedField | None]:
        return {
            "invoice_number": self.invoice_number,
            "issue_date": self.issue_date,
            "due_date": self.due_date,
            "supplier": self.supplier,
            "customer": self.customer,
            "subtotal": self.subtotal,
            "tax": self.tax,
            "total": self.total,
            "currency": self.currency,
        }


@dataclass(frozen=True)
class ContractExtraction:
    contract_number: ExtractedField | None = None
    title: ExtractedField | None = None
    party_a: ExtractedField | None = None
    party_b: ExtractedField | None = None
    effective_date: ExtractedField | None = None
    expiry_date: ExtractedField | None = None
    contract_value: ExtractedField | None = None
    governing_law: ExtractedField | None = None

    def as_dict(self) -> dict[str, ExtractedField | None]:
        return {
            "contract_number": self.contract_number,
            "title": self.title,
            "party_a": self.party_a,
            "party_b": self.party_b,
            "effective_date": self.effective_date,
            "expiry_date": self.expiry_date,
            "contract_value": self.contract_value,
            "governing_law": self.governing_law,
        }


@dataclass(frozen=True)
class FormExtraction:
    form_title: ExtractedField | None = None
    fields: tuple[ExtractedField, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "form_title": self.form_title,
            "fields": list(self.fields),
        }


@dataclass(frozen=True)
class ExtractionContext:
    document_id: UUID
    run_id: UUID


@dataclass(frozen=True)
class ExtractionResult:
    document_id: UUID
    run_id: UUID
    document_type: DocumentType
    invoice: InvoiceExtraction | None = None
    contract: ContractExtraction | None = None
    form: FormExtraction | None = None
    extractor_name: str = "rule-based"
    extractor_version: str = "1.0"
    created_at: datetime = datetime.min

    def __post_init__(self) -> None:
        if not isinstance(self.document_id, UUID) or not isinstance(self.run_id, UUID):
            raise ValueError("Extraction identity must use UUIDs")
        if not isinstance(self.document_type, DocumentType):
            raise ValueError("Document type must be a valid DocumentType enum")
        if not (isinstance(self.extractor_name, str) and self.extractor_name.strip()
                and isinstance(self.extractor_version, str) and self.extractor_version.strip()):
            raise ValueError("Extractor provenance (name and version) is required")
        if self.created_at.utcoffset() != timedelta(0):
            raise ValueError("Extraction timestamp must be UTC")
        if self.document_type == DocumentType.INVOICE and self.invoice is None:
            raise ValueError("Invoice extraction payload is required for invoice type")
        if self.document_type == DocumentType.CONTRACT and self.contract is None:
            raise ValueError("Contract extraction payload is required for contract type")
        if self.document_type == DocumentType.FORM and self.form is None:
            raise ValueError("Form extraction payload is required for form type")


class FieldExtractor(Protocol):
    def extract(self, document_type: DocumentType, ocr_result: OCRResult, context: ExtractionContext) -> ExtractionResult: ...
