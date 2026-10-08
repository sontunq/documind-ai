"""Deterministic test-only field extractor doubles. Never used by production."""
from datetime import UTC, datetime

from app.domain.classification import DocumentType
from app.domain.extraction import (
    ContractExtraction,
    ExtractedField,
    ExtractionContext,
    ExtractionResult,
    FieldExtractor,
    FormExtraction,
    InvoiceExtraction,
)
from app.domain.ocr import BoundingBox, OCRResult


class FakeFieldExtractor(FieldExtractor):
    def __init__(self, override_result=None) -> None:
        self.calls = 0
        self.fail = False
        self.override_result = override_result

    def extract(self, document_type: DocumentType, ocr_result: OCRResult, context: ExtractionContext) -> ExtractionResult:
        self.calls += 1
        if self.fail:
            raise RuntimeError("SECRET extraction adapter failure")
        if self.override_result is not None:
            return self.override_result

        box = BoundingBox(0.1, 0.1, 0.5, 0.05)
        if document_type == DocumentType.INVOICE:
            payload = InvoiceExtraction(
                invoice_number=ExtractedField("invoice_number", "INV-100", "INV-100", 0.95, page=1, box=box),
                total=ExtractedField("total", 100.0, "100.00", 0.90, page=1, box=box),
            )
            return ExtractionResult(
                document_id=context.document_id, run_id=context.run_id,
                document_type=DocumentType.INVOICE, invoice=payload,
                extractor_name="fake-extractor", extractor_version="0.0.1",
                created_at=datetime.now(UTC),
            )
        elif document_type == DocumentType.CONTRACT:
            payload = ContractExtraction(
                title=ExtractedField("title", "SERVICE AGREEMENT", "SERVICE AGREEMENT", 0.92, page=1, box=box),
                party_a=ExtractedField("party_a", "Acme Corp", "Acme Corp", 0.88, page=1, box=box),
            )
            return ExtractionResult(
                document_id=context.document_id, run_id=context.run_id,
                document_type=DocumentType.CONTRACT, contract=payload,
                extractor_name="fake-extractor", extractor_version="0.0.1",
                created_at=datetime.now(UTC),
            )
        else:
            payload = FormExtraction(
                form_title=ExtractedField("form_title", "REGISTRATION FORM", "REGISTRATION FORM", 0.91, page=1, box=box),
                fields=(ExtractedField("Full name", "John Doe", "John Doe", 0.85, page=1, box=box),),
            )
            return ExtractionResult(
                document_id=context.document_id, run_id=context.run_id,
                document_type=DocumentType.FORM, form=payload,
                extractor_name="fake-extractor", extractor_version="0.0.1",
                created_at=datetime.now(UTC),
            )
