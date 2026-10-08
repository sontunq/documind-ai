"""Validate field extraction output and enforce domain provenance rules."""
from dataclasses import replace

from app.application.errors import ApplicationError
from app.domain.classification import DocumentType
from app.domain.extraction import ExtractionContext, ExtractionResult, FieldExtractor
from app.domain.ocr import OCRResult


class ExtractFields:
    """Validate the extraction stage output; the processing use case coordinates and commits it."""
    def __init__(self, extractor: FieldExtractor) -> None:
        self.extractor = extractor

    def execute(
        self,
        document_type: DocumentType,
        ocr: OCRResult | None,
        context: ExtractionContext,
    ) -> ExtractionResult:
        if ocr is None:
            raise ApplicationError("EXTRACTION_OCR_MISSING", "OCR is required before field extraction.")
        if (ocr.document_id, ocr.run_id) != (context.document_id, context.run_id):
            raise ValueError("OCR identity mismatch")
        if not any(character.isalnum() for page in ocr.pages for character in page.text):
            raise ApplicationError("EXTRACTION_EMPTY_TEXT", "OCR contains no usable text for field extraction.")

        result = self.extractor.extract(document_type, ocr, context)
        if not isinstance(result, ExtractionResult):
            raise ValueError("Invalid extraction result returned by extractor")
        if (result.document_id, result.run_id) != (context.document_id, context.run_id):
            raise ValueError("Extractor identity mismatch")
        if result.document_type != document_type:
            raise ValueError("Extractor returned mismatched document type")

        return result
