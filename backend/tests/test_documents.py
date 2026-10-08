from dataclasses import replace
from datetime import datetime
from io import BytesIO
from uuid import UUID, uuid4

import pytest

from app.application.documents import safe_filename
from app.application.errors import ApplicationError
from app.domain.documents import DocumentStatus


def test_create_get_list(service, pdf_bytes):
    document = service.create(BytesIO(pdf_bytes), "invoice.pdf")
    assert isinstance(document.id, UUID)
    assert document.status is DocumentStatus.UPLOADED
    assert document.page_count == 1
    assert document.size_bytes == len(pdf_bytes)
    assert service.get(document.id) == document
    assert service.list() == [document]
    assert service.list(offset=1) == []
    assert document.created_at == document.updated_at


@pytest.mark.parametrize("changes", [
    {"size_bytes": 0}, {"checksum": "wrong"}, {"storage_key": "../private"},
    {"original_filename": "../private"}, {"original_filename": ""},
    {"status": "PROCESSING"}, {"page_count": 0}, {"media_type": "text/plain"},
    {"created_at": datetime(2020, 1, 1)}, {"id": "not-a-uuid"},
])
def test_document_invariants(service, pdf_bytes, changes):
    document = service.create(BytesIO(pdf_bytes), "test.pdf")
    with pytest.raises(ValueError):
        replace(document, **changes)


def test_unknown_document(service):
    with pytest.raises(ApplicationError, match="Document not found") as error:
        service.get(uuid4())
    assert error.value.code == "DOCUMENT_NOT_FOUND"


@pytest.mark.parametrize("name, expected", [
    ("C:\\private\\invoice.pdf", "invoice.pdf"), ("../../invoice.pdf", "invoice.pdf"),
    ("bad\x00\nname.pdf", "badname.pdf"), ("..", "document"), (None, "document"),
])
def test_filename_is_display_only(name, expected):
    assert safe_filename(name) == expected


def test_commit_failure_removes_binary(service, settings, pdf_bytes, monkeypatch):
    def fail(document):
        raise RuntimeError("private database password")
    monkeypatch.setattr(service.repository, "create", fail)
    with pytest.raises(ApplicationError) as error:
        service.create(BytesIO(pdf_bytes), "test.pdf")
    assert error.value.code == "PERSISTENCE_UNAVAILABLE"
    assert list(settings.document_storage_dir.iterdir()) == []
    assert service.list() == []


def test_cleanup_failure_is_not_hidden(service, pdf_bytes, monkeypatch):
    def fail(*args):
        raise OSError("private path")
    monkeypatch.setattr(service.repository, "create", fail)
    monkeypatch.setattr(service.storage, "delete", fail)
    with pytest.raises(ApplicationError) as error:
        service.create(BytesIO(pdf_bytes), "test.pdf")
    assert error.value.code == "UPLOAD_CLEANUP_FAILED"


def test_storage_failure_does_not_create_metadata(service, pdf_bytes, monkeypatch):
    def fail(*args):
        raise OSError("disk full")
    monkeypatch.setattr(service.storage, "store", fail)
    with pytest.raises(ApplicationError) as error:
        service.create(BytesIO(pdf_bytes), "test.pdf")
    assert error.value.code == "STORAGE_UNAVAILABLE"
    assert service.list() == []
