"""Bounded, one-page-at-a-time rendering; PDFium calls are serialized."""
from collections.abc import Iterator
from contextlib import closing, contextmanager
from hashlib import sha256
from io import BytesIO
from math import ceil, isfinite
from threading import Lock
from typing import BinaryIO

from PIL import Image, ImageOps
import pypdfium2 as pdfium

from app.domain.documents import Document
from app.domain.ocr import PreparedPage
from app.domain.ports import DocumentStorage
from app.infrastructure.validation import UploadValidator

PDFIUM_LOCK = Lock()  # PDFium is not thread-safe, even for distinct documents.


class DocumentPagePreparer:
    def __init__(self, storage: DocumentStorage, *, max_upload_bytes: int,
                 max_pdf_pages: int, max_image_pixels: int, dpi: int = 144) -> None:
        self.storage = storage
        self.max_upload_bytes = max_upload_bytes
        self.max_image_pixels = max_image_pixels
        self.validator = UploadValidator(max_pdf_pages, max_image_pixels)
        self.dpi = dpi

    @contextmanager
    def prepare(self, stream: BinaryIO, document: Document) -> Iterator[Iterator[PreparedPage]]:
        digest, size = sha256(), 0
        stream.seek(0)
        while chunk := stream.read(64 * 1024):
            size += len(chunk)
            if size > self.max_upload_bytes:
                raise ValueError("Stored file exceeds upload limit")
            digest.update(chunk)
        if size != document.size_bytes or digest.hexdigest() != document.checksum:
            raise ValueError("Stored document integrity check failed")
        stream.seek(0)
        if self.validator(stream) != (document.media_type, document.page_count):
            raise ValueError("Stored document metadata mismatch")
        stream.seek(0)
        keys: list[str] = []
        pages = self._pages(stream, document, keys)
        try:
            yield pages
        except BaseException:
            # Only newly created artifacts are removed, never the original file.
            for key in keys:
                self.storage.delete(key)
            raise
        finally:
            pages.close()

    def _page(self, image: Image.Image, number: int, keys: list[str]) -> PreparedPage:
        if image.width * image.height > self.max_image_pixels:
            raise ValueError("Rendered page exceeds pixel limit")
        with image.convert("RGB") as rgb:
            output = BytesIO()
            rgb.save(output, format="PNG")
            output.seek(0)
            key = self.storage.store(output)
            keys.append(key)
            return PreparedPage(number, rgb.width, rgb.height, rgb.tobytes(), key)

    def _pages(self, stream: BinaryIO, document: Document, keys: list[str]) -> Iterator[PreparedPage]:
        if document.media_type != "application/pdf":
            with Image.open(stream) as original, ImageOps.exif_transpose(original) as oriented:
                yield self._page(oriented, 1, keys)
            return
        with PDFIUM_LOCK, pdfium.PdfDocument(stream) as pdf:
            if len(pdf) != document.page_count:
                raise ValueError("Rendered PDF page count mismatch")
            scale = self.dpi / 72
            for index in range(len(pdf)):
                with closing(pdf[index]) as page:
                    width, height = page.get_size()
                    if not all(isfinite(v) and v > 0 for v in (width, height)):
                        raise ValueError("Invalid PDF page dimensions")
                    if ceil(width * scale) * ceil(height * scale) > self.max_image_pixels:
                        raise ValueError("PDF render exceeds pixel limit")
                    with closing(page.render(scale=scale)) as bitmap, bitmap.to_pil() as image:
                        prepared = self._page(image, index + 1, keys)
                yield prepared
