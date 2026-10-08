from copy import deepcopy
from dataclasses import replace
from uuid import uuid4

import pytest

from app.core.config import ROOT
from app.domain.classification import ClassificationContext
from app.domain.ocr import BoundingBox, OCRLine, OCRPage, OCRResult
from app.infrastructure.classification.dataset import load_dataset, validate_dataset
from app.infrastructure.classification.evaluation import classification_metrics, evaluate
from app.infrastructure.classification.model import SklearnDocumentClassifier, train
from app.infrastructure.classification.text import normalize_text


def tiny_dataset():
    # Independent test-only data; reported model metrics never use this fixture.
    dataset = {"dataset_version": "TEST-ONLY", "samples": []}
    texts = {"invoice": ["invoice balance due tax", "invoice quantity price total", "bill subtotal payment due"],
             "contract": ["agreement party termination", "contract party obligations", "agreement signatures expiry"],
             "form": ["application name address", "registration tick email", "form checkbox contact details"]}
    for label, examples in texts.items():
        for i, text in enumerate(examples):
            id = f"{label}-{i}"
            dataset["samples"].append(dict(id=id, logical_document_id=id, label=label, source="test synthetic",
                license="CC0-1.0", split="test" if i == 2 else "train", dataset_version="TEST-ONLY",
                text_reference=id, text=text))
    return dataset


@pytest.fixture
def trained(tmp_path):
    artifact = tmp_path / "tiny.joblib"
    dataset = tiny_dataset()
    metadata = train(dataset, artifact)
    return SklearnDocumentClassifier(artifact), dataset, metadata


def test_real_model_serialization_provenance_and_shared_preprocessing(trained):
    classifier, dataset, metadata = trained
    scores = classifier.probabilities(["  INVOICE\n QUANTITY   price TOTAL ", "invoice quantity price total"])
    assert scores[0] == scores[1]
    assert normalize_text(" A-2:  B\nC ") == "a-2: b c"
    assert set(scores[0]) == {"invoice", "contract", "form"}
    assert sum(scores[0].values()) == pytest.approx(1)
    context = ClassificationContext(uuid4(), uuid4())
    line = OCRLine(1, "INVOICE quantity price total", .7, BoundingBox(0, 0, 1, 1))
    page = OCRPage(1, 10, 10, line.text, (line,), 0, "test-image")
    ocr = OCRResult(context.document_id, context.run_id, "test", "test", "test", "test", "test",
                    "test", "test", (page,), "test-raw")
    result = classifier.predict(ocr, context)
    assert result.predicted_type == "invoice"
    assert result.confidence == max(result.scores.as_dict().values())
    assert result.confidence == scores[0]["invoice"]
    assert result.model_version == metadata["model_version"]
    assert result.dataset_version == "TEST-ONLY"
    reloaded = SklearnDocumentClassifier(classifier.artifact)
    assert reloaded.probabilities([line.text]) == [result.scores.as_dict()]
    with pytest.raises(ValueError):
        classifier.predict(replace(ocr, pages=(replace(page, text="", lines=()),)), context)


def test_reproducible_versions_and_probabilities(trained, tmp_path):
    first, dataset, metadata = trained
    second_path = tmp_path / "second.joblib"
    second = train(dataset, second_path)
    assert second["model_version"] == metadata["model_version"]
    assert SklearnDocumentClassifier(second_path).probabilities(["invoice tax"]) == first.probabilities(["invoice tax"])
    changed = train(dataset, tmp_path / "threshold.joblib", .7)
    assert changed["model_version"] != metadata["model_version"]
    data = deepcopy(dataset)
    data["samples"][0]["text"] += " shipping"
    changed = train(data, tmp_path / "data.joblib")
    assert changed["model_version"] != metadata["model_version"]


def test_evaluation_uses_only_test_and_requires_named_version(trained):
    model, dataset, metadata = trained
    report = evaluate(model, dataset, metadata["model_version"])
    assert report["sample_count"] == 3
    assert {p["sample_id"] for p in report["predictions"]} == {s["id"] for s in dataset["samples"] if s["split"] == "test"}
    with pytest.raises(ValueError):
        evaluate(model, dataset, "wrong-model")
    changed = deepcopy(dataset)
    changed["samples"][-1]["text"] += " changed"
    with pytest.raises(ValueError):
        evaluate(model, changed, metadata["model_version"])


def test_hand_computed_metrics():
    actual = ["invoice", "invoice", "contract", "contract", "form", "form"]
    predicted = ["invoice", "contract", "contract", "contract", "invoice", "form"]
    metrics = classification_metrics(actual, predicted)
    assert metrics["confusion_matrix_labels"] == ["invoice", "contract", "form"]
    assert metrics["confusion_matrix"] == [[1, 1, 0], [0, 2, 0], [1, 0, 1]]
    assert metrics["accuracy"] == pytest.approx(4/6)
    assert metrics["macro_precision"] == pytest.approx((1/2 + 2/3 + 1)/3)
    assert metrics["macro_recall"] == pytest.approx((1/2 + 1 + 1/2)/3)
    assert metrics["macro_f1"] == pytest.approx((1/2 + 4/5 + 2/3)/3)
    assert metrics["per_class"]["contract"] == {"precision": 2/3, "recall": 1.0, "f1": .8, "support": 2}
    zero = classification_metrics(["invoice", "contract", "form"], ["invoice"] * 3)
    assert zero["per_class"]["form"]["precision"] == zero["per_class"]["form"]["f1"] == 0
    for a, p in (([], []), (["invoice"], []), (["receipt"], ["invoice"])):
        with pytest.raises(ValueError):
            classification_metrics(a, p)


@pytest.mark.parametrize("mutation", ["id", "logical", "text", "numeric_variant", "label", "split", "version", "license"])
def test_manifest_leakage_and_validity(mutation):
    data = tiny_dataset()
    first, test = data["samples"][0], data["samples"][2]
    if mutation == "id":
        test["id"] = first["id"]
    elif mutation == "logical":
        test["logical_document_id"] = first["logical_document_id"]
    elif mutation in {"text", "numeric_variant"}:
        test["text"] = first["text"].upper() + (" 234!!" if mutation == "numeric_variant" else "\n")
    elif mutation == "label":
        test["label"] = "receipt"
    elif mutation == "split":
        test["split"] = "development"
    elif mutation == "version":
        test["dataset_version"] = "wrong"
    else:
        test["license"] = ""
    with pytest.raises(ValueError):
        validate_dataset(data)


def test_committed_manifest_has_fixed_balanced_splits():
    data = load_dataset(ROOT / "data/manifests/classification-v1.json")
    assert len(data["samples"]) == 63
    for label in ("invoice", "contract", "form"):
        assert sum(s["label"] == label and s["split"] == "train" for s in data["samples"]) == 15
        assert sum(s["label"] == label and s["split"] == "test" for s in data["samples"]) == 6


def test_missing_and_changed_artifact_fail_explicitly(tmp_path, trained):
    with pytest.raises(FileNotFoundError):
        SklearnDocumentClassifier(tmp_path / "missing.joblib").load()
    model, _, _ = trained
    model.artifact.write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        model.load()
