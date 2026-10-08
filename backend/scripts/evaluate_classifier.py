"""Evaluate an explicitly named model and dataset on held-out text only."""
import argparse
import json
from pathlib import Path

from app.core.config import ROOT
from app.infrastructure.classification.dataset import load_dataset
from app.infrastructure.classification.evaluation import evaluate
from app.infrastructure.classification.model import SklearnDocumentClassifier


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifests/classification-v1.json")
    parser.add_argument("--artifact", type=Path, default=ROOT / ".runtime/classification/baseline.joblib")
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / ".runtime/classification/evaluation.json")
    args = parser.parse_args()
    dataset = load_dataset(args.manifest)
    if dataset["dataset_version"] != args.dataset_version:
        parser.error("Requested dataset version does not match manifest")
    report = evaluate(SklearnDocumentClassifier(args.artifact), dataset, args.model_version)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
