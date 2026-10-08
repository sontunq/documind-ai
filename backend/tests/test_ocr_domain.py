from dataclasses import replace
from math import inf, nan

import pytest

from app.domain.documents import DocumentStatus as S, InvalidTransition, transition
from app.domain.ocr import BoundingBox, OCRLine, OCRPage, PreparedPage
from app.infrastructure.ocr.paddle import normalize_polygon


@pytest.mark.parametrize("value", [-0.1, 1.01, nan, inf])
def test_confidence_and_geometry_reject_invalid_values(value):
    with pytest.raises(ValueError):
        BoundingBox(value, 0, 0, 0)
    with pytest.raises(ValueError):
        OCRLine(1, "test", value, BoundingBox(0, 0, 1, 1))


def test_polygon_conversion_and_bounds():
    assert normalize_polygon([(10, 20), (70, 10), (80, 60), (0, 50)], 100, 100) == BoundingBox(0, .1, .8, .5)
    assert normalize_polygon([(-1, -1), (101, 0), (101, 102)], 100, 100) == BoundingBox(0, 0, 1, 1)
    with pytest.raises(ValueError):
        BoundingBox(.8, .2, .3, .1)
    with pytest.raises(ValueError):
        normalize_polygon([(nan, 0), (1, 1), (2, 2)], 100, 100)


@pytest.mark.parametrize("source,target", [
    (S.UPLOADED, S.QUEUED), (S.QUEUED, S.PROCESSING), (S.PROCESSING, S.COMPLETED),
    (S.PROCESSING, S.FAILED), (S.QUEUED, S.FAILED), (S.FAILED, S.QUEUED),
    (S.COMPLETED, S.QUEUED), (S.UPLOADED, S.PROCESSING),
    (S.PROCESSING, S.NEEDS_REVIEW), (S.NEEDS_REVIEW, S.QUEUED),
    (S.NEEDS_REVIEW, S.COMPLETED),
])
def test_canonical_transitions(source, target):
    assert transition(source, target) == target


@pytest.mark.parametrize("source,target", [(S.UPLOADED, S.COMPLETED), (S.PROCESSING, S.QUEUED),
                                           (S.COMPLETED, S.COMPLETED), (S.UPLOADED, S.FAILED)])
def test_invalid_transitions(source, target):
    with pytest.raises(InvalidTransition):
        transition(source, target)


def test_ordered_pages_lines_and_dimensions():
    line = OCRLine(1, "hello", 1, BoundingBox(0, 0, 1, 1))
    page = OCRPage(1, 10, 10, "hello", (line,), 0, "fixture")
    for changes in ({"number": 0}, {"width": 0}, {"text": "different"},
                    {"lines": (replace(line, order=2),)}, {"ocr_seconds": nan}):
        with pytest.raises(ValueError):
            replace(page, **changes)
    with pytest.raises(ValueError):
        PreparedPage(1, 2, 2, b"short", "fixture")
