"""Opt-in, real CPU OCR. No ordinary test imports Paddle or downloads models."""
from io import BytesIO
import os
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont
import pytest

from app.core.config import Settings
from app.domain.ocr import OCRContext, PreparedPage
from app.infrastructure.ocr.paddle import PaddleOCRProvider
from app.infrastructure.storage.local import LocalDocumentStorage


@pytest.mark.real_ocr
@pytest.mark.skipif(os.environ.get("RUN_REAL_OCR") != "1", reason="Set RUN_REAL_OCR=1 for real model execution")
def test_real_paddle_cpu_adapter(tmp_path):
    image = Image.new("RGB", (1000, 260), "white")
    ImageDraw.Draw(image).text((40, 50), "DOCUMIND TEST 123", fill="black", font=ImageFont.load_default(size=44))
    storage = LocalDocumentStorage(tmp_path)
    png = BytesIO()
    image.save(png, "PNG")
    png.seek(0)
    reference = storage.store(png)
    page = PreparedPage(1, image.width, image.height, image.tobytes(), reference)
    context = OCRContext(uuid4(), uuid4(), "adapter-smoke-v1")
    provider = PaddleOCRProvider(storage, Settings().ocr_cache_dir)
    result = provider.recognize([page], context)
    assert "DOCUMIND" in result.pages[0].text.upper()
    assert result.pages[0].number == 1
    assert result.provider == "PaddleOCR" and result.provider_version and result.engine_version
    assert result.model_version.startswith("sha256:")
    import json
    with storage.open(result.raw_output_reference) as raw:
        source = json.load(raw)["pages"][0]["output"]["res"]
    assert [line.confidence for line in result.pages[0].lines] == source["rec_scores"]
    for line in result.pages[0].lines:
        assert 0 <= line.confidence <= 1
        assert 0 <= line.box.x <= line.box.x + line.box.width <= 1
        assert 0 <= line.box.y <= line.box.y + line.box.height <= 1
