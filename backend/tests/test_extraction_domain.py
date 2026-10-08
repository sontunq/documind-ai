from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4
import pytest

from app.domain.classification import DocumentType
from app.domain.extraction import (
    ContractExtraction,
    ExtractedField,
    ExtractionResult,
    FormExtraction,
    InvoiceExtraction,
)
from app.domain.ocr import BoundingBox
from app.infrastructure.extraction.normalization import (
    clean_text,
    normalize_amount,
    normalize_currency,
    normalize_date,
)


def test_extracted_field_validation():
    box = BoundingBox(0.1, 0.1, 0.5, 0.2)
    # Valid source-backed field
    field = ExtractedField(name="total", value=100.0, raw_value="100.00", confidence=0.9, page=1, box=box)
    assert field.name == "total"
    assert field.value == 100.0
    assert not field.is_derived

    # Valid derived field (no box or page required)
    derived = ExtractedField(name="total", value=100.0, raw_value=None, confidence=0.95, is_derived=True)
    assert derived.is_derived
    assert derived.box is None

    # Invalid empty name
    with pytest.raises(ValueError, match="Field name"):
        ExtractedField(name="", value=10, raw_value="10", confidence=0.8, page=1, box=box)

    # Invalid confidence
    with pytest.raises(ValueError, match="finite value between zero and one"):
        ExtractedField(name="total", value=10, raw_value="10", confidence=1.5, page=1, box=box)

    # Missing page or box for source-backed non-None value
    with pytest.raises(ValueError, match="valid 1-based page number"):
        ExtractedField(name="total", value=10, raw_value="10", confidence=0.8, page=None, box=box)
    with pytest.raises(ValueError, match="valid bounding box"):
        ExtractedField(name="total", value=10, raw_value="10", confidence=0.8, page=1, box=None)


def test_normalization_utilities():
    # Dates
    assert normalize_date("2026-09-01") == "2026-09-01"
    assert normalize_date("September 1, 2026") == "2026-09-01"
    assert normalize_date("Sep 1, 2026") == "2026-09-01"
    assert normalize_date("1 September 2026") == "2026-09-01"
    assert normalize_date("01/09/2026") == "2026-01-09"
    assert normalize_date("invalid date") is None
    assert normalize_date("") is None

    # Amounts
    assert normalize_amount("$88.00") == 88.0
    assert normalize_amount("80.00 USD") == 80.0
    assert normalize_amount("1,250.50") == 1250.50
    assert normalize_amount("none") is None

    # Currencies
    assert normalize_currency("$88.00") == "USD"
    assert normalize_currency("EUR 50") == "EUR"
    assert normalize_currency("50 €") == "EUR"
    assert normalize_currency("no currency") is None

    # Text cleaning
    assert clean_text("Full name: ___________________") == "Full name"
    assert clean_text("  ::: Demo Office Supplies --- ") == "Demo Office Supplies"


def test_extraction_result_validation():
    doc_id = uuid4()
    run_id = uuid4()
    box = BoundingBox(0.0, 0.0, 0.5, 0.5)
    inv = InvoiceExtraction(
        invoice_number=ExtractedField("invoice_number", "INV-1", "INV-1", 0.9, page=1, box=box)
    )

    result = ExtractionResult(
        document_id=doc_id,
        run_id=run_id,
        document_type=DocumentType.INVOICE,
        invoice=inv,
        extractor_name="test-extractor",
        extractor_version="1.0",
        created_at=datetime.now(UTC),
    )
    assert result.document_type == DocumentType.INVOICE
    assert result.invoice.invoice_number.value == "INV-1"

    # Mismatched payload for invoice
    with pytest.raises(ValueError, match="Invoice extraction payload is required"):
        ExtractionResult(
            document_id=doc_id,
            run_id=run_id,
            document_type=DocumentType.INVOICE,
            invoice=None,
            extractor_name="test-extractor",
            extractor_version="1.0",
            created_at=datetime.now(UTC),
        )

    # Non-UTC timestamp
    with pytest.raises(ValueError, match="timestamp must be UTC"):
        ExtractionResult(
            document_id=doc_id,
            run_id=run_id,
            document_type=DocumentType.INVOICE,
            invoice=inv,
            extractor_name="test-extractor",
            extractor_version="1.0",
            created_at=datetime.now(UTC).replace(tzinfo=timezone(timedelta(hours=7))),
        )
