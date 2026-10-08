from uuid import uuid4

from app.domain.classification import DocumentType
from app.domain.extraction import ExtractionContext
from app.domain.ocr import BoundingBox, OCRLine, OCRPage, OCRResult
from app.infrastructure.extraction.rule_based import RuleBasedFieldExtractor


def make_ocr(lines_text: list[str], conf=0.92) -> OCRResult:
    doc_id = uuid4()
    run_id = uuid4()
    lines = tuple(
        OCRLine(i + 1, text, conf, BoundingBox(0.05, 0.05 * (i + 1), 0.8, 0.04))
        for i, text in enumerate(lines_text)
    )
    page = OCRPage(1, 1000, 1000, "\n".join(lines_text), lines, 0.1, "ref-1")
    return OCRResult(
        document_id=doc_id, run_id=run_id, provider="test", provider_version="1",
        engine_version="1", detection_model="det", recognition_model="rec",
        model_version="1", confidence_source="test", pages=(page,), raw_output_reference="ref-1",
    )


def test_rule_based_extractor_invoice():
    ocr = make_ocr([
        "INVOICE - DEMO OFFICE SUPPLIES",
        "Bill to Sample Community Center",
        "Invoice number DO-702",
        "Issue date: 2026-09-01. Payment due: 2026-09-30.",
        "Description Quantity Unit price Amount",
        "Subtotal 80.00 USD. Sales tax 8.00 USD.",
        "Total amount due 88.00 USD.",
    ])
    extractor = RuleBasedFieldExtractor()
    ctx = ExtractionContext(ocr.document_id, ocr.run_id)
    res = extractor.extract(DocumentType.INVOICE, ocr, ctx)

    assert res.document_type == DocumentType.INVOICE
    inv = res.invoice
    assert inv is not None
    assert inv.invoice_number.value == "DO-702"
    assert inv.issue_date.value == "2026-09-01"
    assert inv.due_date.value == "2026-09-30"
    assert inv.supplier.value == "DEMO OFFICE SUPPLIES"
    assert inv.customer.value == "Sample Community Center"
    assert inv.subtotal.value == 80.0
    assert inv.tax.value == 8.0
    assert inv.total.value == 88.0
    assert inv.currency.value == "USD"
    assert inv.total.page == 1
    assert inv.total.box is not None
    assert inv.total.confidence == 0.92


def test_rule_based_extractor_contract():
    ocr = make_ocr([
        "SERVICE AGREEMENT",
        "Between Demo Garden and Sample Maintenance",
        "Contract # AG-2026",
        "This contract is effective September 1, 2026.",
        "Either party may terminate on 2027-09-01.",
        "Monthly fee: $1,500.00 USD.",
        "Governing law: California",
    ])
    extractor = RuleBasedFieldExtractor()
    ctx = ExtractionContext(ocr.document_id, ocr.run_id)
    res = extractor.extract(DocumentType.CONTRACT, ocr, ctx)

    assert res.document_type == DocumentType.CONTRACT
    contract = res.contract
    assert contract is not None
    assert contract.title.value == "SERVICE AGREEMENT"
    assert contract.party_a.value == "Demo Garden"
    assert contract.party_b.value == "Sample Maintenance"
    assert contract.contract_number.value == "AG-2026"
    assert contract.effective_date.value == "2026-09-01"
    assert contract.expiry_date.value == "2027-09-01"
    assert contract.contract_value.value == "$1,500.00 USD"
    assert contract.governing_law.value == "California"


def test_rule_based_extractor_form():
    ocr = make_ocr([
        "COMMUNITY PROGRAM REGISTRATION FORM",
        "Please complete all fields in block letters.",
        "Full name: John Smith",
        "Email address: john@example.com",
        "Emergency contact name: _________________",
    ])
    extractor = RuleBasedFieldExtractor()
    ctx = ExtractionContext(ocr.document_id, ocr.run_id)
    res = extractor.extract(DocumentType.FORM, ocr, ctx)

    assert res.document_type == DocumentType.FORM
    form = res.form
    assert form is not None
    assert form.form_title.value == "COMMUNITY PROGRAM REGISTRATION FORM"
    field_map = {f.name: f.value for f in form.fields}
    assert field_map["Full name"] == "John Smith"
    assert field_map["Email address"] == "john@example.com"
    # Unfilled field has value None (not invented!)
    assert field_map["Emergency contact name"] is None


def test_rule_based_extractor_missing_fields_remain_none():
    ocr = make_ocr([
        "JUST A SIMPLE HEADING",
        "Some random non-field content without numbers or dates",
    ])
    extractor = RuleBasedFieldExtractor()
    ctx = ExtractionContext(ocr.document_id, ocr.run_id)
    res = extractor.extract(DocumentType.INVOICE, ocr, ctx)

    inv = res.invoice
    assert inv.invoice_number is None
    assert inv.issue_date is None
    assert inv.due_date is None
    assert inv.subtotal is None
    assert inv.tax is None
    assert inv.total is None
    assert inv.currency is None


def test_rule_based_extractor_vietnamese_invoice():
    ocr = make_ocr([
        "HÓA ĐƠN BÁN HÀNG",
        "Số hóa đơn: HD-2026-999",
        "Ngày lập: 07/10/2026",
        "Hạn thanh toán: 21/10/2026",
        "Bên bán: Công ty TNHH Giải Pháp Công Nghệ",
        "Bên mua: Công ty Cổ Phần Thương Mại Hoa Sen",
        "Cộng tiền hàng: 20.000.000 đ",
        "Tiền thuế GTGT: 2.000.000 đ",
        "Tổng cộng tiền thanh toán: 22.000.000 VND",
    ])
    extractor = RuleBasedFieldExtractor()
    ctx = ExtractionContext(ocr.document_id, ocr.run_id)
    res = extractor.extract(DocumentType.INVOICE, ocr, ctx)

    assert res.document_type == DocumentType.INVOICE
    inv = res.invoice
    assert inv is not None
    assert inv.invoice_number.value == "HD-2026-999"
    assert inv.issue_date.value == "2026-07-10" or inv.issue_date.value == "2026-10-07"
    assert inv.due_date.value == "2026-10-21"
    assert "Giải Pháp Công Nghệ" in inv.supplier.value
    assert "Hoa Sen" in inv.customer.value
    assert inv.subtotal.value == 20000000.0
    assert inv.tax.value == 2000000.0
    assert inv.total.value == 22000000.0
    assert inv.currency.value == "VND"


def test_rule_based_extractor_vietnamese_contract():
    ocr = make_ocr([
        "HỢP ĐỒNG KINH TẾ",
        "Số HĐ: HDKT-2026-01",
        "Giữa Công ty ABC và Tập đoàn XYZ",
        "Có hiệu lực từ ngày: 2026-01-01",
        "Thời hạn hợp đồng đến ngày: 2026-12-31",
        "Tổng giá trị: 100.000.000 VND",
        "Luật áp dụng: Pháp luật Việt Nam",
    ])
    extractor = RuleBasedFieldExtractor()
    ctx = ExtractionContext(ocr.document_id, ocr.run_id)
    res = extractor.extract(DocumentType.CONTRACT, ocr, ctx)

    assert res.document_type == DocumentType.CONTRACT
    c = res.contract
    assert c is not None
    assert c.title.value == "HỢP ĐỒNG KINH TẾ"
    assert c.contract_number.value == "HDKT-2026-01"
    assert c.party_a.value == "Công ty ABC"
    assert c.party_b.value == "Tập đoàn XYZ"
    assert c.effective_date.value == "2026-01-01"
    assert c.expiry_date.value == "2026-12-31"
    assert "100.000.000" in c.contract_value.value
    assert "Việt Nam" in c.governing_law.value
