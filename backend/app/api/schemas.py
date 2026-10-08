from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.documents import DocumentStatus
from app.domain.ocr import BoundingBox
from app.domain.classification import ClassScores, DocumentType
from app.domain.review import ReviewStatus


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    media_type: str
    size_bytes: int
    checksum: str
    status: DocumentStatus
    page_count: int | None
    revision: int = 1
    created_at: datetime
    updated_at: datetime


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class OCRLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    order: int
    text: str
    confidence: float
    box: BoundingBox


class OCRPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    number: int
    width: int
    height: int
    text: str
    lines: list[OCRLineResponse]
    ocr_seconds: float


class OCRResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    document_id: UUID
    run_id: UUID
    provider: str
    provider_version: str
    engine_version: str
    detection_model: str
    recognition_model: str
    model_version: str
    confidence_source: str
    pages: list[OCRPageResponse]


class ClassificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    document_id: UUID
    run_id: UUID
    predicted_type: DocumentType
    scores: ClassScores
    confidence: float
    threshold: float
    needs_review: bool
    model_identifier: str
    model_version: str
    dataset_version: str
    config_version: str
    created_at: datetime


class ExtractedFieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    value: str | int | float | bool | None
    raw_value: str | None
    confidence: float
    page: int | None
    box: BoundingBox | None
    is_derived: bool


class InvoiceExtractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    invoice_number: ExtractedFieldResponse | None = None
    issue_date: ExtractedFieldResponse | None = None
    due_date: ExtractedFieldResponse | None = None
    supplier: ExtractedFieldResponse | None = None
    customer: ExtractedFieldResponse | None = None
    subtotal: ExtractedFieldResponse | None = None
    tax: ExtractedFieldResponse | None = None
    total: ExtractedFieldResponse | None = None
    currency: ExtractedFieldResponse | None = None


class ContractExtractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    contract_number: ExtractedFieldResponse | None = None
    title: ExtractedFieldResponse | None = None
    party_a: ExtractedFieldResponse | None = None
    party_b: ExtractedFieldResponse | None = None
    effective_date: ExtractedFieldResponse | None = None
    expiry_date: ExtractedFieldResponse | None = None
    contract_value: ExtractedFieldResponse | None = None
    governing_law: ExtractedFieldResponse | None = None


class FormExtractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    form_title: ExtractedFieldResponse | None = None
    fields: list[ExtractedFieldResponse] = []


class ExtractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    document_id: UUID
    run_id: UUID
    document_type: DocumentType
    invoice: InvoiceExtractionResponse | None = None
    contract: ContractExtractionResponse | None = None
    form: FormExtractionResponse | None = None
    extractor_name: str
    extractor_version: str
    created_at: datetime


class ProcessingRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    document_id: UUID
    pipeline_version: str
    config_version: str
    config: dict[str, str | int | float | bool]
    attempt: int
    status: DocumentStatus
    queued_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    total_seconds: float | None
    error_code: str | None
    error_message: str | None
    is_current: bool
    result: OCRResultResponse | None
    classification: ClassificationResponse | None
    classification_seconds: float | None
    extraction: ExtractionResponse | None
    extraction_seconds: float | None


class ReviewedFieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    field_name: str
    original_value: str | int | float | bool | None = None
    corrected_value: str | int | float | bool | None = None
    original_confidence: float | None = None
    is_modified: bool = False


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    document_id: UUID
    revision: int
    status: ReviewStatus
    reviewer_id: str
    document_type: DocumentType | None = None
    fields: list[ReviewedFieldResponse] = []
    rejection_reason: str | None = None
    notes: str | None = None
    created_at: datetime


class SubmitReviewRequest(BaseModel):
    expected_revision: int
    status: ReviewStatus
    reviewer_id: str = "reviewer"
    document_type: DocumentType | None = None
    fields: list[ReviewedFieldResponse] = []
    rejection_reason: str | None = None
    notes: str | None = None


class DocumentResultsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    document_id: UUID
    status: DocumentStatus
    latest_run: ProcessingRunResponse | None
    current_run: ProcessingRunResponse | None
    current_review: ReviewResponse | None = None
