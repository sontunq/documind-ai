# ADR 0003: Hybrid ML Classification and Spatial Rule-Based Extraction

## Status
Accepted

## Context
Document understanding requires solving two distinct tasks:
1. Document-level classification (determining whether an incoming scan is an invoice, contract, or form).
2. Field-level structured extraction (identifying specific key-value pairs like invoice numbers, dates, parties, and totals).

While heavy generative multimodal LLMs or complex vision-language models (e.g. LayoutLMv3, Donut) can handle both, they require GPUs, substantial memory (4GB–16GB VRAM), and introduce latency and non-deterministic hallucinations.

## Decision
We implemented a hybrid, decoupled architecture:
1. **Document Classification:** A lightweight Scikit-learn TF-IDF vectorizer + Multinomial Logistic Regression pipeline. It runs in under 4 milliseconds on CPU, requires less than 40KB model storage, and provides mathematically calibrated class probabilities.
2. **Field Extraction:** A spatial layout-aware, rule-based extractor (`RuleBasedFieldExtractor`). It leverages normalized bounding box geometries `(x, y, width, height)` and bilingual English/Vietnamese regex patterns to extract fields directly from OCR token lines.
3. **Pluggable Interface:** The extractor adheres to a domain protocol `FieldExtractor`. Future phases can inject multimodal models or specialized deep learning extractors without altering the application workflow.

## Consequences
- **Positive:** Sub-second extraction latency on standard consumer CPUs; zero GPU dependency; fully deterministic output; zero cloud API cost.
- **Negative:** Rule-based extraction requires keyword and geometric tuning when facing highly divergent, unconventional invoice layouts.
