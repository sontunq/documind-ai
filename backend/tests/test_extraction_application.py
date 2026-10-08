from io import BytesIO
from uuid import uuid4
import pytest

from app.application.errors import ApplicationError
from app.application.extract_fields import ExtractFields
from app.application.process_document import ProcessDocument
from app.domain.classification import DocumentType
from app.domain.documents import DocumentStatus as S
from app.domain.extraction import ExtractionContext
from conftest import make_image
from extraction_fakes import FakeFieldExtractor
from test_extractors import make_ocr
from test_processing import processing  # Shared fixture


def test_extract_fields_validations():
    extractor = FakeFieldExtractor()
    service = ExtractFields(extractor)
    doc_id = uuid4()
    run_id = uuid4()
    ctx = ExtractionContext(doc_id, run_id)

    # 1. Missing OCR
    with pytest.raises(ApplicationError, match="OCR is required"):
        service.execute(DocumentType.INVOICE, None, ctx)

    # 2. Mismatched OCR identity
    ocr = make_ocr(["Sample text"])
    with pytest.raises(ValueError, match="OCR identity mismatch"):
        service.execute(DocumentType.INVOICE, ocr, ctx)

    # 3. Empty OCR text
    empty_ocr = make_ocr(["    ", "  ---  "])
    empty_ctx = ExtractionContext(empty_ocr.document_id, empty_ocr.run_id)
    with pytest.raises(ApplicationError, match="no usable text"):
        service.execute(DocumentType.INVOICE, empty_ocr, empty_ctx)


def test_process_document_end_to_end_extraction(service, processing):
    p = processing
    extractor = FakeFieldExtractor()
    # Re-wire worker with extractor
    worker = ProcessDocument(p.repository, service.storage, p.preparer, p.provider, p.classifier, extractor)

    document = service.create(BytesIO(make_image()), "synthetic.png")
    run = p.scheduling.schedule(document.id)
    worker.execute(run.id)

    # Verify run completed with OCR, classification, and extraction
    completed_run = p.repository.results(document.id).current_run
    assert completed_run.status == S.COMPLETED
    assert completed_run.result is not None
    assert completed_run.classification is not None
    assert completed_run.classification.predicted_type == DocumentType.INVOICE
    assert completed_run.extraction is not None
    assert completed_run.extraction.document_type == DocumentType.INVOICE
    assert completed_run.extraction.invoice.invoice_number.value == "INV-100"
    assert completed_run.extraction_seconds is not None
    assert completed_run.extraction_seconds >= 0
    assert extractor.calls == 1


def test_process_document_extraction_failure_retains_ocr(service, processing):
    p = processing
    extractor = FakeFieldExtractor()
    extractor.fail = True  # Extraction fails
    worker = ProcessDocument(p.repository, service.storage, p.preparer, p.provider, p.classifier, extractor)

    document = service.create(BytesIO(make_image()), "synthetic.png")
    run = p.scheduling.schedule(document.id)
    worker.execute(run.id)

    runs = p.repository.runs
    failed_run = runs[run.id]
    assert failed_run.status == S.FAILED
    assert failed_run.error_code == "EXTRACTION_FAILED"
    # OCR was already saved before extraction failure!
    assert failed_run.result is not None
    assert failed_run.extraction is None
