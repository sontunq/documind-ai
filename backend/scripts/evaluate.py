"""CLI script to run reproducible evaluation across OCR, Classification, and Extraction."""
import argparse
import json
from pathlib import Path
import sys

from app.core.config import ROOT
from app.evaluation.runner import EvaluationRunner


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data/manifests/evaluation-v1.json",
        help="Path to evaluation manifest",
    )
    parser.add_argument(
        "--classifier-artifact",
        type=Path,
        default=ROOT / ".runtime/classification/baseline.joblib",
        help="Path to trained classification model artifact",
    )
    parser.add_argument(
        "--training-manifest",
        type=Path,
        default=ROOT / "data/manifests/classification-v1.json",
        help="Path to training manifest for leakage detection",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / ".runtime/evaluation/baseline.json",
        help="Path to write structured JSON evaluation output",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=ROOT / "reports/baseline.md",
        help="Path to write rendered Markdown baseline report",
    )
    args = parser.parse_args()

    if not args.manifest.is_file():
        print(f"Error: Evaluation manifest not found: {args.manifest}", file=sys.stderr)
        sys.exit(1)

    print(f"Starting IDP Pipeline Evaluation...")
    print(f"  Manifest:    {args.manifest}")
    print(f"  Classifier:  {args.classifier_artifact}")
    print(f"  Training:    {args.training_manifest}")

    runner = EvaluationRunner(
        eval_manifest_path=args.manifest,
        classifier_artifact_path=args.classifier_artifact,
        training_manifest_path=args.training_manifest,
    )

    try:
        report = runner.run()
    except Exception as exc:
        print(f"Evaluation failed: {exc}", file=sys.stderr)
        sys.exit(1)

    # Save JSON report
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved JSON evaluation report: {args.output} ({args.output.stat().st_size} bytes)")

    # Save Markdown report
    md_content = runner.render_markdown(report)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(md_content, encoding="utf-8")
    print(f"Saved Markdown baseline report: {args.markdown_output} ({args.markdown_output.stat().st_size} bytes)")

    # Print summary table
    ocr_m = report["ocr"]["corpus_metrics"]
    cls_m = report["classification"]["metrics"]
    ext_m = report["extraction"]["metrics"]
    print("\n" + "=" * 60)
    print("           DOCUMIND AI — EVALUATION BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"OCR CER:                  {ocr_m['cer'] * 100:.2f}%")
    print(f"OCR WER:                  {ocr_m['wer'] * 100:.2f}%")
    print(f"Classification Accuracy:  {cls_m['accuracy'] * 100:.2f}% ({report['classification']['sample_count']} samples)")
    print(f"Classification Macro F1:  {cls_m['macro_f1']:.4f}")
    print(f"Extraction Exact Match:   {ext_m['exact_match_ratio'] * 100:.2f}% ({ext_m['total_fields']} fields)")
    print(f"Extraction Macro F1:      {ext_m['macro_f1']:.4f}")
    print("=" * 60)
    print("Evaluation completed successfully.")


if __name__ == "__main__":
    main()
