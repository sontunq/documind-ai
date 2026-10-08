"""Content inspection only: no OCR, rendering, or text extraction."""

from typing import BinaryIO
import warnings

from PIL import Image
from pypdf import PdfReader

from app.application.errors import ApplicationError


class UploadValidator:
    def __init__(self, max_pdf_pages: int, max_image_pixels: int) -> None:
        self.max_pdf_pages = max_pdf_pages
        self.max_image_pixels = max_image_pixels

    def __call__(self, stream: BinaryIO) -> tuple[str, int]:
        signature = stream.read(8)
        stream.seek(0)
        if signature.startswith(b"%PDF-"):
            return self._pdf(stream)
        if signature.startswith(b"\x89PNG\r\n\x1a\n"):
            return self._image(stream, "PNG", "image/png")
        if signature.startswith(b"\xff\xd8\xff"):
            return self._image(stream, "JPEG", "image/jpeg")
        raise ApplicationError("UNSUPPORTED_FORMAT", "Only PDF, PNG, and JPEG documents are supported.")

    def _pdf(self, stream: BinaryIO) -> tuple[str, int]:
        try:
            reader = PdfReader(stream, strict=True)
            if reader.is_encrypted:
                raise ApplicationError("ENCRYPTED_PDF", "Password-protected PDFs are not supported.")
            count = len(reader.pages)
            if count > self.max_pdf_pages:
                raise ApplicationError("TOO_MANY_PAGES", "PDF exceeds the configured page limit.")
            if not count:
                raise ValueError("Empty page tree")
            for page in reader.pages:
                if float(page.mediabox.width) <= 0 or float(page.mediabox.height) <= 0:
                    raise ValueError("Invalid page size")
            return "application/pdf", count
        except ApplicationError:
            raise
        except Exception as exc:
            raise ApplicationError("MALFORMED_FILE", "The PDF could not be validated.") from exc

    def _image(self, stream: BinaryIO, expected: str, media_type: str) -> tuple[str, int]:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(stream) as image:
                    if image.format != expected:
                        raise ValueError("Signature mismatch")
                    if image.width * image.height > self.max_image_pixels:
                        raise ApplicationError("IMAGE_TOO_LARGE", "Image exceeds the configured pixel limit.")
                    if getattr(image, "n_frames", 1) != 1:
                        raise ApplicationError("UNSUPPORTED_FORMAT", "Animated images are not supported.")
                    image.verify()
                stream.seek(0)
                with Image.open(stream) as image:
                    image.load()  # Detect truncated data, not just a plausible header.
            return media_type, 1
        except ApplicationError:
            raise
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise ApplicationError("IMAGE_TOO_LARGE", "Image exceeds safe decoding limits.") from exc
        except Exception as exc:
            raise ApplicationError("MALFORMED_FILE", "The image could not be validated.") from exc
