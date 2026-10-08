"""PaddleOCR 3.x adapter. Library polygons and raw output stay here."""
from collections.abc import Iterable, Sequence
from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import version
from io import BytesIO
import json
from math import isfinite
import os
from pathlib import Path
from threading import Lock
from time import perf_counter

from app.domain.ocr import BoundingBox, OCRContext, OCRLine, OCRPage, OCRResult, PreparedPage
from app.domain.ports import DocumentStorage
from app.domain.processing import PipelineSpec

DETECTION_MODEL = "PP-OCRv5_mobile_det"
RECOGNITION_MODEL = "en_PP-OCRv5_mobile_rec"


def pipeline_spec(dpi: int, cpu_threads: int) -> PipelineSpec:
    config = {
        "provider": "PaddleOCR", "provider_version": version("paddleocr"),
        "engine_version": version("paddlepaddle"), "paddlex_version": version("paddlex"),
        "numpy_version": version("numpy"), "opencv_version": version("opencv-contrib-python"),
        "renderer": "pypdfium2", "renderer_version": version("pypdfium2"),
        "pillow_version": version("pillow"), "pdf_dpi": dpi,
        "detection_model": DETECTION_MODEL, "recognition_model": RECOGNITION_MODEL,
        "device": "cpu", "cpu_threads": cpu_threads, "enable_mkldnn": False,
        "orientation_classification": False, "unwarping": False, "textline_orientation": False,
        "exif_transpose": True, "text_rec_score_thresh": 0.0,
        "text_det_limit_side_len": 960, "text_det_limit_type": "max",
    }
    fingerprint = sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    return PipelineSpec("ocr-v1", fingerprint, config)


def normalize_polygon(polygon: Sequence[Sequence[float]], width: int, height: int) -> BoundingBox:
    if width < 1 or height < 1 or len(polygon) < 3:
        raise ValueError("Invalid OCR polygon or page dimensions")
    points = [(float(p[0]), float(p[1])) for p in polygon]
    if not all(isfinite(v) for p in points for v in p):
        raise ValueError("Non-finite OCR polygon")
    # Provider polygons may overshoot the image edge by a rounding pixel.
    x1 = max(0.0, min(1.0, min(p[0] for p in points) / width))
    y1 = max(0.0, min(1.0, min(p[1] for p in points) / height))
    x2 = max(0.0, min(1.0, max(p[0] for p in points) / width))
    y2 = max(0.0, min(1.0, max(p[1] for p in points) / height))
    return BoundingBox(x1, y1, x2 - x1, y2 - y1)


class PaddleOCRProvider:
    def __init__(self, storage: DocumentStorage, cache_dir: Path, cpu_threads: int = 2) -> None:
        self.storage = storage
        self.cache_dir = cache_dir
        self.cpu_threads = cpu_threads
        self._engine = None
        self._model_version = ""
        self._lock = Lock()

    def _load(self) -> None:
        if self._engine is not None:
            return
        # Set before importing PaddleX; downloads are lazy and outside test paths.
        os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(self.cache_dir))
        os.environ.setdefault("HF_HOME", str(self.cache_dir / "huggingface"))
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        from paddleocr import PaddleOCR

        engine = PaddleOCR(
            text_detection_model_name=DETECTION_MODEL,
            text_recognition_model_name=RECOGNITION_MODEL,
            use_doc_orientation_classify=False, use_doc_unwarping=False,
            use_textline_orientation=False, device="cpu", enable_mkldnn=False,
            cpu_threads=self.cpu_threads,
        )
        # Record the actual model artifacts, not an invented model release number.
        cache = Path(os.environ["PADDLE_PDX_CACHE_HOME"]) / "official_models"
        digest = sha256()
        for name in (DETECTION_MODEL, RECOGNITION_MODEL):
            for filename in ("inference.json", "inference.pdiparams", "inference.yml"):
                digest.update(f"{name}/{filename}".encode())
                with (cache / name / filename).open("rb") as file:
                    while chunk := file.read(1024 * 1024):
                        digest.update(chunk)
        self._model_version = "sha256:" + digest.hexdigest()
        self._engine = engine

    def recognize(self, pages: Iterable[PreparedPage], context: OCRContext) -> OCRResult:
        import cv2
        import numpy as np

        with self._lock:
            self._load()
            normalized: list[OCRPage] = []
            raw_pages: list[dict] = []
            for page in pages:
                rgb = np.frombuffer(page.rgb, dtype=np.uint8).reshape(page.height, page.width, 3)
                bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                start = perf_counter()
                predictions = list(self._engine.predict(
                    bgr, text_rec_score_thresh=0.0,
                    text_det_limit_side_len=960, text_det_limit_type="max",
                ))
                seconds = perf_counter() - start
                if len(predictions) != 1:
                    raise ValueError("Expected exactly one OCR prediction per page")
                prediction = predictions[0]
                texts, scores, polygons = (prediction[k] for k in ("rec_texts", "rec_scores", "rec_polys"))
                if not len(texts) == len(scores) == len(polygons):
                    raise ValueError("Inconsistent OCR output lengths")
                # Preserve provider reading order; never fabricate word-level boxes
                # or split a line score into artificial token confidence values.
                lines = tuple(OCRLine(i + 1, str(t), float(s), normalize_polygon(p, page.width, page.height))
                              for i, (t, s, p) in enumerate(zip(texts, scores, polygons, strict=True)))
                normalized.append(OCRPage(page.number, page.width, page.height,
                                          "\n".join(line.text for line in lines), lines, seconds,
                                          page.image_reference))
                # Paddle's JSON representation omits image arrays. It is stored
                # privately through storage; only an opaque reference crosses out.
                raw = prediction.json
                raw_pages.append({"page_number": page.number, "output": raw})
            raw_bytes = json.dumps({"context": asdict(context), "pages": raw_pages},
                                   default=str, ensure_ascii=False).encode("utf-8")
            reference = self.storage.store(BytesIO(raw_bytes))
            try:
                return OCRResult(
                    context.document_id, context.run_id, "PaddleOCR", version("paddleocr"),
                    version("paddlepaddle"), DETECTION_MODEL, RECOGNITION_MODEL, self._model_version,
                    "PaddleOCR rec_scores (line recognition confidence)", tuple(normalized), reference,
                )
            except Exception:
                self.storage.delete(reference)
                raise
