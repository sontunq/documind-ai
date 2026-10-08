"""Normalized OCR contracts: no imaging, database, or AI library objects."""
from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite
from typing import Protocol
from uuid import UUID


def unit_interval(value: float) -> None:
    if not isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Expected a finite value between zero and one")


@dataclass(frozen=True)
class BoundingBox:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        for value in (self.x, self.y, self.width, self.height):
            unit_interval(value)
        if self.x + self.width > 1 + 1e-9 or self.y + self.height > 1 + 1e-9:
            raise ValueError("Bounding box extends beyond the page")


@dataclass(frozen=True)
class OCRLine:
    order: int
    text: str
    confidence: float
    box: BoundingBox

    def __post_init__(self) -> None:
        if self.order < 1:
            raise ValueError("Line order is one-based")
        unit_interval(self.confidence)


@dataclass(frozen=True)
class PreparedPage:
    number: int
    width: int
    height: int
    rgb: bytes
    image_reference: str

    def __post_init__(self) -> None:
        if self.number < 1 or self.width < 1 or self.height < 1:
            raise ValueError("Invalid page dimensions or number")
        if len(self.rgb) != self.width * self.height * 3:
            raise ValueError("Expected packed RGB bytes")


@dataclass(frozen=True)
class OCRPage:
    number: int
    width: int
    height: int
    text: str
    lines: tuple[OCRLine, ...]
    ocr_seconds: float
    image_reference: str

    def __post_init__(self) -> None:
        if self.number < 1 or self.width < 1 or self.height < 1:
            raise ValueError("Invalid page dimensions or number")
        if [line.order for line in self.lines] != list(range(1, len(self.lines) + 1)):
            raise ValueError("Lines must be ordered consecutively")
        if self.text != "\n".join(line.text for line in self.lines):
            raise ValueError("Page text must match ordered lines")
        if not isfinite(self.ocr_seconds) or self.ocr_seconds < 0:
            raise ValueError("Invalid OCR duration")


@dataclass(frozen=True)
class OCRContext:
    document_id: UUID
    run_id: UUID
    pipeline_version: str


@dataclass(frozen=True)
class OCRResult:
    document_id: UUID
    run_id: UUID
    provider: str
    provider_version: str
    engine_version: str
    detection_model: str
    recognition_model: str
    model_version: str
    confidence_source: str
    pages: tuple[OCRPage, ...]
    raw_output_reference: str

    def __post_init__(self) -> None:
        if not self.pages or [p.number for p in self.pages] != list(range(1, len(self.pages) + 1)):
            raise ValueError("OCR pages must be consecutive and one-based")
        if not all((self.provider, self.provider_version, self.engine_version,
                    self.detection_model, self.recognition_model, self.model_version,
                    self.confidence_source, self.raw_output_reference)):
            raise ValueError("OCR provenance is required")


class OCRProvider(Protocol):
    def recognize(self, pages: Iterable[PreparedPage], context: OCRContext) -> OCRResult: ...
