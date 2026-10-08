"""Rule-based and layout-aware field extractor."""
from datetime import UTC, datetime
import re

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
from app.domain.ocr import OCRLine, OCRPage, OCRResult
from app.infrastructure.extraction.normalization import (
    clean_text,
    normalize_amount,
    normalize_currency,
    normalize_date,
)

EXTRACTOR_NAME = "rule-based-baseline"
EXTRACTOR_VERSION = "1.0.0"


class RuleBasedFieldExtractor(FieldExtractor):
    def __init__(self) -> None:
        self.name = EXTRACTOR_NAME
        self.version = EXTRACTOR_VERSION

    def extract(
        self,
        document_type: DocumentType,
        ocr_result: OCRResult,
        context: ExtractionContext,
    ) -> ExtractionResult:
        if document_type == DocumentType.INVOICE:
            invoice_data = self._extract_invoice(ocr_result)
            return ExtractionResult(
                document_id=context.document_id,
                run_id=context.run_id,
                document_type=DocumentType.INVOICE,
                invoice=invoice_data,
                extractor_name=self.name,
                extractor_version=self.version,
                created_at=datetime.now(UTC),
            )
        elif document_type == DocumentType.CONTRACT:
            contract_data = self._extract_contract(ocr_result)
            return ExtractionResult(
                document_id=context.document_id,
                run_id=context.run_id,
                document_type=DocumentType.CONTRACT,
                contract=contract_data,
                extractor_name=self.name,
                extractor_version=self.version,
                created_at=datetime.now(UTC),
            )
        elif document_type == DocumentType.FORM:
            form_data = self._extract_form(ocr_result)
            return ExtractionResult(
                document_id=context.document_id,
                run_id=context.run_id,
                document_type=DocumentType.FORM,
                form=form_data,
                extractor_name=self.name,
                extractor_version=self.version,
                created_at=datetime.now(UTC),
            )
        else:
            raise ValueError(f"Unsupported document type: {document_type}")

    def _extract_invoice(self, ocr: OCRResult) -> InvoiceExtraction:
        inv_number: ExtractedField | None = None
        issue_date: ExtractedField | None = None
        due_date: ExtractedField | None = None
        supplier: ExtractedField | None = None
        customer: ExtractedField | None = None
        subtotal: ExtractedField | None = None
        tax: ExtractedField | None = None
        total: ExtractedField | None = None
        currency: ExtractedField | None = None

        # Helper for layout-aware amount lookup (inline, horizontally adjacent, or next line)
        def find_amount(target_line_idx: int, lbl_line: OCRLine, keyword_pattern: str | None = None) -> tuple[float | None, str | None, OCRLine]:
            # 1. Check if amount is on the same line after the label (strip percentage rates like 8%)
            text_to_search = lbl_line.text
            if keyword_pattern:
                m_pos = re.search(keyword_pattern, lbl_line.text, re.IGNORECASE)
                if m_pos:
                    text_to_search = lbl_line.text[m_pos.end():]
            text_without_pct = re.sub(r"\(?\s*\d+(?:\.\d+)?\s*%\s*\)?", "", text_to_search)
            norm = normalize_amount(text_without_pct)
            if norm is not None and re.search(r"\d", text_without_pct):
                return norm, text_to_search.strip(), lbl_line

            # 2. Look horizontally adjacent on the same row (x to the right, y close)
            for j, other in enumerate(lines):
                if j != target_line_idx and abs(other.box.y - lbl_line.box.y) < 0.025 and other.box.x > lbl_line.box.x:
                    amt = normalize_amount(other.text)
                    if amt is not None:
                        return amt, other.text.strip(), other

            # 3. Look at immediately following line
            if target_line_idx + 1 < len(lines):
                nxt = lines[target_line_idx + 1]
                amt = normalize_amount(nxt.text)
                if amt is not None and nxt.box.y < lbl_line.box.y + 0.08:
                    return amt, nxt.text.strip(), nxt

            return None, None, lbl_line

        # Helper for column-based party lookup below a header like 'BILLED FROM' or 'BILLED TO'
        def find_party_below(hdr_line: OCRLine) -> OCRLine | None:
            candidates = []
            hx, hy = hdr_line.box.x, hdr_line.box.y
            for other in lines:
                ox, oy = other.box.x, other.box.y
                if hy < oy < hy + 0.15 and abs(ox - hx) < 0.15:
                    txt = other.text.strip()
                    if not re.search(r"^(?:tax\s*code|mã\s*số\s*thuế|mst|address|địa\s*chỉ|phone|điện\s*thoại|tel|contact|người\s*liên\s*hệ|billed|from|to)\b", txt, re.IGNORECASE):
                        candidates.append((oy - hy, other))
            if candidates:
                candidates.sort(key=lambda c: c[0])
                return candidates[0][1]
            return None

        # Iterate through pages and lines
        for page in ocr.pages:
            lines = page.lines
            for i, line in enumerate(lines):
                text = line.text

                # 1. Invoice Number
                if not inv_number:
                    match = re.search(r"(?:invoice\s*(?:no\.?|num(?:ber)?|#)?|số\s*(?:hóa\s*đơn|hđ|hd)?|hóa\s*đơn\s*số)\s*[:\-]?\s*([A-Za-z0-9\-]+)", text, re.IGNORECASE)
                    if match and match.group(1).upper() not in {"DEMO", "OFFICE", "SUPPLIES", "INVOICE"}:
                        inv_number = ExtractedField(
                            name="invoice_number",
                            value=clean_text(match.group(1)),
                            raw_value=match.group(0),
                            confidence=line.confidence,
                            page=page.number,
                            box=line.box,
                        )

                # 2. Issue Date
                if not issue_date:
                    match = re.search(r"(?:issue\s*date|invoice\s*date|date\s*of\s*issue|ngày\s*(?:lập|xuất|hóa\s*đơn|ký)|ngày)\s*[:\-]?\s*([^.]+)", text, re.IGNORECASE)
                    if match:
                        norm = normalize_date(match.group(1))
                        if norm:
                            issue_date = ExtractedField(
                                name="issue_date",
                                value=norm,
                                raw_value=match.group(1).strip(),
                                confidence=line.confidence,
                                page=page.number,
                                box=line.box,
                            )

                # 3. Due Date
                if not due_date:
                    match = re.search(r"(?:payment\s*due(?:\s*date)?|due\s*date|hạn\s*thanh\s*toán|ngày\s*hết\s*hạn)\s*[:\-]?\s*([^.]+)", text, re.IGNORECASE)
                    if match:
                        norm = normalize_date(match.group(1))
                        if norm:
                            due_date = ExtractedField(
                                name="due_date",
                                value=norm,
                                raw_value=match.group(1).strip(),
                                confidence=line.confidence,
                                page=page.number,
                                box=line.box,
                            )

                # 4. Supplier
                if not supplier:
                    match = re.search(r"(?:from|supplier|vendor|đơn\s*vị\s*bán(?:\s*hàng)?|bên\s*bán|người\s*bán|nhà\s*cung\s*cấp)\s*[:\-]\s*(.+)", text, re.IGNORECASE)
                    if match and clean_text(match.group(1)):
                        supplier = ExtractedField(
                            name="supplier",
                            value=clean_text(match.group(1)),
                            raw_value=match.group(1),
                            confidence=line.confidence,
                            page=page.number,
                            box=line.box,
                        )
                    elif re.search(r"\b(?:billed\s*from|đơn\s*vị\s*bán(?:\s*hàng)?|bên\s*bán|người\s*bán|nhà\s*cung\s*cấp)\b", text, re.IGNORECASE):
                        found_line = find_party_below(line)
                        if found_line:
                            supplier = ExtractedField(
                                name="supplier",
                                value=clean_text(found_line.text),
                                raw_value=found_line.text,
                                confidence=found_line.confidence,
                                page=page.number,
                                box=found_line.box,
                            )
                    elif re.search(r"^invoice\s*[-–:]\s*(.+)", text, re.IGNORECASE):
                        match = re.search(r"^invoice\s*[-–:]\s*(.+)", text, re.IGNORECASE)
                        supplier = ExtractedField(
                            name="supplier",
                            value=clean_text(match.group(1)),
                            raw_value=match.group(1),
                            confidence=line.confidence,
                            page=page.number,
                            box=line.box,
                        )

                # 5. Customer
                if not customer:
                    match = re.search(r"(?:bill\s*to|customer|client|đơn\s*vị\s*mua(?:\s*hàng)?|bên\s*mua|người\s*mua|khách\s*hàng)\s*[:\-]\s*(.+)", text, re.IGNORECASE)
                    if match and clean_text(match.group(1)):
                        customer = ExtractedField(
                            name="customer",
                            value=clean_text(match.group(1)),
                            raw_value=match.group(1),
                            confidence=line.confidence,
                            page=page.number,
                            box=line.box,
                        )
                    elif re.search(r"\b(?:billed\s*to|đơn\s*vị\s*mua(?:\s*hàng)?|bên\s*mua|người\s*mua|khách\s*hàng)\b", text, re.IGNORECASE):
                        found_line = find_party_below(line)
                        if found_line:
                            customer = ExtractedField(
                                name="customer",
                                value=clean_text(found_line.text),
                                raw_value=found_line.text,
                                confidence=found_line.confidence,
                                page=page.number,
                                box=found_line.box,
                            )
                    elif re.search(r"(?:bill\s*to|customer|client)\s*[:\-]?\s*(.*)", text, re.IGNORECASE):
                        match = re.search(r"(?:bill\s*to|customer|client)\s*[:\-]?\s*(.*)", text, re.IGNORECASE)
                        cust_val = clean_text(match.group(1))
                        if cust_val:
                            customer = ExtractedField(
                                name="customer",
                                value=cust_val,
                                raw_value=match.group(1),
                                confidence=line.confidence,
                                page=page.number,
                                box=line.box,
                            )
                        elif i + 1 < len(lines):
                            next_line = lines[i + 1]
                            customer = ExtractedField(
                                name="customer",
                                value=clean_text(next_line.text),
                                raw_value=next_line.text,
                                confidence=next_line.confidence,
                                page=page.number,
                                box=next_line.box,
                            )

                # 6. Subtotal
                if not subtotal:
                    subtotal_pat = r"\b(?:subtotal|sub-total|cộng\s*tiền\s*hàng|tổng\s*tiền\s*hàng|tiền\s*hàng|thành\s*tiền)\b"
                    if re.search(subtotal_pat, text, re.IGNORECASE):
                        amt, raw, target_l = find_amount(i, line, subtotal_pat)
                        if amt is not None:
                            subtotal = ExtractedField(
                                name="subtotal",
                                value=amt,
                                raw_value=raw,
                                confidence=target_l.confidence,
                                page=page.number,
                                box=target_l.box,
                            )

                # 7. Tax
                if not tax:
                    tax_pat = r"\b(?:vat(?:\s*\(\d+%\))?|sales\s*tax|tax(?:\s*\(\d+%\))?|thuế\s*(?:gtgt|suất)?(?:\s*\(\d+%\))?|tiền\s*thuế(?:\s*gtgt)?)\b"
                    if re.search(tax_pat, text, re.IGNORECASE) and not re.search(r"(?:tax\s*code|mã\s*số\s*thuế|mst|tax\s*invoice|vat\s*invoice|hóa\s*đơn\s*(?:gtgt|giá\s*trị\s*gia\s*tăng))\b", text, re.IGNORECASE):
                        amt, raw, target_l = find_amount(i, line, tax_pat)

                        if amt is not None:
                            tax = ExtractedField(
                                name="tax",
                                value=amt,
                                raw_value=raw,
                                confidence=target_l.confidence,
                                page=page.number,
                                box=target_l.box,
                            )

                # 8. Total
                if not total:
                    total_pat = r"\b(?:total(?:\s*payment)?|total(?:\s*amount)?(?:\s*due)?|amount\s*due|grand\s*total|balance\s*due|tổng\s*(?:cộng\s*)?(?:tiền\s*)?thanh\s*toán|tổng\s*cộng|tổng\s*tiền|số\s*tiền\s*bằng\s*số)\b"
                    if re.search(total_pat, text, re.IGNORECASE):
                        amt, raw, target_l = find_amount(i, line, total_pat)
                        if amt is not None:
                            total = ExtractedField(
                                name="total",
                                value=amt,
                                raw_value=raw,
                                confidence=target_l.confidence,
                                page=page.number,
                                box=target_l.box,
                            )

                # 9. Currency
                if not currency:
                    curr = normalize_currency(text)
                    if curr:
                        currency = ExtractedField(
                            name="currency",
                            value=curr,
                            raw_value=curr,
                            confidence=line.confidence,
                            page=page.number,
                            box=line.box,
                        )

            # Fallback for supplier from header if still missing
            if not supplier:
                for line in lines[:6]:
                    if re.search(r"(?:JSC|INC|LLC|LTD|CORP|COMPANY|CORPORATION|CÔNG\s*TY)\b", line.text, re.IGNORECASE):
                        supplier = ExtractedField(
                            name="supplier",
                            value=clean_text(line.text),
                            raw_value=line.text,
                            confidence=line.confidence,
                            page=page.number,
                            box=line.box,
                        )
                        break

            # Fallback for generic date if issue_date still missing
            if not issue_date:
                for line in lines:
                    match = re.search(r"\b(?:date|ngày)\s*[:\-]\s*([^.]+)", line.text, re.IGNORECASE)
                    if match:
                        norm = normalize_date(match.group(1))
                        if norm:
                            issue_date = ExtractedField(
                                name="issue_date",
                                value=norm,
                                raw_value=match.group(1).strip(),
                                confidence=line.confidence,
                                page=page.number,
                                box=line.box,
                            )
                            break

        return InvoiceExtraction(
            invoice_number=inv_number,
            issue_date=issue_date,
            due_date=due_date,
            supplier=supplier,
            customer=customer,
            subtotal=subtotal,
            tax=tax,
            total=total,
            currency=currency,
        )

    def _extract_contract(self, ocr: OCRResult) -> ContractExtraction:
        contract_number: ExtractedField | None = None
        title: ExtractedField | None = None
        party_a: ExtractedField | None = None
        party_b: ExtractedField | None = None
        effective_date: ExtractedField | None = None
        expiry_date: ExtractedField | None = None
        contract_value: ExtractedField | None = None
        governing_law: ExtractedField | None = None

        for page in ocr.pages:
            lines = page.lines
            for i, line in enumerate(lines):
                text = line.text

                # 1. Title
                if not title:
                    if re.search(r"(?:AGREEMENT|CONTRACT|TERMS OF SERVICE|MEMORANDUM OF UNDERSTANDING|HỢP\s*ĐỒNG|BIÊN\s*BẢN\s*GHI\s*NHỚ|THỎA\s*THUẬN)\b", text, re.IGNORECASE):
                        title = ExtractedField(
                            name="title",
                            value=clean_text(text),
                            raw_value=text,
                            confidence=line.confidence,
                            page=page.number,
                            box=line.box,
                        )

                # 2. Contract Number
                if not contract_number:
                    match = re.search(r"(?:(?:contract|agreement|hợp\s*đồng)\s*(?:no\.?|num(?:ber)?|#|số\s*(?:hđ)?)|số\s*(?:hợp\s*đồng|hđ)|contract\s*#)\s*[:\-]?\s*([A-Za-z0-9\-_/]+)", text, re.IGNORECASE)
                    if match:
                        contract_number = ExtractedField(
                            name="contract_number",
                            value=clean_text(match.group(1)),
                            raw_value=match.group(0),
                            confidence=line.confidence,
                            page=page.number,
                            box=line.box,
                        )

                # 3. Parties (Between X and Y or Bên A / Bên B)
                if not party_a or not party_b:
                    match = re.search(r"(?:between|giữa)\s+(.+?)\s+(?:and|và)\s+(.+?)(?:,|\.|$)", text, re.IGNORECASE)
                    if match:
                        p_a = clean_text(match.group(1))
                        p_b = clean_text(match.group(2))
                        if not party_a and p_a:
                            party_a = ExtractedField(
                                name="party_a",
                                value=p_a,
                                raw_value=match.group(1),
                                confidence=line.confidence,
                                page=page.number,
                                box=line.box,
                            )
                        if not party_b and p_b:
                            party_b = ExtractedField(
                                name="party_b",
                                value=p_b,
                                raw_value=match.group(2),
                                confidence=line.confidence,
                                page=page.number,
                                box=line.box,
                            )
                    else:
                        match_a = re.search(r"(?:party\s*a|bên\s*a|đại\s*diện\s*bên\s*a)\s*[:\-]\s*(.+)", text, re.IGNORECASE)
                        if match_a and not party_a:
                            party_a = ExtractedField(
                                name="party_a",
                                value=clean_text(match_a.group(1)),
                                raw_value=match_a.group(1),
                                confidence=line.confidence,
                                page=page.number,
                                box=line.box,
                            )
                        match_b = re.search(r"(?:party\s*b|bên\s*b|đại\s*diện\s*bên\s*b)\s*[:\-]\s*(.+)", text, re.IGNORECASE)
                        if match_b and not party_b:
                            party_b = ExtractedField(
                                name="party_b",
                                value=clean_text(match_b.group(1)),
                                raw_value=match_b.group(1),
                                confidence=line.confidence,
                                page=page.number,
                                box=line.box,
                            )

                # 4. Effective Date and Expiry Date Range
                if not effective_date or not expiry_date:
                    range_match = re.search(r"(?:thời\s*hạn\s*(?:hợp\s*đồng)?|term|duration)\s*[:\-]?\s*(?:từ\s*)?(\S+)\s+(?:đến|to|-)\s+(\S+)", text, re.IGNORECASE)
                    if range_match:
                        norm_eff = normalize_date(range_match.group(1))
                        norm_exp = normalize_date(range_match.group(2))
                        if norm_eff and not effective_date:
                            effective_date = ExtractedField(
                                name="effective_date",
                                value=norm_eff,
                                raw_value=range_match.group(1),
                                confidence=line.confidence,
                                page=page.number,
                                box=line.box,
                            )
                        if norm_exp and not expiry_date:
                            expiry_date = ExtractedField(
                                name="expiry_date",
                                value=norm_exp,
                                raw_value=range_match.group(2),
                                confidence=line.confidence,
                                page=page.number,
                                box=line.box,
                            )

                # 5. Effective Date Single
                if not effective_date:
                    match = re.search(r"(?:effective\s*(?:date)?\s*(?:is|as\s*of|[:\-])?|có\s*hiệu\s*lực\s*(?:từ\s*ngày|kể\s*từ\s*ngày)?\s*[:\-]?|ngày\s*bắt\s*đầu\s*[:\-]?)\s*([^.]+)", text, re.IGNORECASE)
                    if match:
                        norm = normalize_date(match.group(1))
                        if norm:
                            effective_date = ExtractedField(
                                name="effective_date",
                                value=norm,
                                raw_value=match.group(1).strip(),
                                confidence=line.confidence,
                                page=page.number,
                                box=line.box,
                            )

                # 6. Expiry / Termination Date Single
                if not expiry_date:
                    match = re.search(r"(?:(?:expiry|expiration|termination)\s*date|hết\s*hiệu\s*lực\s*(?:vào\s*ngày|ngày)?|thời\s*hạn\s*(?:hợp\s*đồng\s*)?đến\s*ngày|đến\s*ngày)\s*[:\-]?\s*([^.]+)", text, re.IGNORECASE)
                    if not match:
                        match = re.search(r"terminate(?:s)?\s*on\s*([^.]+)", text, re.IGNORECASE)
                    if match:
                        norm = normalize_date(match.group(1))
                        if norm:
                            expiry_date = ExtractedField(
                                name="expiry_date",
                                value=norm,
                                raw_value=match.group(1).strip(),
                                confidence=line.confidence,
                                page=page.number,
                                box=line.box,
                            )


                # 6. Contract Value
                if not contract_value:
                    match = re.search(r"(?:contract\s*value|fee|monthly\s*fee|total\s*fee|consideration|giá\s*trị\s*hợp\s*đồng|tổng\s*giá\s*trị|tổng\s*chi\s*phí)\s*[:\-]?\s*([$€£₫đ]?\s*[\d,.]+(?:\.\d{1,2})?(?:\s*[A-Z]{3})?)", text, re.IGNORECASE)
                    if match:
                        val = clean_text(match.group(1))
                        contract_value = ExtractedField(
                            name="contract_value",
                            value=val,
                            raw_value=match.group(1).strip(),
                            confidence=line.confidence,
                            page=page.number,
                            box=line.box,
                        )

                # 7. Governing Law
                if not governing_law:
                    match = re.search(r"(?:governed\s*by\s*(?:the\s*laws\s*of\s*)?|governing\s*law\s*[:\-]?\s*|luật\s*áp\s*dụng\s*[:\-]?\s*|pháp\s*luật\s*(?:áp\s*dụng)?\s*[:\-]?\s*)([A-Za-zÀ-ỹ\s]+?)(?:\.|$)", text, re.IGNORECASE)
                    if match:
                        law = clean_text(match.group(1))
                        if law:
                            governing_law = ExtractedField(
                                name="governing_law",
                                value=law,
                                raw_value=match.group(1).strip(),
                                confidence=line.confidence,
                                page=page.number,
                                box=line.box,
                            )

        return ContractExtraction(
            contract_number=contract_number,
            title=title,
            party_a=party_a,
            party_b=party_b,
            effective_date=effective_date,
            expiry_date=expiry_date,
            contract_value=contract_value,
            governing_law=governing_law,
        )

    def _extract_form(self, ocr: OCRResult) -> FormExtraction:
        form_title: ExtractedField | None = None
        fields: list[ExtractedField] = []

        for page in ocr.pages:
            lines = page.lines
            for line in lines:
                text = line.text

                # 1. Form title (usually first prominent header line with "FORM" or "APPLICATION")
                if not form_title:
                    if re.search(r"(?:FORM|APPLICATION|REGISTRATION|ĐƠN\s*XIN|TỜ\s*KHAI|PHIẾU\s*ĐĂNG\s*KÝ|BIỂU\s*MẪU|GIẤY\s*ĐỀ\s*NGHỊ)\b", text, re.IGNORECASE):
                        form_title = ExtractedField(
                            name="form_title",
                            value=clean_text(text),
                            raw_value=text,
                            confidence=line.confidence,
                            page=page.number,
                            box=line.box,
                        )
                        continue

                # 2. Key-Value pairs: e.g. "Full name: John Doe" or "Full name: ______"
                if ":" in text:
                    parts = text.split(":", 1)
                    label = clean_text(parts[0])
                    raw_val = parts[1].strip()
                    # Check if value is unfilled (e.g. underlines or brackets)
                    cleaned_val = clean_text(raw_val)
                    if not cleaned_val or re.match(r"^[_.\s\[\]]+$", raw_val):
                        val = None
                    else:
                        val = cleaned_val

                    if label and len(label) < 60:
                        fields.append(ExtractedField(
                            name=label,
                            value=val,
                            raw_value=raw_val if raw_val else None,
                            confidence=line.confidence,
                            page=page.number,
                            box=line.box,
                        ))

        return FormExtraction(
            form_title=form_title,
            fields=tuple(fields),
        )
