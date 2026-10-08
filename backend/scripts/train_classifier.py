"""Offline training. Run from repository root; artifacts remain ignored."""
import argparse
import json
from pathlib import Path

from app.core.config import ROOT
from app.infrastructure.classification.dataset import load_dataset
from app.infrastructure.classification.model import train


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifests/classification-v1.json")
    parser.add_argument("--artifact", type=Path, default=ROOT / ".runtime/classification/baseline.joblib")
    parser.add_argument("--threshold", type=float, default=0.60)
    args = parser.parse_args()
    metadata = train(load_dataset(args.manifest), args.artifact, args.threshold)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
