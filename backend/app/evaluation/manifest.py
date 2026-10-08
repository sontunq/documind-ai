"""Evaluation manifest loading, validation, and leakage detection."""
import json
from pathlib import Path
import re
from typing import Any

VALID_DOC_TYPES = {"invoice", "contract", "form"}


def _normalize_for_leakage(text: str) -> str:
    """Normalize text by lowercasing, stripping punctuation and digits to detect overlap."""
    t = text.lower()
    t = re.sub(r"\d+", "0", t)
    t = re.sub(r"[^\w\s]", " ", t)
    return " ".join(t.split())


def validate_evaluation_manifest(data: dict[str, Any]) -> None:
    """Validate the schema and integrity of an evaluation manifest."""
    if not isinstance(data, dict):
        raise ValueError("Evaluation manifest must be a JSON object")

    if not data.get("dataset_version"):
        raise ValueError("Evaluation manifest must specify 'dataset_version'")

    tracks = data.get("evaluation_tracks")
    if not isinstance(tracks, list) or not tracks:
        raise ValueError("Evaluation manifest must contain a non-empty 'evaluation_tracks' list")

    sample_ids = set()

    # OCR samples validation
    if "ocr" in tracks:
        ocr_samples = data.get("ocr_samples")
        if not isinstance(ocr_samples, list) or not ocr_samples:
            raise ValueError("Manifest specifies 'ocr' track but 'ocr_samples' is missing or empty")
        for idx, sample in enumerate(ocr_samples):
            sid = sample.get("id")
            if not sid or not isinstance(sid, str):
                raise ValueError(f"OCR sample at index {idx} missing valid 'id'")
            if sid in sample_ids:
                raise ValueError(f"Duplicate sample ID detected: '{sid}'")
            sample_ids.add(sid)
            if "reference_text" not in sample or not isinstance(sample["reference_text"], str):
                raise ValueError(f"OCR sample '{sid}' missing valid 'reference_text'")
            if "hypothesis_text" not in sample or not isinstance(sample["hypothesis_text"], str):
                raise ValueError(f"OCR sample '{sid}' missing valid 'hypothesis_text'")

    # Classification samples validation
    if "classification" in tracks:
        cls_samples = data.get("classification_samples")
        if not isinstance(cls_samples, list) or not cls_samples:
            raise ValueError("Manifest specifies 'classification' track but 'classification_samples' is missing or empty")
        for idx, sample in enumerate(cls_samples):
            sid = sample.get("id")
            if not sid or not isinstance(sid, str):
                raise ValueError(f"Classification sample at index {idx} missing valid 'id'")
            if sid in sample_ids:
                raise ValueError(f"Duplicate sample ID detected: '{sid}'")
            sample_ids.add(sid)
            lbl = sample.get("label")
            if lbl not in VALID_DOC_TYPES:
                raise ValueError(f"Classification sample '{sid}' has unsupported label '{lbl}'")
            txt = sample.get("text")
            if not txt or not isinstance(txt, str) or not txt.strip():
                raise ValueError(f"Classification sample '{sid}' has missing or empty 'text'")

    # Extraction samples validation
    if "extraction" in tracks:
        ext_samples = data.get("extraction_samples")
        if not isinstance(ext_samples, list) or not ext_samples:
            raise ValueError("Manifest specifies 'extraction' track but 'extraction_samples' is missing or empty")
        for idx, sample in enumerate(ext_samples):
            sid = sample.get("id")
            if not sid or not isinstance(sid, str):
                raise ValueError(f"Extraction sample at index {idx} missing valid 'id'")
            if sid in sample_ids:
                raise ValueError(f"Duplicate sample ID detected: '{sid}'")
            sample_ids.add(sid)
            dtype = sample.get("document_type")
            if dtype not in VALID_DOC_TYPES:
                raise ValueError(f"Extraction sample '{sid}' has unsupported document_type '{dtype}'")
            gt = sample.get("ground_truth")
            if not isinstance(gt, dict):
                raise ValueError(f"Extraction sample '{sid}' missing 'ground_truth' dictionary")
            lines = sample.get("ocr_lines")
            if not isinstance(lines, list) or not lines:
                raise ValueError(f"Extraction sample '{sid}' missing non-empty 'ocr_lines'")


def check_data_leakage(eval_manifest: dict[str, Any], training_manifest: dict[str, Any]) -> list[str]:
    """Verify that no training data leaks into evaluation test splits."""
    violations: list[str] = []

    # Collect training IDs and normalized text from training samples
    train_samples = [
        s for s in training_manifest.get("samples", [])
        if s.get("split") == "train"
    ]
    train_ids = {s["id"] for s in train_samples if "id" in s}
    train_texts = {_normalize_for_leakage(s["text"]): s["id"] for s in train_samples if "text" in s}

    # Check classification samples in evaluation
    for s in eval_manifest.get("classification_samples", []):
        sid = s.get("id")
        if sid in train_ids:
            violations.append(f"Sample ID leakage: evaluation sample '{sid}' exists in training split")
        norm = _normalize_for_leakage(s.get("text", ""))
        if norm in train_texts:
            violations.append(
                f"Content leakage: evaluation sample '{sid}' text matches training sample '{train_texts[norm]}'"
            )

    # Check extraction samples in evaluation
    for s in eval_manifest.get("extraction_samples", []):
        sid = s.get("id")
        if sid in train_ids:
            violations.append(f"Sample ID leakage: extraction sample '{sid}' exists in training split")

    return violations


def load_evaluation_manifest(path: Path) -> dict[str, Any]:
    """Load and validate an evaluation manifest JSON file."""
    if not path.is_file():
        raise FileNotFoundError(f"Evaluation manifest file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_evaluation_manifest(data)
    return data
