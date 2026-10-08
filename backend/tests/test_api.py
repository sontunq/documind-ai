from hashlib import sha256
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.main import create_app
from conftest import make_image, make_pdf


def test_health_without_database(settings):
    with TestClient(create_app(settings)) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("data,media", [
    (make_pdf(), "application/pdf"), (make_image(), "image/png"),
    (make_image("JPEG"), "image/jpeg"),
], ids=["pdf", "png", "jpeg"])
def test_upload_get_list(client, data, media):
    # Wrong filename/MIME deliberately: content is authoritative.
    response = client.post("/api/v1/documents", files={"file": ("../../sample.txt", data, "text/plain")})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["original_filename"] == "sample.txt"
    assert body["media_type"] == media
    assert body["status"] == "UPLOADED"
    assert body["page_count"] == 1
    assert body["checksum"] == sha256(data).hexdigest()
    assert body["size_bytes"] == len(data)
    assert body["created_at"].endswith("Z")
    assert "storage_key" not in body
    assert client.get(f"/api/v1/documents/{body['id']}").json() == body
    assert client.get("/api/v1/documents").json() == [body]
    assert client.get("/api/v1/documents?offset=1").json() == []


@pytest.mark.parametrize("data,status,code", [
    (b"", 422, "EMPTY_UPLOAD"), (b"not a pdf", 415, "UNSUPPORTED_FORMAT"),
    (b"%PDF-1.7\nbroken", 422, "MALFORMED_FILE"),
    (b"\x89PNG\r\n\x1a\nbroken", 422, "MALFORMED_FILE"),
    (b"\xff\xd8\xffbroken", 422, "MALFORMED_FILE"),
    (b"x" * 4097, 413, "UPLOAD_TOO_LARGE"),
    (b"x" * 75000, 413, "UPLOAD_TOO_LARGE"),
    (make_pdf(3), 413, "TOO_MANY_PAGES"),
    (make_pdf(password="test-only"), 422, "ENCRYPTED_PDF"),
    (make_image(size=(101, 101)), 413, "IMAGE_TOO_LARGE"),
    (make_image("JPEG")[:-20], 422, "MALFORMED_FILE"),
], ids=["empty", "unsupported", "bad-pdf", "bad-png", "bad-jpeg", "file-limit",
        "request-limit", "page-limit", "encrypted", "pixel-limit", "truncated-jpeg"])
def test_invalid_uploads_leave_no_data(client, service, settings, data, status, code):
    response = client.post("/api/v1/documents", files={"file": ("safe.pdf", data, "application/pdf")})
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code
    assert service.list() == []
    assert not settings.document_storage_dir.exists()


def test_unknown_and_invalid_id(client):
    assert client.get(f"/api/v1/documents/{uuid4()}").json() == {
        "error": {"code": "DOCUMENT_NOT_FOUND", "message": "Document not found."}}
    assert client.get(f"/api/v1/documents/{uuid4()}").status_code == 404
    assert client.get("/api/v1/documents/invalid").status_code == 422
    assert client.get("/api/v1/documents?limit=0").status_code == 422
    assert client.get("/api/v1/documents?offset=-1").status_code == 422


def test_invalid_multipart(client, pdf_bytes):
    assert client.post("/api/v1/documents").status_code == 422
    response = client.post("/api/v1/documents", files=[
        ("file", ("one.pdf", pdf_bytes)), ("file", ("two.pdf", pdf_bytes))])
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_failure_response_is_safe_and_cleans_storage(client, service, settings, pdf_bytes, monkeypatch):
    def fail(document):
        raise RuntimeError("SECRET database password C:/private/path")
    monkeypatch.setattr(service.repository, "create", fail)
    response = client.post("/api/v1/documents", files={"file": ("file.pdf", pdf_bytes)})
    assert response.status_code == 503
    assert "SECRET" not in response.text
    assert "private" not in response.text
    assert list(settings.document_storage_dir.iterdir()) == []


def test_chunked_upload_limit(client):
    boundary = "testboundary"
    def chunks():
        yield f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="a.pdf"\r\n\r\n'.encode()
        for _ in range(80):
            yield b"x" * 1024
        yield f"\r\n--{boundary}--\r\n".encode()
    response = client.post("/api/v1/documents", content=chunks(),
                           headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    assert response.status_code == 413, response.text
    assert response.json()["error"]["code"] == "UPLOAD_TOO_LARGE"


def test_get_document_file(client, pdf_bytes):
    upload_res = client.post("/api/v1/documents", files={"file": ("sample.pdf", pdf_bytes)})
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    file_res = client.get(f"/api/v1/documents/{doc_id}/file")
    assert file_res.status_code == 200
    assert file_res.content == pdf_bytes
    assert file_res.headers["content-type"] == "application/pdf"
