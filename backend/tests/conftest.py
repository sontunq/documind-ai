import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter

from app.api.dependencies import document_service
from app.application.documents import DocumentService
from app.core.config import Settings
from app.infrastructure.storage.local import LocalDocumentStorage
from app.infrastructure.validation import UploadValidator
from app.main import create_app


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    # Windows sandbox/IDE processes can inherit the same USERNAME and TEMP
    # while running as different security principals. Never share pytest's
    # predictable pytest-of-<user> root (or its restrictive ACLs) between them.
    run_directory = TemporaryDirectory(prefix="documind-pytest-")
    config.add_cleanup(run_directory.cleanup)
    run_root = Path(run_directory.name)
    if config.option.basetemp is None:
        # pytest may delete basetemp: give it only a fresh child of our own dir.
        config.option.basetemp = str(run_root / "tmp")
    # Configure before pytest's cache plugin. Explicit ini/-o settings still win.
    config.inicfg.setdefault("cache_dir", str(run_root / "cache"))


class MemoryRepository:
    def __init__(self):
        self.documents = {}

    def create(self, document):
        self.documents[document.id] = document

    def get(self, document_id):
        return self.documents.get(document_id)

    def list(self, *, limit, offset):
        items = sorted(self.documents.values(), key=lambda d: (d.created_at, d.id), reverse=True)
        return items[offset:offset + limit]


def make_pdf(pages=1, password=None):
    output = BytesIO()
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=100, height=100)
    if password:
        writer.encrypt(password)
    writer.write(output)
    return output.getvalue()


def make_image(format="PNG", size=(16, 16)):
    output = BytesIO()
    Image.new("RGB", size, "white").save(output, format=format)
    return output.getvalue()


@pytest.fixture
def pdf_bytes():
    return make_pdf()


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, document_storage_dir=tmp_path / "uploads",
                    database_url="postgresql+psycopg://localhost:1/unavailable",
                    max_upload_bytes=4096, max_pdf_pages=2, max_image_pixels=10000,
                    ocr_auto_process=False)


@pytest.fixture
def service(settings):
    return DocumentService(MemoryRepository(), LocalDocumentStorage(settings.document_storage_dir),
                           UploadValidator(settings.max_pdf_pages, settings.max_image_pixels),
                           settings.max_upload_bytes)


@pytest.fixture
def client(settings, service):
    app = create_app(settings)
    app.dependency_overrides[document_service] = lambda: service
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
