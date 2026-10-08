from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from app.application.errors import ApplicationError

STATUS_CODES = {
    "UPLOAD_TOO_LARGE": 413, "IMAGE_TOO_LARGE": 413, "TOO_MANY_PAGES": 413,
    "UNSUPPORTED_FORMAT": 415, "EMPTY_UPLOAD": 422, "MALFORMED_FILE": 422,
    "ENCRYPTED_PDF": 422, "INVALID_REQUEST": 422, "DOCUMENT_NOT_FOUND": 404,
    "STORAGE_UNAVAILABLE": 503, "PERSISTENCE_UNAVAILABLE": 503,
    "UPLOAD_CLEANUP_FAILED": 500,
    "INVALID_PROCESSING_TRANSITION": 409, "SCHEDULING_FAILED": 503,
    "STALE_REVISION_CONFLICT": 409, "INVALID_REVIEW_STATE": 400,
    "INVALID_REVIEW_DATA": 422, "PAGE_NOT_FOUND": 404,
}


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def application_error(request: Request, exc: ApplicationError) -> JSONResponse:
        return error_response(STATUS_CODES.get(exc.code, 500), exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(422, "INVALID_REQUEST", "Request parameters are invalid.")

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        return error_response(503, "PERSISTENCE_UNAVAILABLE", "Document metadata is unavailable.")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        if exc.status_code == 413:
            return error_response(413, "UPLOAD_TOO_LARGE", "Request exceeds the configured size limit.")
        return error_response(exc.status_code, "INVALID_REQUEST", "The requested operation could not be completed.")

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        return error_response(500, "INTERNAL_ERROR", "An unexpected server error occurred.")
