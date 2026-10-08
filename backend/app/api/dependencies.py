from collections.abc import Iterator

from fastapi import Request

from app.application.documents import DocumentService
from app.infrastructure.db.repository import SQLDocumentRepository
from app.infrastructure.validation import UploadValidator
from app.application.process_document import ProcessingService
from app.infrastructure.db.processing import SQLProcessingRepository


from app.application.review_document import ReviewDocumentService
from app.infrastructure.db.review import SQLReviewRepository


def document_service(request: Request) -> Iterator[DocumentService]:
    settings = request.app.state.settings
    with request.app.state.sessions() as session:
        yield DocumentService(
            SQLDocumentRepository(session), request.app.state.storage,
            UploadValidator(settings.max_pdf_pages, settings.max_image_pixels),
            settings.max_upload_bytes,
        )


def processing_service(request: Request) -> Iterator[ProcessingService]:
    with request.app.state.sessions() as session:
        yield ProcessingService(SQLProcessingRepository(session), request.app.state.dispatcher,
                                request.app.state.pipeline_spec)


def review_service(request: Request) -> Iterator[ReviewDocumentService]:
    with request.app.state.sessions() as session:
        yield ReviewDocumentService(SQLReviewRepository(session))
