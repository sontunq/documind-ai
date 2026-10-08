from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

from app.domain.classification import DocumentType
from app.infrastructure.classification.text import normalize_text

LABELS = [label.value for label in DocumentType]


def fingerprint(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def load_dataset(path: Path) -> dict:
    dataset = json.loads(path.read_text(encoding="utf-8"))
    validate_dataset(dataset)
    return dataset


def validate_dataset(dataset: dict) -> None:
    if not dataset.get("dataset_version") or not dataset.get("samples"):
        raise ValueError("A version and samples are required")
    ids, logical_splits, text_splits = set(), {}, {}
    for sample in dataset["samples"]:
        required = ("id", "label", "logical_document_id", "source", "license", "split",
                    "dataset_version", "text_reference", "text")
        if any(not isinstance(sample.get(k), str) or not sample[k].strip() for k in required):
            raise ValueError("Incomplete sample manifest")
        if sample["id"] in ids:
            raise ValueError("Duplicate sample ID")
        ids.add(sample["id"])
        if sample["label"] not in LABELS or sample["split"] not in {"train", "validation", "test"}:
            raise ValueError("Invalid label or split")
        if sample["dataset_version"] != dataset["dataset_version"]:
            raise ValueError("Dataset version mismatch")
        # Catch exact/formatting duplicates, including variants differing only in
        # numbers. Logical IDs additionally group human-identified variants.
        canonical = " ".join(re.findall(r"[a-z]+", normalize_text(sample["text"])))
        if not canonical:
            raise ValueError("Dataset sample has no English words")
        for key, registry in ((sample["logical_document_id"], logical_splits), (canonical, text_splits)):
            if key in registry and registry[key] != sample["split"]:
                raise ValueError("Train/validation/test leakage")
            registry[key] = sample["split"]
    for split in ("train", "test"):
        if set(distribution(dataset, split)) != set(LABELS):
            raise ValueError("Train and test must each contain all three classes")


def distribution(dataset: dict, split: str) -> dict[str, int]:
    return dict(Counter(s["label"] for s in dataset["samples"] if s["split"] == split))
