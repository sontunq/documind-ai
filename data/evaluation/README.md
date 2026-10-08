# DocuMind AI — Evaluation Dataset & Benchmark Protocol

## Overview

This directory and the accompanying manifest `data/manifests/evaluation-v1.json` define the authoritative evaluation dataset for DocuMind AI (Phase 7: Evaluation & Model Reporting).

Evaluation covers the three sequential AI stages of Intelligent Document Processing (IDP):
1. **OCR Engine**: Measures transcription fidelity using Character Error Rate (CER) and Word Error Rate (WER) against ground-truth text pairs.
2. **Document Classifier**: Measures 3-class classification (`invoice`, `contract`, `form`) accuracy, macro/per-class precision, recall, F1, and confusion matrix on held-out test splits.
3. **Structured Field Extractor**: Measures exact-match ratio, per-field precision, recall, and F1 across English and Vietnamese invoices, contracts, and forms.

## Provenance & Ground Truth Integrity

- **Licensing & Data Origin**: All evaluation samples are synthetic, redistributable under CC0-1.0, created specifically for DocuMind AI benchmarking. All company names, personal names, invoice numbers, and transaction amounts are entirely fictional.
- **Bilingual Coverage**: Includes both English and Vietnamese business documents (e.g. VAT invoices / *Hóa đơn GTGT*, service contracts / *Hợp đồng dịch vụ*, registration forms / *Tờ khai đăng ký*).
- **Zero Fabrication**: Per project engineering standards, every metric reported must be directly computed from actual model execution on test data. No metrics, confidence scores, or benchmark numbers may be invented.

## Splits and Data Leakage Prevention

- **Independent Held-Out Evaluation**: Evaluation samples are strictly separated from training sets.
- **Automated Leakage Checking**: `backend/app/evaluation/manifest.py::check_data_leakage` enforces:
  - Unique sample identifiers across training and test splits.
  - Punctuation- and case-normalized content comparison to guarantee no training text appears in the evaluation dataset.
- **Zero Hyperparameter Tuning on Test Split**: Evaluation splits are evaluated as a final measurement without tuning thresholds or feature weights against test results.

## Mathematical Formulations

### 1. Optical Character Recognition (OCR)
- **Levenshtein Distance**: Edit distance $D(r, h)$ computed via dynamic programming (insertions, deletions, substitutions).
- **Character Error Rate (CER)**:
  $$\text{CER} = \frac{D(\text{ref\_chars}, \text{hyp\_chars})}{\max(1, |\text{ref\_chars}|)}$$
- **Word Error Rate (WER)**:
  $$\text{WER} = \frac{D(\text{ref\_words}, \text{hyp\_words})}{\max(1, |\text{ref\_words}|)}$$

### 2. Document Classification
- **Accuracy**: $\frac{\sum \text{Correct}}{\text{Total Samples}}$
- **Macro Precision, Recall, F1**: Unweighted mean of per-class metrics over `invoice`, `contract`, `form`.
- **Confusion Matrix**: Rows represent true labels; columns represent predicted labels.

### 3. Structured Field Extraction
- **Field Match Equality**: Normalized comparison supporting case-insensitivity, whitespace collapsing, and floating-point numeric tolerance ($|v_1 - v_2| < 10^{-4}$).
- **Per-Field Precision & Recall**:
  $$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}}, \quad \text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}}$$
- **Exact Match Ratio**: Ratio of correctly predicted fields over all evaluated ground truth field opportunities.

## Running Evaluation

To execute a complete, reproducible evaluation run across all stages:

```bash
python backend/scripts/evaluate.py --manifest data/manifests/evaluation-v1.json --output .runtime/evaluation/baseline.json --markdown-output reports/baseline.md
```
