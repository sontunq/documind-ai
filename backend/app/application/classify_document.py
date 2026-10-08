from dataclasses import replace

from app.application.errors import ApplicationError
from app.domain.classification import ClassificationContext, ClassificationResult, DocumentClassifier
from app.domain.ocr import OCRResult


class ClassifyDocument:
    """Validate the stage output; the processing use case commits it with state."""
    def __init__(self, classifier: DocumentClassifier) -> None:
        self.classifier = classifier

    def execute(self, ocr: OCRResult | None, context: ClassificationContext) -> ClassificationResult:
        if ocr is None:
            raise ApplicationError("CLASSIFICATION_OCR_MISSING", "OCR is required before classification.")
        if (ocr.document_id, ocr.run_id) != (context.document_id, context.run_id):
            raise ValueError("OCR identity mismatch")
        if not any(character.isalnum() for page in ocr.pages for character in page.text):
            raise ApplicationError("CLASSIFICATION_EMPTY_TEXT", "OCR contains no usable text for classification.")
        result = self.classifier.predict(ocr, context)
        if not isinstance(result, ClassificationResult):
            raise ValueError("Invalid classifier result")
        # Re-run domain validation even for an incorrectly implemented adapter.
        result = replace(result, scores=replace(result.scores))
        if (result.document_id, result.run_id) != (context.document_id, context.run_id):
            raise ValueError("Classifier identity mismatch")
        return result
