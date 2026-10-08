# DocuMind AI — Baseline Evaluation Report

> **Zero-Fabrication Commitment:** All metrics below are computed directly from actual local model and extractor execution against frozen held-out evaluation splits. No numbers have been fabricated or manually adjusted.

## 1. System & Evaluation Context

- **Evaluation Date (UTC):** `2026-10-07T23:20:48.302320+00:00`
- **Dataset Version:** `evaluation-synthetic-v1`
- **Operating System:** Windows 11 (Windows-11-10.0.22631-SP0)
- **Processor / Architecture:** Intel64 Family 6 Model 126 Stepping 5, GenuineIntel (AMD64) — 8 Logical Cores
- **Python Version:** `3.12.14`
- **Key Libraries:** scikit-learn `1.7.2`, NumPy `2.2.6`, FastAPI `0.141.1`
- **Total Benchmark Execution Duration:** 0.0461s

---

## 2. Executive Benchmark Summary

| AI Stage | Primary Metric | Measured Value | Samples Evaluated | Status |
|---|---|---:|---:|:---:|
| **OCR Engine** | Character Error Rate (CER) | `0.54%` | 6 text pairs | Passed |
| **OCR Engine** | Word Error Rate (WER) | `3.23%` | 6 text pairs | Passed |
| **Document Classification** | Test Accuracy | `100.00%` | 18 documents | Passed |
| **Document Classification** | Macro F1 Score | `1.0000` | 18 documents | Passed |
| **Field Extraction** | Exact Match Ratio | `100.00%` | 6 documents (42 fields) | Passed |
| **Field Extraction** | Macro F1 Score | `1.0000` | 42 fields | Passed |

---

## 3. Optical Character Recognition (OCR) Evaluation

- **Total Characters Evaluated:** 367
- **Total Words Evaluated:** 62
- **Aggregate Character Edit Distance:** 2
- **Aggregate Word Edit Distance:** 2
- **Corpus Character Error Rate (CER):** `0.0054` (0.54%)
- **Corpus Word Error Rate (WER):** `0.0323` (3.23%)

### Per-Sample OCR Breakdown

| Sample ID | Category | Ref Chars | Hyp Chars | CER | WER |
|---|---|---:|---:|---:|---:|
| `ocr-eval-en-01` | clean-english | 56 | 56 | 0.0000 | 0.0000 |
| `ocr-eval-en-02` | legal-clause | 77 | 77 | 0.0000 | 0.0000 |
| `ocr-eval-en-03` | ocr-noise-substitution | 62 | 62 | 0.0161 | 0.1000 |
| `ocr-eval-vi-01` | clean-vietnamese | 74 | 74 | 0.0000 | 0.0000 |
| `ocr-eval-vi-02` | vietnamese-diacritic-noise | 48 | 48 | 0.0208 | 0.0909 |
| `ocr-eval-form-01` | form-trailing-dots | 50 | 50 | 0.0000 | 0.0000 |

---

## 4. Document Classification Evaluation

- **Model Identifier:** `tfidf-logistic-regression`
- **Model Version:** `f1281042d7c9dce5c39e5afab8005c14f692ac22a39addf88345ac4cd0538e39`
- **Training Dataset Version:** `classification-synthetic-en-v1`
- **Held-Out Test Sample Count:** 18 (6 per class)
- **Inference Duration:** 0.0030s

### Classification Metrics

- **Accuracy:** `1.0000` (100.00%)
- **Macro Precision:** `1.0000`
- **Macro Recall:** `1.0000`
- **Macro F1 Score:** `1.0000`

### Per-Class Performance

| Document Type | Precision | Recall | F1 Score | Test Support |
|---|---:|---:|---:|---:|
| `contract` | 1.0000 | 1.0000 | 1.0000 | 6 |
| `form` | 1.0000 | 1.0000 | 1.0000 | 6 |
| `invoice` | 1.0000 | 1.0000 | 1.0000 | 6 |

### Confusion Matrix

Labels order: ['contract', 'form', 'invoice']
```text
    6    0    0
    0    6    0
    0    0    6
```

---

## 5. Structured Field Extraction Evaluation

- **Extractor Name / Version:** `rule-based-baseline` v`1.0.0`
- **Evaluated Document Types:** contract, form, invoice
- **Language Coverage:** Bilingual (English & Vietnamese)
- **Total Opportunities Evaluated:** 42
- **Exact Match Ratio:** `100.00%`
- **Macro Precision:** `1.0000`
- **Macro Recall:** `1.0000`
- **Macro F1 Score:** `1.0000`

### Per-Field Extraction Performance

| Field Name | Precision | Recall | F1 Score | Support (GT) | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| `Company Name` | 1.0000 | 1.0000 | 1.0000 | 1 | 1 | 0 | 0 |
| `Contact Email` | 1.0000 | 1.0000 | 1.0000 | 1 | 1 | 0 | 0 |
| `Họ và tên` | 1.0000 | 1.0000 | 1.0000 | 1 | 1 | 0 | 0 |
| `Số CCCD` | 1.0000 | 1.0000 | 1.0000 | 1 | 1 | 0 | 0 |
| `Số điện thoại` | 1.0000 | 1.0000 | 1.0000 | 1 | 1 | 0 | 0 |
| `Tax ID` | 1.0000 | 1.0000 | 1.0000 | 1 | 1 | 0 | 0 |
| `contract_number` | 1.0000 | 1.0000 | 1.0000 | 2 | 2 | 0 | 0 |
| `contract_value` | 1.0000 | 1.0000 | 1.0000 | 2 | 2 | 0 | 0 |
| `currency` | 1.0000 | 1.0000 | 1.0000 | 2 | 2 | 0 | 0 |
| `customer` | 1.0000 | 1.0000 | 1.0000 | 2 | 2 | 0 | 0 |
| `due_date` | 1.0000 | 1.0000 | 1.0000 | 2 | 2 | 0 | 0 |
| `effective_date` | 1.0000 | 1.0000 | 1.0000 | 2 | 2 | 0 | 0 |
| `expiry_date` | 1.0000 | 1.0000 | 1.0000 | 2 | 2 | 0 | 0 |
| `form_title` | 1.0000 | 1.0000 | 1.0000 | 2 | 2 | 0 | 0 |
| `governing_law` | 1.0000 | 1.0000 | 1.0000 | 2 | 2 | 0 | 0 |
| `invoice_number` | 1.0000 | 1.0000 | 1.0000 | 2 | 2 | 0 | 0 |
| `issue_date` | 1.0000 | 1.0000 | 1.0000 | 2 | 2 | 0 | 0 |
| `party_a` | 1.0000 | 1.0000 | 1.0000 | 2 | 2 | 0 | 0 |
| `party_b` | 1.0000 | 1.0000 | 1.0000 | 2 | 2 | 0 | 0 |
| `subtotal` | 1.0000 | 1.0000 | 1.0000 | 2 | 2 | 0 | 0 |
| `supplier` | 1.0000 | 1.0000 | 1.0000 | 2 | 2 | 0 | 0 |
| `tax` | 1.0000 | 1.0000 | 1.0000 | 2 | 2 | 0 | 0 |
| `title` | 1.0000 | 1.0000 | 1.0000 | 2 | 2 | 0 | 0 |
| `total` | 1.0000 | 1.0000 | 1.0000 | 2 | 2 | 0 | 0 |

---

## 6. Real-World Limitations & Governance

1. **Synthetic Corpus Scope**: Evaluation texts are generated synthetic business documents. While they accurately reflect standard layout conventions, real-world documents will exhibit higher degradation, skew, handwritten notes, watermarks, and irregular multi-column tables.
2. **Classifier Vocabulary**: The TF-IDF + Logistic Regression baseline relies on closed-vocabulary unigrams/bigrams for 3 classes (`invoice`, `contract`, `form`). Unseen out-of-distribution documents (e.g. medical records, resumes) receive an argmax prediction flagged with low confidence rather than a native reject class.
3. **Extraction Heuristics**: The rule-based extractor uses spatial proximity and regex patterns. Highly non-standard invoice templates or handwritten forms require layout-aware vision-language models (e.g. LayoutLM / Donut) planned for future phases.
4. **Human Review Auditing**: Raw AI predictions must never be overwritten; reviewed corrections are retained separately in the audit trail per Phase 6 governance.
