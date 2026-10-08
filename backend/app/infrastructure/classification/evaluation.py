from datetime import UTC, datetime
from time import perf_counter

from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support

from app.infrastructure.classification.dataset import LABELS, distribution, fingerprint, validate_dataset
from app.infrastructure.classification.model import SklearnDocumentClassifier


def classification_metrics(actual: list[str], predicted: list[str]) -> dict:
    if not actual or len(actual) != len(predicted) or not set(actual + predicted) <= set(LABELS):
        raise ValueError("Metrics require nonempty aligned supported labels")
    precision, recall, f1, support = precision_recall_fscore_support(
        actual, predicted, labels=LABELS, zero_division=0)
    return {
        "accuracy": float(accuracy_score(actual, predicted)),
        "macro_precision": float(precision.mean()), "macro_recall": float(recall.mean()),
        "macro_f1": float(f1.mean()),
        "per_class": {label: {"precision": float(p), "recall": float(r), "f1": float(f), "support": int(n)}
                      for label, p, r, f, n in zip(LABELS, precision, recall, f1, support, strict=True)},
        "confusion_matrix_labels": LABELS,
        "confusion_matrix": confusion_matrix(actual, predicted, labels=LABELS).tolist(),
    }


def evaluate(classifier: SklearnDocumentClassifier, dataset: dict, model_version: str) -> dict:
    validate_dataset(dataset)
    classifier.load()
    metadata = classifier.metadata
    if metadata["model_version"] != model_version:
        raise ValueError("Requested model version does not match artifact")
    if (metadata["dataset_version"] != dataset["dataset_version"]
            or metadata["dataset_digest"] != fingerprint(dataset)):
        raise ValueError("Evaluation dataset differs from the versioned manifest")
    samples = sorted((s for s in dataset["samples"] if s["split"] == "test"), key=lambda s: s["id"])
    start = perf_counter()
    scores = classifier.probabilities([s["text"] for s in samples])
    predicted = [max(row, key=row.get) for row in scores]
    return {
        "dataset_version": dataset["dataset_version"], "dataset_digest": fingerprint(dataset),
        "model_version": model_version, "config_version": metadata["config_version"],
        "sample_count": len(samples), "class_distribution": distribution(dataset, "test"),
        "evaluation_date": datetime.now(UTC).isoformat(),
        "evaluation_method": "Held-out synthetic OCR-like text; frozen explicit test split; argmax predict_proba; no fitting",
        "metrics": classification_metrics([s["label"] for s in samples], predicted),
        "evaluation_seconds": perf_counter() - start, "model_load_seconds": classifier.load_seconds,
        "batch_inference_seconds": classifier.last_inference_seconds,
        "predictions": [{"sample_id": s["id"], "actual": s["label"], "predicted": p, "scores": row}
                        for s, p, row in zip(samples, predicted, scores, strict=True)],
    }
