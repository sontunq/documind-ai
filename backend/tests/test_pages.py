from dataclasses import replace
from io import BytesIO

from PIL import Image
from pypdf import PdfWriter
import pytest

from app.infrastructure.imaging.pages import DocumentPagePreparer
from app.application.errors import ApplicationError
from conftest import make_image


def preparer(service, **changes):
    options = dict(max_upload_bytes=4096, max_pdf_pages=2, max_image_pixels=10000, dpi=72)
    return DocumentPagePreparer(service.storage, **(options | changes))


def test_pdf_page_order_dimensions_and_artifacts(service):
    pdf = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=80, height=90)
    writer.add_blank_page(width=90, height=80)
    writer.write(pdf)
    doc = service.create(pdf, "ordered.pdf")
    with service.storage.open(doc.storage_key) as source, preparer(service).prepare(source, doc) as pages:
        result = list(pages)
    assert [(p.number, p.width, p.height) for p in result] == [(1, 80, 90), (2, 90, 80)]
    for page in result:
        with service.storage.open(page.image_reference) as image, Image.open(image) as rendered:
            assert rendered.size == (page.width, page.height)
            assert rendered.getpixel((20, 20)) == (255, 255, 255)


def test_exif_orientation(service):
    stream = BytesIO()
    image = Image.new("RGB", (20, 40), "white")
    exif = Image.Exif()
    exif[274] = 6
    image.save(stream, format="JPEG", exif=exif)
    doc = service.create(stream, "oriented.jpg")
    with service.storage.open(doc.storage_key) as source, preparer(service).prepare(source, doc) as pages:
        page = next(pages)
        assert (page.width, page.height) == (40, 20)


@pytest.mark.parametrize("limits", [
    {"max_image_pixels": 99}, {"max_upload_bytes": 10},
])
def test_processing_rechecks_resource_limits(service, limits):
    doc = service.create(BytesIO(make_image(size=(10, 10))), "test.png")
    with service.storage.open(doc.storage_key) as source, pytest.raises((ValueError, ApplicationError)):
        with preparer(service, **limits).prepare(source, doc) as pages:
            list(pages)


def test_render_limit_before_allocation_and_page_limit(service):
    stream = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.add_blank_page(width=100, height=100)
    writer.write(stream)
    doc = service.create(stream, "test.pdf")
    for limits in ({"max_image_pixels": 9999}, {"max_pdf_pages": 1}):
        with service.storage.open(doc.storage_key) as source, pytest.raises((ValueError, ApplicationError)):
            with preparer(service, **limits).prepare(source, doc) as pages:
                list(pages)


def test_integrity_check_and_failed_run_artifact_cleanup(service):
    data = make_image()
    doc = service.create(BytesIO(data), "test.png")
    with service.storage.open(doc.storage_key) as source, pytest.raises(ValueError, match="integrity"):
        with preparer(service).prepare(source, replace(doc, checksum="a" * 64)):
            pass
    generated = None
    with service.storage.open(doc.storage_key) as source, pytest.raises(RuntimeError):
        with preparer(service).prepare(source, doc) as pages:
            generated = next(pages).image_reference
            raise RuntimeError("simulated downstream failure")
    with pytest.raises(FileNotFoundError):
        service.storage.open(generated)
    with service.storage.open(doc.storage_key) as source:
        assert source.read() == data
