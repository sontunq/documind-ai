from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import FastAPI, Request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from app.api.errors import register_error_handlers
from app.api.routes import router
from app.api.upload_limit import UploadLimitMiddleware
from app.core.config import Settings
from app.core.observability import CorrelationIdMiddleware
from app.infrastructure.storage.local import LocalDocumentStorage
from app.application.process_document import ProcessDocument
from app.infrastructure.db.processing import SQLProcessingRepository
from app.infrastructure.imaging.pages import DocumentPagePreparer
from app.infrastructure.jobs.in_process import InProcessDispatcher
from app.infrastructure.ocr.paddle import PaddleOCRProvider, pipeline_spec
from app.infrastructure.classification.model import SklearnDocumentClassifier, classification_pipeline_spec
from app.infrastructure.extraction.rule_based import RuleBasedFieldExtractor



def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    # Engine creation is lazy: /health never connects to the database.
    engine = create_engine(settings.database_url.get_secret_value(), pool_pre_ping=True,
                           connect_args={"connect_timeout": 5})

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        await run_in_threadpool(app.state.dispatcher.close)
        engine.dispose()

    app = FastAPI(title="DocuMind AI", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = engine
    app.state.sessions = sessionmaker(engine, expire_on_commit=False)
    app.state.storage = LocalDocumentStorage(settings.document_storage_dir)
    app.state.ocr_provider = PaddleOCRProvider(app.state.storage, settings.ocr_cache_dir, settings.ocr_cpu_threads)
    app.state.classifier = SklearnDocumentClassifier(settings.classification_model_path)
    app.state.extractor = RuleBasedFieldExtractor()
    app.state.pipeline_spec = classification_pipeline_spec(
        pipeline_spec(settings.ocr_pdf_dpi, settings.ocr_cpu_threads), app.state.classifier)
    app.state.page_preparer = DocumentPagePreparer(
        app.state.storage, max_upload_bytes=settings.max_upload_bytes,
        max_pdf_pages=settings.max_pdf_pages, max_image_pixels=settings.max_image_pixels,
        dpi=settings.ocr_pdf_dpi,
    )

    def execute(run_id: UUID) -> None:
        # Each job owns a session, never the HTTP request's session.
        with app.state.sessions() as session:
            ProcessDocument(SQLProcessingRepository(session), app.state.storage,
                            app.state.page_preparer, app.state.ocr_provider, app.state.classifier,
                            app.state.extractor).execute(run_id)

    app.state.dispatcher = InProcessDispatcher(execute, settings.ocr_queue_capacity)
    # A small envelope allowance is separate from the exact file byte limit.
    app.add_middleware(UploadLimitMiddleware, max_bytes=settings.max_upload_bytes + 64 * 1024)
    app.add_middleware(CorrelationIdMiddleware)
    register_error_handlers(app)
    app.include_router(router)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/live", tags=["health"])
    def health_live() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready", tags=["health"])
    def health_ready(request: Request) -> JSONResponse:
        try:
            with request.app.state.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return JSONResponse(status_code=200, content={"status": "ready", "database": "connected"})
        except Exception:
            return JSONResponse(status_code=503, content={"status": "unavailable", "database": "disconnected"})

    return app


app = create_app()
