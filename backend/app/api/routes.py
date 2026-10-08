from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.responses import StreamingResponse

from app.api.dependencies import document_service, processing_service, review_service
from app.api.schemas import (
    DocumentResponse, ErrorResponse, DocumentResultsResponse, ProcessingRunResponse,
    ReviewResponse, SubmitReviewRequest,
)
from app.application.documents import DocumentService
from app.application.errors import ApplicationError
from app.application.process_document import ProcessingService
from app.application.review_document import ReviewDocumentCommand, ReviewDocumentService
from app.domain.review import ReviewedField

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])
Service = Annotated[DocumentService, Depends(document_service)]
Processing = Annotated[ProcessingService, Depends(processing_service)]
Review = Annotated[ReviewDocumentService, Depends(review_service)]


@router.post(
    "", status_code=201, response_model=DocumentResponse,
    responses={code: {"model": ErrorResponse} for code in (413, 415, 422, 500, 503)},
    openapi_extra={"requestBody": {"required": True, "content": {
        "multipart/form-data": {"schema": {"type": "object", "required": ["file"],
            "properties": {"file": {"type": "string", "format": "binary"}}}}
    }}},
)
async def upload_document(request: Request, service: Service, processing: Processing) -> DocumentResponse:
    # Restrict multipart shape before running synchronous validation/storage work.
    async with request.form(max_files=1, max_fields=0) as form:
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise ApplicationError("INVALID_REQUEST", "Provide one file in the 'file' multipart field.")
        document = await run_in_threadpool(service.create, upload.file, upload.filename)
        if request.app.state.settings.ocr_auto_process:
            await run_in_threadpool(processing.after_upload, document.id)
        # This is the committed creation snapshot. Get/detail returns live state.
        return DocumentResponse.model_validate(document)


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    service: Service,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DocumentResponse]:
    return [DocumentResponse.model_validate(item) for item in service.list(limit=limit, offset=offset)]


@router.get("/{document_id}", response_model=DocumentResponse,
            responses={404: {"model": ErrorResponse}})
def get_document(document_id: UUID, service: Service) -> DocumentResponse:
    return DocumentResponse.model_validate(service.get(document_id))


@router.get("/{document_id}/file",
            responses={404: {"model": ErrorResponse}})
def get_document_file(document_id: UUID, service: Service) -> StreamingResponse:
    document = service.get(document_id)
    stream = service.storage.open(document.storage_key)
    return StreamingResponse(
        stream,
        media_type=document.media_type,
        headers={"Content-Disposition": f'inline; filename="{document.original_filename}"'}
    )


@router.get("/{document_id}/pages/{page_number}/image",
            responses={404: {"model": ErrorResponse}})
def get_page_image(
    document_id: UUID,
    page_number: int,
    service: Service,
    processing: Processing,
) -> StreamingResponse:
    if page_number < 1:
        raise ApplicationError("PAGE_NOT_FOUND", "Page number must be positive.")
    document = service.get(document_id)
    results = processing.results(document_id)
    active_run = results.current_run or results.latest_run
    if active_run and active_run.result and active_run.result.pages:
        for page in active_run.result.pages:
            if page.number == page_number:
                stream = service.storage.open(page.image_reference)
                return StreamingResponse(
                    stream,
                    media_type="image/png",
                    headers={"Content-Disposition": f'inline; filename="{document.id}_page_{page_number}.png"'}
                )
    if page_number == 1 and document.media_type in ("image/png", "image/jpeg"):
        stream = service.storage.open(document.storage_key)
        return StreamingResponse(
            stream,
            media_type=document.media_type,
            headers={"Content-Disposition": f'inline; filename="{document.original_filename}"'}
        )
    raise ApplicationError("PAGE_NOT_FOUND", f"Page image {page_number} not found for document.")


@router.post("/{document_id}/process", status_code=202, response_model=ProcessingRunResponse,
             responses={code: {"model": ErrorResponse} for code in (404, 409, 503)})
def process_document(document_id: UUID, processing: Processing, reprocess: bool = False) -> ProcessingRunResponse:
    return ProcessingRunResponse.model_validate(processing.schedule(document_id, reprocess=reprocess))


@router.get("/{document_id}/results", response_model=DocumentResultsResponse,
            responses={404: {"model": ErrorResponse}})
def document_results(document_id: UUID, processing: Processing) -> DocumentResultsResponse:
    return DocumentResultsResponse.model_validate(processing.results(document_id))


@router.put("/{document_id}/review", response_model=ReviewResponse,
            responses={code: {"model": ErrorResponse} for code in (404, 409, 422)})
def submit_review(
    document_id: UUID,
    payload: SubmitReviewRequest,
    review: Review,
) -> ReviewResponse:
    fields = tuple(
        ReviewedField(
            field_name=f.field_name,
            original_value=f.original_value,
            corrected_value=f.corrected_value,
            original_confidence=f.original_confidence,
            is_modified=f.is_modified,
        )
        for f in payload.fields
    )
    command = ReviewDocumentCommand(
        document_id=document_id,
        expected_revision=payload.expected_revision,
        status=payload.status,
        reviewer_id=payload.reviewer_id,
        document_type=payload.document_type,
        fields=fields,
        rejection_reason=payload.rejection_reason,
        notes=payload.notes,
    )
    _, record = review.submit_review(command)
    return ReviewResponse.model_validate(record)


@router.get("/{document_id}/review", response_model=ReviewResponse,
            responses={404: {"model": ErrorResponse}})
def get_latest_review(document_id: UUID, review: Review) -> ReviewResponse:
    record = review.get_latest(document_id)
    if record is None:
        raise ApplicationError("DOCUMENT_NOT_FOUND", "No review found for document.")
    return ReviewResponse.model_validate(record)


@router.get("/{document_id}/reviews", response_model=list[ReviewResponse])
def list_document_reviews(document_id: UUID, review: Review) -> list[ReviewResponse]:
    records = review.list_history(document_id)
    return [ReviewResponse.model_validate(r) for r in records]
