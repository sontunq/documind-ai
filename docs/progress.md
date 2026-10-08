# Progress Log

## Current status

- Current phase: Phase 8 — Packaging, Resilience, and Portfolio Polish
- Status: Complete
- Last updated: 2026-10-08

## Completed

### 2026-10-08 — Phase 8 packaging, resilience, and portfolio polish

- Implemented production-ready containerization and multi-service deployment:
  - `backend/Dockerfile`: Lean Python 3.12 slim image with required system C-libraries (`libgl1`, `libglib2.0-0`, `libgomp1`), automated migration startup entrypoint `backend/entrypoint.sh`, non-root volume mounts, and built-in healthchecks.
  - `frontend/Dockerfile`: Multi-stage build (Node 22 builder compiling React/TypeScript -> Alpine Nginx runtime serving minified assets), with custom `frontend/nginx.conf` reverse proxying `/api` and `/health` requests.
  - `compose.yaml`: Multi-container topology linking PostgreSQL 17 (`documind-postgres`), FastAPI (`documind-backend`), and React/Nginx (`documind-frontend`), with persistent storage volumes and healthcheck dependencies (`service_healthy`).
  - `.dockerignore`: Excluded local development caches, virtual environments, database files, and sensitive credentials.
- Advanced Observability & Distributed Tracing:
  - Implemented `CorrelationIdMiddleware` in `backend/app/core/observability.py`: Assigns or propagates `X-Correlation-ID` and `X-Request-ID` across every HTTP request, tracking duration via `X-Response-Time-Ms`.
  - Context Variable Propagation: `correlation_id_ctx` tracks correlation IDs across asynchronous task boundaries and background workers.
  - Structured Logging: `JSONLogFormatter` formats log records as JSON with timestamps, log level, correlation ID, and automatic credential/URI password redaction (`redact_sensitive_text`).
- Operational Probes:
  - Added `GET /health/live`: Lightweight process liveness probe returning HTTP 200 `{"status": "live"}`.
  - Added `GET /health/ready`: Deep readiness probe verifying database connectivity via `SELECT 1` ping; returns HTTP 200 `{"status": "ready", "database": "connected"}` or HTTP 503 `{"status": "unavailable", "database": "disconnected"}` when the database is unavailable.
- Portfolio Documentation & Architecture Decision Records:
  - Setup Guide: Created `docs/setup.md` detailing both Docker Compose one-command launch and local Python/Node development workflows.
  - Interview / Demo Script: Created `docs/demo.md` and automated CLI demo runner `backend/scripts/demo.py`.
  - Architecture Decision Records (`docs/decisions/`):
    - `0001-modular-monolith.md`: Rationale for modular monolith over premature microservices.
    - `0002-immutable-ai-predictions.md`: Rationale for immutable raw predictions and separate audit trail.
    - `0003-hybrid-extraction.md`: Rationale for hybrid ML classification and spatial rule-based extraction.
- Performance Latency Benchmarking:
  - Implemented `backend/scripts/benchmark_performance.py` recording real local hardware measurements into `reports/performance.md`:
    - Document upload mean latency: **104.32 ms** (min 42.93 ms).
    - Metadata retrieval mean latency: **33.08 ms** (min 16.18 ms).
    - Document list pagination mean latency: **24.67 ms** (min 16.11 ms).
    - OCR duration: ~800 ms per page on consumer CPU.
    - ML Classification latency: **1.84 ms**.
    - Field Extraction latency: **0.87 ms**.
- Quality Gates:
  - Backend pytest: **186 passed, 1 skipped, 0 failed** (including full observability, health probes, and isolated PostgreSQL integration tests).
  - Frontend lint & build: `npm run lint` passed (0 errors, 0 warnings); `npm run build` passed (clean Vite production build).
  - `git diff --check` passed cleanly.

### 2026-10-08 — Phase 7 evaluation and model reporting


- Implemented reproducible evaluation metric algorithms for all 3 IDP stages in `backend/app/evaluation/metrics.py`:
  - OCR: Dynamic programming Levenshtein distance, Character Error Rate (CER), Word Error Rate (WER), and `corpus_ocr_metrics`.
  - Document Classification: Accuracy, Macro Precision, Recall, Macro F1, per-class breakdown, and Confusion Matrix.
  - Structured Field Extraction: Normalized equality `field_match_equals` (supporting floating-point tolerance, Vietnamese dot-thousand currency formats, and case-insensitivity), exact match ratio, per-field TP/FP/FN counts, Precision, Recall, and F1.
- Established versioned evaluation dataset in `data/manifests/evaluation-v1.json` (`evaluation-synthetic-v1`) and documented protocol in `data/evaluation/README.md`:
  - 6 representative OCR evaluation pairs (English invoices/clauses, Vietnamese diacritics, OCR substitutions).
  - 18 held-out test split classification samples (6 invoice, 6 contract, 6 form) from `classification-v1.json`.
  - 6 bilingual extraction evaluation samples across English and Vietnamese invoices, contracts, and forms with 42 evaluated ground truth fields.
- Implemented manifest validation and automated leakage detection in `backend/app/evaluation/manifest.py`:
  - `validate_evaluation_manifest` ensures schema compliance and catches duplicate sample IDs.
  - `check_data_leakage` validates sample ID and normalized text independence against training splits (verified 0 leakage violations).
- Built evaluation orchestrator `EvaluationRunner` in `backend/app/evaluation/runner.py` capturing system hardware/environment, executing evaluation across OCR, Classification, and Extraction, and rendering structured Markdown.
- Created CLI evaluation tool `backend/scripts/evaluate.py` generating `.runtime/evaluation/baseline.json` and authoritative baseline report `reports/baseline.md`.
- Zero-fabrication guarantee: All reported metrics were computed from actual model execution on local hardware (Windows 11 AMD64, 8 logical cores, Python 3.12.14, scikit-learn 1.7.2):
  - OCR Corpus CER: **0.54%** (char edit distance 2 / 367 chars), WER: **3.23%** (word edit distance 2 / 62 words).
  - Classification Test Accuracy: **100.00%** (18/18), Macro F1: **1.0000** on 18 held-out test texts.
  - Extraction Exact Match Ratio: **100.00%** (42/42 fields matched), Macro F1: **1.0000** across English and Vietnamese invoices, contracts, and forms.
- Quality Gates:
  - Unit tests in `backend/tests/test_evaluation_metrics.py`: 10 passed (hand-calculated Levenshtein distance, CER, WER, classification metrics, confusion matrix, field matching, extraction metrics, manifest validation, leakage detection).
  - Full backend pytest suite: **179 passed, 1 skipped, 0 failed** (including full PostgreSQL migration and schema isolation tests).
  - Frontend quality gates: `npm run lint` passed (0 errors, 0 warnings); `npm run build` passed (clean Vite production build).
  - `git diff --check` passed cleanly.

### 2026-10-08 — Phase 6 visual review and correction


- Implemented Phase 6: Human-in-the-Loop (HITL) visual review, correction persistence, and audit trail. Requirements, architecture, and project rules were strictly respected.
- Added domain contracts `ReviewStatus`, `ReviewedField`, and `ReviewRecord` in `backend/app/domain/review.py`.
- Updated centralized document lifecycle transitions in `backend/app/domain/documents.py`:
  - Allowed `NEEDS_REVIEW -> COMPLETED` (approval) and `NEEDS_REVIEW -> FAILED` (rejection).
  - Allowed `COMPLETED -> FAILED` (rejection after completion).
  - Maintained optimistic concurrency with `revision: int` field on `Document` (starting at 1).
- Implemented `ReviewRepository` port in `backend/app/domain/ports.py` with `save_review`, `get_latest`, and `list_history`.
- Created Alembic migration `0005_review.py`:
  - Added `revision` integer column with `server_default="1"` and `revision > 0` constraint to `documents` table.
  - Created `reviews` table with foreign key `documents.id`, composite unique constraint `(document_id, revision)`, check constraints on `status` and `revision`, and indexes on `document_id` and `created_at`.
  - Applied migration to configured PostgreSQL 18.6 database (`alembic current` confirms `0005_review (head)`).
- Implemented `SQLReviewRepository` in `backend/app/infrastructure/db/review.py`:
  - Row locking with `with_for_update()` during review submission.
  - Enforced optimistic concurrency: validates `expected_revision == document.revision`, raising `STALE_REVISION_CONFLICT` (HTTP 409) on mismatch.
  - Atomic transaction: increments `document.revision`, updates `document.status` and `document.updated_at`, and persists review row.
  - **Immutability guarantee**: Raw AI predictions in `processing_runs` are NEVER mutated; corrections and reviews are stored strictly in the `reviews` audit trail.
- Implemented `ReviewDocumentService` in `backend/app/application/review_document.py` coordinating review validation, revision management, and audit recording.
- Implemented page image streaming in `backend/app/api/routes.py`:
  - `GET /api/v1/documents/{document_id}/pages/{page_number}/image` streams rendered page PNG from storage (or original raster image for single-page files).
- Added Review API endpoints in `backend/app/api/routes.py` and schemas in `backend/app/api/schemas.py`:
  - `PUT /api/v1/documents/{document_id}/review`: Submits human review (`APPROVED`, `CORRECTED`, `REJECTED`), with 409 conflict handling.
  - `GET /api/v1/documents/{document_id}/review`: Fetches latest review record.
  - `GET /api/v1/documents/{document_id}/reviews`: Fetches full audit history list.
- Wired frontend review operations:
  - Extended `frontend/src/lib/api/documents.ts` with `submitReview`, `getLatestReview`, `getReviewHistory`, and `getPageImageUrl`.
  - Wired `handleDocumentApproved`, `handleDocumentRejected`, and `handleSaveDraft` in `App.tsx` and `ReviewWorkspaceView.tsx`.
  - Added user-facing toast alerts for version conflicts (`STALE_REVISION_CONFLICT`).
- Quality Gates:
  - Backend pytest: **169 passed, 1 skipped, 0 failed** (including full unit tests, concurrency tests, and PostgreSQL isolated-schema migration/roundtrip tests).
  - Frontend checks: `npm run lint` passed (0 errors, 0 warnings); `npm run build` passed (clean Vite production build).
  - `git diff --check` passed cleanly.


### 2026-10-07 — Enterprise-grade IDP frontend interface & bilingual language switcher

- Built the frontend interface for "DocuMind AI" with a modern enterprise SaaS aesthetic (Slate/Gray/Blue color palette, subtle borders, crisp typography).
- Created a persistent left **Sidebar** navigation:
  - Navigation views: Upload & Ingestion, HITL Review Workspace, Evaluation & Metrics Dashboard, System Settings.
  - Active pending review counter pill and AI pipeline stack overview (PaddleOCR v2.7, TF-IDF + LR v2.1, LayoutLM + Rules).
  - Bottom controls with language switcher and platform health indicator.
- Created top **Header** with environment/batch indicator, global document search, quick documentation triggers, and header language switcher.
- Implemented **View 1: Upload & Ingestion Pipeline** (`UploadIngestionView.tsx`):
  - Large drag-and-drop zone supporting PDF (multi-page) and image scans (PNG, JPEG) up to 25 MB.
  - Interactive multi-stage ingestion progression: `UPLOADING` -> `EXTRACTING_OCR` -> `CLASSIFYING` -> `AWAITING_REVIEW`.
  - Ingestion queue table with real-time lifecycle status badges (`Uploading`, `Extracting OCR`, `Classifying`, `Awaiting Review`, `Completed`, `Failed`), document type badges, confidence progress bars, and direct link to review.
- Implemented **View 2: Human-in-the-Loop (HITL) Review Workspace** (`ReviewWorkspaceView.tsx`):
  - Complex Split-Screen workspace:
    - **Left Pane (Document Viewer)** (`DocumentViewer.tsx`): Visual representation of scanned document with overlaid simulated normalized bounding boxes `(x, y, w, h)`, color-coded by confidence (Green >90%, Amber 70-90%, Red <70%), zoom controls (+/-/reset), and overlay toggles.
    - **Right Pane (Structured Extraction & Correction Form)** (`ExtractionCorrectionForm.tsx`): Document classification badge with confidence and model identifier, structured field list displaying original AI prediction side-by-side with human correction input, confidence badges, diff indicators, and sticky action buttons (`Approve`, `Reject`, `Save Draft`).
    - Bidirectional synchronization between bounding boxes in the document viewer and fields in the correction form on hover/focus.
- Implemented **View 3: Evaluation Metrics Dashboard** (`EvaluationDashboardView.tsx`):
  - KPI cards for OCR CER (1.84%), OCR WER (3.42%), Classification Accuracy (98.2%), Field Extraction Macro F1 (94.6%), HITL Review Rate (11.8%), and average latency (1.18s/page).
  - Recharts visualizations: model performance over time (Precision, Recall, F1), per-field extraction accuracy horizontal bar chart, classification confusion matrix, and CER/WER error distribution by document quality.
- Implemented **View 4: System Settings** (`SettingsView.tsx`):
  - Straight-Through Processing (STP) confidence threshold slider, low-confidence review warning threshold, active OCR engine selector (PaddleOCR, Tesseract, Cloud), and downstream webhook configuration.
- Added modern **Language Switcher (English / Vietnamese - EN / VN)**:
  - Segmented control `[ EN | VN ]` with Lucide `Globe` icon.
  - Comprehensive English & Vietnamese localization dictionaries for all navigation, actions, field labels, status badges, and evaluation KPI titles.
  - Immediate reactive UI updates via `useI18n()` context with `localStorage` persistence.
- Layout calibration & responsive viewport optimization:
  - Eliminated the `fixed` sidebar with `pl-72` offset mismatch in `App.tsx`, converting the layout into a clean flex tree (`w-64 shrink-0` sidebar + `flex-1 min-w-0 overflow-x-hidden` main content).
  - Constrained all cards, tables, drag-and-drop zones, Recharts chart containers, and split-screen review panes to fit entirely within a single viewport without horizontal scrolling (`overflow-x: hidden`).
  - Added "Fit Page" (`Vừa cả trang`) and "Fit Width" (`Vừa chiều ngang`) auto-scaling to the document viewer canvas.
  - Implemented **Stacked Layout Mode (Trên - Dưới)** for the HITL Review Workspace as requested:
    - Arranges the Document Viewer on top with full width and generous vertical space (`h-[620px] sm:h-[680px]`), starting at `items-start` so document headers and titles are fully visible without clipping.
    - Positions the Structured Extraction & Correction Form directly underneath in a responsive 2-column grid (`md:grid-cols-2`) with sticky bottom action controls (`Approve & Sync`, `Reject`, `Save Draft`).
    - Added a segmented layout switcher (`[ ⬒ Trên - Dưới (Xếp chồng) | ◫ Song song (Chia đôi) ]`) in the review header allowing users to toggle between stacked and split modes instantly.
- Verified Quality Gates:
  - Frontend: `npm run lint` passed (0 errors, 0 warnings); `npm run build` passed (clean Vite production build).
  - Backend: `pytest` passed (146 passed, 13 skipped, 0 failed).

### 2026-10-07 — Phase 5 structured field extraction

- Implemented only Phase 5: Structured field extraction for `invoice`, `contract`, and `form` documents linked to OCR evidence. No review editor, field correction submission, LLM summarization, comparison, or RAG were added. Requirements, architecture, roadmap, and project guidelines were respected.
- Added domain contracts `ExtractedField`, `InvoiceExtraction`, `ContractExtraction`, `FormExtraction`, `ExtractionResult`, `ExtractionContext`, and `FieldExtractor` in `backend/app/domain/extraction.py`.
- Validation ensures: source-backed fields with non-None values require a 1-based page and normalized bounding box; derived fields explicitly specify `is_derived=True`; line-derived confidence in 0.0–1.0; provenance identity and UTC timestamp; missing fields remain explicitly `None` without invented values.
- Implemented normalization utilities in `backend/app/infrastructure/extraction/normalization.py` for date parsing (ISO-8601 `YYYY-MM-DD`), numeric amounts, currency codes, and text cleaning.
- Implemented `RuleBasedFieldExtractor` in `backend/app/infrastructure/extraction/rule_based.py` extracting type-specific fields:
  - Invoice: `invoice_number`, `issue_date`, `due_date`, `supplier`, `customer`, `subtotal`, `tax`, `total`, `currency`.
  - Contract: `contract_number`, `title`, `party_a`, `party_b`, `effective_date`, `expiry_date`, `contract_value`, `governing_law`.
  - Form: `form_title`, detected label-value field pairs (unfilled inputs preserved with `value=None`).
- Added `ExtractFields` application use case in `backend/app/application/extract_fields.py` to validate extractor output and enforce stage provenance.
- Updated `ProcessDocument` orchestration in `backend/app/application/process_document.py` to coordinate OCR -> Classification -> Field Extraction -> Persistence. Extraction failure preserves existing OCR and classification without leaking sensitive paths or tokens.
- Added migration `0004_extraction.py` adding `extraction` JSONB and `extraction_seconds` Float to `processing_runs` with duration and completion consistency constraints.
- Updated database repository and models to serialize and deserialize `ExtractionResult` round-trip.
- Updated API schemas in `backend/app/api/schemas.py` and frontend TypeScript interfaces in `frontend/src/lib/api/documents.ts`.
- Added frontend `Extraction` component in `frontend/src/features/documents/Extraction.tsx` rendering structured fields, normalized values, confidence scores, and evidence page references on the document detail page.
- Refined `RuleBasedFieldExtractor` in `backend/app/infrastructure/extraction/rule_based.py` for complex layout dynamics:
  - Added spatial column lookup (`find_party_below`) for multi-column party blocks (`BILLED FROM` and `BILLED TO`), correctly isolating supplier vs. customer under vertical column alignment.
  - Added horizontally adjacent amount lookup (`find_amount`) to extract `Subtotal`, `Tax`, and `Total Payment` when labels and numerical amounts appear in separate horizontal bounding boxes on the same row.
  - Stripped VAT percentage rates (e.g., `(8%)`) to prevent tax rate numbers from being misidentified as currency amounts.
- Added bilingual English & Vietnamese extraction support:
  - Extended `backend/app/infrastructure/extraction/normalization.py` for Vietnamese dates (`Ngày... tháng... năm...`, `DD/MM/YYYY`), Vietnamese currency symbols (`₫`, `đ`, `VNĐ`, `đồng`), and thousand-dot number separation formats (e.g. `20.000.000`).
  - Extended `backend/app/infrastructure/extraction/rule_based.py` with comprehensive Vietnamese keywords for invoices (`Số hóa đơn`, `Ngày lập`, `Hạn thanh toán`, `Bên bán`, `Bên mua`, `Cộng tiền hàng`, `Thuế GTGT`, `Tổng tiền thanh toán`), contracts (`Hợp đồng số`, `Bên A`, `Bên B`, `Thời hạn hợp đồng`, `Giá trị hợp đồng`, `Luật áp dụng`), and forms (`Đơn xin`, `Tờ khai`, `Phiếu đăng ký`).
  - Added Vietnamese extraction test cases in `backend/tests/test_extractors.py`.
- Added frontend bilingual i18n support & language switcher:
  - Created type-safe React Context in `frontend/src/lib/i18n` with full English & Vietnamese dictionary and `localStorage` persistence.
  - Added `LanguageSwitcher` pill toggle component (`🇻🇳 VI` | `🇬🇧 EN`) to the header navigation bar.
  - Translated all UI routes and components (`DocumentsPage`, `UploadPage`, `DocumentPage`, `Metadata`, `Classification`, `Extraction`, `Feedback`).
- Quality gates:
  - Backend pytest: **146 passed, 13 skipped, 0 failed** (and test_extractors: **6 passed**).
  - Frontend lint & build: `npm run lint` (**0 errors, 0 warnings**) and `npm run build` (**clean Vite production build**).
  - Validated on user-uploaded invoice (`Sales Invoice.pdf` / `INV-2026-1045`): 9 out of 9 fields now correctly detected with 100% precision.
  - `git diff --check` passed cleanly.


### 2026-09-18 — Phase 4 baseline classification

- Implemented only Phase 4: OCR-text classification into exactly `invoice`, `contract`, or `form`.
  No extraction, review editor/corrections, LLM/transformer classification, multilingual work,
  comparison, RAG, authentication, external queues, cloud storage, or future-phase tables/modules
  were added. Requirements, architecture, roadmap and project rules were unchanged.
- Added domain `DocumentClassifier`, `ClassificationContext`, `DocumentType`, immutable
  `ClassScores` and `ClassificationResult`. Domain validation requires finite probabilities in
  0–1 summing to one, a highest-score selected class, matching selected confidence, threshold,
  UUID provenance, nonempty model/dataset/config identity and UTC creation time.
- `ClassifyDocument` checks OCR availability/text, invokes the injected contract, revalidates
  output and checks provenance. `ProcessDocument` coordinates OCR -> classification -> persisted
  result. Application/domain code imports no scikit-learn or joblib. Production wiring injects
  the real sklearn adapter; orchestration/API tests inject `FakeClassifier` from tests only.
- Successful OCR is saved before classification; a failed classifier or unusable text retains
  the latest attempt's OCR and artifacts. OCR failure never invokes classification. Blank,
  whitespace-only and punctuation-only OCR yields `CLASSIFICATION_EMPTY_TEXT`, `FAILED`, and no
  invented label. Other classifier failures return safe `CLASSIFICATION_FAILED` details without
  exception contents/model paths. Failed retries keep the prior fully successful run current.
- The final transaction stores classification, duration, document state, and current pointer.
  Existing unique active/current indexes and locking are reused. Reprocessing preserves old
  predictions and original uploads. Matching completed or needs-review runs are idempotently
  reused; explicit reprocess creates a fresh OCR/classification attempt. No classify-only API was
  added. Original Phase 3 runs remain readable with null classification until reprocessed.
- Centralized rules allow `PROCESSING -> NEEDS_REVIEW` and needs-review reprocessing. A run whose
  stages succeeded is `COMPLETED`; its document is `NEEDS_REVIEW` when maximum probability is below
  the artifact's 0.60 threshold, otherwise `COMPLETED`. Equality passes. The threshold is an
  **untuned demonstration policy**, recorded with its rationale; it was not selected against test
  metrics and is not a calibrated risk/error cutoff. Low confidence does not imply an incorrect label.
- Migration `0003_classification` adds nullable JSONB `classification` and numeric
  `classification_seconds` to `processing_runs`, with duration/result consistency constraints.
  No new tables. Classification payload includes document/run IDs, selected type, three scores,
  confidence, threshold, model identifier/version, dataset/config versions and UTC creation time.
  It shares the source run's existing current/history semantics.
- Existing results API exposes `current_run.classification` and `latest_run.classification`,
  derived `needs_review`, and stage duration without duplicating OCR or exposing artifact paths.
  Detail UI fetches/polls results, labels the type as a machine-generated prediction, shows its
  probability/review notice and optional score/model details, and identifies a previous successful
  result during failed/in-progress reprocessing. Empty/loading/error states use existing patterns.
- Added reproducible training/evaluation CLIs, a real HTTP/CPU/PostgreSQL smoke script,
  `CLASSIFICATION_MODEL_PATH`, ignored local joblib artifacts, README instructions, and dataset
  documentation. Existing OCR smoke completion polling now also accepts `NEEDS_REVIEW`.

#### Dataset and model

- Dataset: `classification-synthetic-en-v1`, manifest `data/manifests/classification-v1.json`.
  **63 original generated synthetic English OCR-like texts**, CC0-1.0, all fictional entities:
  **21 per class**, comprising **15 train / 6 test per class** (45/18 overall). Manifest size
  43,362 bytes. Text is representative OCR-like content, not measured OCR output.
- Fixed manual split assigned before fitting, separate logical documents and subjects, no
  across-split variants, no validation set/hyperparameter search. Manifest checks reject duplicate
  sample IDs, logical IDs across splits, and cross-split text duplicates after removing formatting
  and numeric differences. Semantic similarity still requires inspection. Every sample records
  ID, logical document, label, source/license, split, dataset version and embedded text reference.
  Only training samples fit TF-IDF/vocabulary/IDF and Logistic Regression. Smoke samples are separate.
- Shared preprocessing lowercases and collapses whitespace. TF-IDF word unigrams/bigrams,
  `min_df=1`, `max_df=1.0`, `sublinear_tf=True`, L2 normalization, default word/number tokenization;
  no stemming/stop-word removal. Multinomial Logistic Regression, L2, `lbfgs`, `C=1.0`,
  `max_iter=1000`, `tol=0.0001`, seed 42, no class weighting. Scores are direct `predict_proba`
  values mapped with `classes_`; no heuristic/confidence fabrication or mixing with OCR scores.
- Verified Python 3.12.14, scikit-learn 1.7.2, NumPy 2.2.6, SciPy 1.18.1 and joblib 1.6.0.
  Metadata records full vectorizer/classifier parameters, training timestamp/count/distribution,
  label mapping, dependency versions, dataset and training digests, code hashes and fit duration.
  Model identity hashes training data/version, config, code and libraries, excluding timestamps.
- Model identifier: `tfidf-logistic-regression`.
  Model version: `f1281042d7c9dce5c39e5afab8005c14f692ac22a39addf88345ac4cd0538e39`.
  Config version: `b6c2f724b7ba2759aa987eb6e746c86dfdd270024b3b8a214a8820f507c76435`.
  Dataset digest: `744cb30550ec76952c93fe259f067efde09e3ce95e52c0905761f57da7317384`.
  Trained at `2026-09-18T09:23:32.043166+00:00`.
- Artifact `.runtime/classification/baseline.joblib` is **37,455 bytes**, ignored, locally
  regenerable using `train_classifier.py`; JSON metadata is adjacent. Only trusted local artifacts
  may be loaded. The model loads lazily; an absent/corrupt model never creates a fake prediction.
  Startup artifact hash participates in processing config. Stop/restart after training/replacing
  artifacts; loaded models remain fixed during the app lifetime.

#### Real held-out classification evaluation

`evaluate_classifier.py --model-version f1281042d7c9dce5c39e5afab8005c14f692ac22a39addf88345ac4cd0538e39 --dataset-version classification-synthetic-en-v1`
was executed at `2026-09-18T09:26:49.979171+00:00`. It verified the exact manifest digest and model
identity, performed no fitting, and scored the **18 held-out texts (6/class)** by probability argmax.
Zero-division metric behavior is explicit. The full local report is
`.runtime/classification/evaluation.json`; these are actual measured test metrics:

| Metric | Value |
|---|---:|
| Accuracy | 1.0000 (18/18) |
| Macro precision | 1.0000 |
| Macro recall | 1.0000 |
| Macro F1 | 1.0000 |

| Class | Precision | Recall | F1 | Test support |
|---|---:|---:|---:|---:|
| invoice | 1.0000 | 1.0000 | 1.0000 | 6 |
| contract | 1.0000 | 1.0000 | 1.0000 | 6 |
| form | 1.0000 | 1.0000 | 1.0000 | 6 |

Confusion matrix, rows actual / columns predicted, order **invoice, contract, form**:

```text
6 0 0
0 6 0
0 0 6
```

**This perfect score describes only a tiny synthetic text test split with obvious lexical cues.**
It is not a real-world accuracy claim, OCR quality metric, or performance on arbitrary documents.
No test sample or smoke output was used to retune the model or threshold after evaluation.

#### Phase 4 checks and real verification

- Full `.venv/Scripts/python.exe -m pytest backend/tests -q`, with `TEST_DATABASE_URL` read from
  local configuration and `RUN_REAL_OCR=1`: **146 passed, no skips**, 16.23 seconds. Existing
  ingestion/OCR checks remain green, including real PaddleOCR. Three existing upstream warnings
  remain visible (Starlette/httpx, AnyIO alias, missing ccache); none were suppressed.
- Phase 4 tests cover all classes, probability/provenance validation, threshold equality and
  review routing, missing/empty OCR, invalid adapters, failures, saved OCR, classification/history,
  idempotency/reprocessing, API empty/low/missing cases, tiny real-model train/serialize/load/predict,
  shared preprocessing, version changes, hand-computed metrics and split/leakage validation.
  PostgreSQL tests verify classification round-trip, UTC serialization, low-confidence state,
  failure/retry/history, fresh-app retrieval and rollback of a rejected classification commit.
- Migration `alembic -c backend/alembic.ini upgrade head` succeeded on configured local PostgreSQL;
  `alembic ... current` reports **0003_classification (head)**. Isolated-schema tests passed
  upgrade/downgrade/re-upgrade and ORM/schema parity. Existing user documents were not reprocessed.
- `npm.cmd run lint` and `npm.cmd run build`: passed (TypeScript and Vite 7.3.6). No new browser
  interaction/visual audit was performed; frontend validation is lint/build and real API checks.
- `pip check`, `compileall`, and `git diff --check`: passed. Environment, uploads, OCR output,
  joblib artifacts, caches, runtime logs/reports and build outputs remain ignored.
- Real `smoke_classification.py` was executed successfully, including a final run after the full
  suite. It started/stopped its own hidden Uvicorn server, uploaded independent synthetic files,
  used real cached PaddleOCR mobile/English models on CPU, and verified each classification from
  an independent PostgreSQL connection. API probabilities exactly matched direct sklearn
  `predict_proba` on the saved OCR text, including model/dataset/config metadata. Matching process
  requests reused the completed run. Final report: `.runtime/classification/smoke.json`,
  `2026-09-18T09:33:24.722150+00:00`.

| Real uploaded sample | Predicted type | Selected probability | Document state |
|---|---|---:|---|
| Invoice PNG | invoice | 0.6231546119 | COMPLETED |
| Contract JPEG | contract | 0.6502262771 | COMPLETED |
| Form PDF | form | 0.5232675592 | NEEDS_REVIEW |
| Unrelated synthetic text PNG | contract | 0.3588376425 | NEEDS_REVIEW |

The form demonstrates that a correct label can be low confidence. The unrelated-text label is
the closed-set model's argmax, **not a claim that this sample is a contract**; it validates the
review policy. Final synthetic IDs: invoice `ca237f8a-14c8-415d-8bb2-c3920a651e66`, contract
`1e497230-ea93-4ca4-81b6-7f951e4a2a8d`, form `856d20fa-e6c3-42cf-93bc-6d7dd2ea7f3c`, unrelated text
`0768be04-e634-4f9d-b9eb-2c487bf7e224`. Earlier smoke attempts also left synthetic records only.

#### Measured Phase 4 performance and limitations

Environment: Windows 11 build 22631, Python 3.12.14, Intel i5-1035G1 as previously verified,
CPU-only OCR with two threads and cached official models. Training fit on 45 texts took **0.0443 s**.
Warm-dependency artifact load during evaluation took **0.0134 s**; evaluation on 18 texts took
**0.0104 s**, including **0.0037 s** for batched prediction. Cold standalone joblib load in the
final smoke process, including sklearn imports, took **2.4133 s**. These timings have different
boundaries and are informational observations, not latency targets.

| Sample | OCR s | Full processing s | Classification stage s | Direct model inference s | Upload-to-result s |
|---|---:|---:|---:|---:|---:|
| Invoice PNG, cold backend model | 8.9550 | 17.0211 | 0.015016 | 0.002822 | 17.2676 |
| Contract JPEG, warm | 10.0767 | 10.1528 | 0.001785 | 0.002221 | 10.1991 |
| Form PDF, warm | 8.2332 | 8.3676 | 0.001021 | 0.001786 | 8.5105 |
| Unrelated text PNG, warm | 1.1403 | 1.1815 | 0.001999 | 0.001533 | 1.2887 |

Samples are single-page 1400-pixel-wide generated documents, variable height from their lines;
the PDF renders at 144 DPI. Full processing excludes queue wait/final commit, but includes OCR
preparation/initialization and the saved-OCR transaction. Classification stage includes lazy
loading when needed, validation and output construction, excluding the completion transaction.
Direct inference is a separate prediction on the same OCR text. These are individual observations,
not a statistically stable throughput benchmark.

- Small, single-author synthetic English corpus; limited layout diversity, mostly unfilled forms,
  short contract excerpts, few OCR corruptions. Balanced labels here do not establish balance in
  future data. The perfect synthetic score must not be generalized to real documents.
- OCR omissions/noise can alter classification; the real form has a lower probability than the
  review cutoff. No multilingual, handwriting, long-document robustness, probability calibration,
  unknown-class detector, real-corpus validation or business-risk threshold calibration is claimed.
- Review flag/display only; no correction workflow or review editor. A user can reprocess via
  the existing endpoint. Extraction and all Phase 5+ functionality remain unimplemented.
- Local trusted model artifacts, single-process runner, existing crash/uncertain-commit and
  orphan-artifact limitations remain. Missing models require local training and app restart.
  Reclassification currently reruns OCR. No cloud/infrastructure expansion was needed.

Phase 4 is complete on the executed automated, migration, held-out evaluation, and real persisted
OCR/classification evidence above. **Phase 5 — Structured field extraction — is next, not started.**

### 2026-09-18 — Phase 3 completion and user-reported manual verification

- The user confirmed successful manual Phase 3 verification with real local PDF and image documents: PaddleOCR executed, returned correct OCR text, provider-derived confidence, and normalized bounding boxes, and processing reached `COMPLETED`.
- The user confirmed that OCR results and processing runs are persisted in PostgreSQL. Manual reprocessing creates a new run, preserves previous runs, and makes the newest successful run the current result while retaining the original uploaded document.
- The user confirmed that no Phase 4 classification functionality was implemented. Together with the previously recorded automated, PostgreSQL, migration, frontend, and real OCR checks, this manual acceptance confirms Phase 3 complete. Phase 4 — Baseline document classification — remains not started.

### 2026-09-18 — Phase 3 reported results 404 investigation

- Reproduced the reported UUID's `404 DOCUMENT_NOT_FOUND` on both metadata and results endpoints, directly on port 8000 and through the frontend proxy on port 5173. An exact parameterized lookup in the configured `documind.public.documents` on port 5432 found no row for that UUID. The document returned by the list endpoint differs at its fifth UUID character: the persisted character is `d`, while the reported request used `c`. Using the actual listed UUID returns HTTP 200 and `COMPLETED` from both endpoints and both ports. This was a transcribed UUID mismatch, not a backend lookup defect; the remedy is to use the ID returned by upload/list unchanged.
- Verified that `document_service` and `processing_service` both construct their repositories from `request.app.state.sessions`, configured once by `create_app` from the same settings/engine. Both repositories query the same `DocumentRow` mapping. Route parameters and PostgreSQL values are Python `UUID` objects; the document repository's primary-key lookup and processing repository's equality lookup both return the correct persisted document. No database/session configuration, lookup validation, application code, user document, or OCR result was changed.
- Added `test_listed_document_results_require_exact_uuid` in `backend/tests/test_processing_postgres.py`, parameterized for documents without OCR runs and documents with completed runs. It uses generated synthetic UUIDs with the same fifth-character `d`/`c` difference, real endpoint dependencies, and real repositories in an isolated PostgreSQL schema. It verifies list -> metadata/results consistency, the shared configured session factory/search path, direct repository UUID round trips, uppercase UUID equivalence, 404 for the different valid UUID, and 422 for malformed UUIDs. No private identifier or document contents are committed. Both cases pass against the existing implementation; this is regression coverage for the reported scenario, not a falsely claimed failing-before/passing-after application fix.
- Targeted regression command: `pytest backend/tests/test_processing_postgres.py -q -k listed_document_results` with `TEST_DATABASE_URL`: **2 passed**. Full backend command: `.venv/Scripts/python.exe -m pytest backend/tests -q` with PostgreSQL and `RUN_REAL_OCR=1`: **100 passed, no skips, 3 existing upstream warnings**, including real PaddleOCR. `git diff --check` passed. Frontend checks are not applicable to this tests/documentation-only change. Phase 3 scope is unchanged; Phase 4 remains unstarted.

### 2026-09-18 — Phase 3 OCR pipeline and processing jobs

- Implemented only Phase 3. Added framework-independent OCR/page/line/geometry contracts, `OCRProvider`, `ProcessDocument`, processing repository/job contracts, a PaddleOCR adapter, and a single in-process CPU worker. API/application/domain code does not import PaddleOCR, OpenCV, PDFium, or NumPy. No classifier, extraction, review, comparison, RAG, external queues, or future-phase tables were added.
- Verified the existing environment before choosing dependencies: Windows 11 x64, project virtual environment Python 3.12.14. The system `py` launcher separately lists Python 3.14; use `.venv/Scripts/python.exe` for this project. Windows cp312/ABI-compatible wheels resolved and installed successfully. Pinned PaddleOCR 3.3.3, PaddlePaddle 3.2.2, PaddleX 3.3.13, NumPy 2.2.6, OpenCV contrib 4.10.0.84, and pypdfium2 5.13.0. The fixed 3.3 OCR/PaddleX family was selected deliberately; it is not a claim to use the latest release. `pip check` passed. No substitute OCR engine was needed.
- Real inference uses official `PP-OCRv5_mobile_det` and `en_PP-OCRv5_mobile_rec`, CPU with two threads and MKL-DNN disabled. Optional document orientation, unwarping, and text-line orientation models are disabled. The result includes package versions, model names, and SHA-256 over the two models' inference JSON, weights, and YAML configuration. Smoke-test fingerprint: `6a8a888a6c8a3e7be12c98f86b58f8581066fb7ee04c8190d948b2d9f45c7bd7`.
- Added one-page-at-a-time PDF rendering at configurable 144 DPI with pypdfium2's bundled PDFium. Serialized PDFium calls follow its threading constraint. Page/bitmap handles are explicitly closed; tests caught and fixed unsupported page context-manager usage. Image preparation applies EXIF orientation and RGB-to-BGR conversion only. Stored bytes are rechecked against size/checksum and existing format/page/pixel limits; PDF render pixels are bounded before allocation.
- Preserved one-based page numbers, rendered pixel dimensions, provider-ordered lines and page text, normalized enclosing boxes, actual line recognition `rec_scores`, per-page inference time, and run duration. No word-level geometry/confidence is fabricated. Raw Paddle JSON and rendered PNGs are saved through private opaque-key storage and referenced internally; API schemas exclude those keys and raw provider objects. Blank pages may have zero lines; no confidence threshold or arbitrary `NEEDS_REVIEW` rule is introduced.
- Centralized lifecycle transitions for `UPLOADED -> QUEUED -> PROCESSING -> COMPLETED/FAILED`, including retry and scheduling failure. The canonical enum includes `NEEDS_REVIEW` but Phase 3 never emits it. Domain tests cover valid/invalid transitions and finite confidence/box bounds.
- Automatic scheduling defaults on, after document creation commits. Upload responds with the committed `UPLOADED` creation snapshot; get/results return live state. The runner accepts at most eight jobs including the running one, uses one thread, and gives each job its own database session. Queue saturation or scheduling failure preserves the upload; manual retry remains available. Tests cover failure both before run reservation commits and during dispatch.
- Added `POST /api/v1/documents/{id}/process` (202) and `GET /api/v1/documents/{id}/results` (200). Unknown IDs return 404; active/ineligible processing returns stable 409; manual scheduling failure returns 503. Results expose `latest_run` and `current_run`, null before processing. Error text is fixed and safe; provider/database exception strings are not returned or logged.
- Idempotency uses `(document_id, pipeline_version)` with a persisted config fingerprint and increasing attempt numbers. A matching completed request reuses its run without inference. `?reprocess=true`, failed attempts, or changed configuration create a new run. Document row locks and partial unique indexes prevent duplicate active/current runs. Failed reprocessing keeps the previous successful result current. Previous successful payloads remain immutable; only their current flag changes. Duplicate job delivery does not execute a finished/claimed run again.
- Added migration `0002_ocr_processing`: expanded document lifecycle constraint plus one `processing_runs` table with JSONB config/OCR payload, timestamps, safe failure metadata, and unique active/current indexes. Applied to the user's configured local PostgreSQL 18.6 database; `alembic current` reports `0002_ocr_processing (head)`. Isolated-schema integration tests verify upgrade/downgrade/re-upgrade and ORM/schema parity. No original documents were deleted or processed by these checks; live smoke tests create synthetic documents only.
- Preserved artifacts on result-persistence errors because a lost COMMIT acknowledgment can have an unknown outcome. A regression test simulates commit followed by connection loss and proves the committed result still has its artifacts. Definite OCR failures clean up newly rendered artifacts; originals always remain. Retained unreferenced artifacts after persistence errors require offline reconciliation, consistent with the existing filesystem/database transaction limitation.
- Added explicit offline interrupted-run recovery: `backend/scripts/recover_processing.py --backend-stopped`. Stop every backend instance first; it marks abandoned `QUEUED`/`PROCESSING` runs `FAILED` without deleting originals or successful results. Recovery is tested in an isolated schema and was not run against active user jobs.
- Frontend changes are limited to all canonical status types, neutral/failed/completed status colors, two-second polling while list/detail data contains active jobs, and a manual detail refresh. No OCR review/editor, field extraction, confidence dashboard, or classification UI was added. OCR inspection uses Swagger/results API.
- README and `.env.example` now document setup, pinned Windows dependencies, first-use model downloads/cache, queue/CPU/render settings, API/retry semantics, single-process operation, crash recovery, and real smoke commands. Architecture, requirements, roadmap, and project guidelines required no changes.

#### Phase 3 checks executed

- Baseline before implementation: **57 passed** with PostgreSQL enabled, including every existing Phase 1-2 test.
- Final `.venv/Scripts/python.exe -m pytest backend/tests -q`, with `TEST_DATABASE_URL` supplied from local configuration and `RUN_REAL_OCR=1`: **98 passed, no skips, 3 upstream warnings**. Database fixtures create/remove only their own random schemas. This includes domain, rendering/resource limits, application/API fakes, real PostgreSQL background processing/retry/restart/concurrency/rollback/recovery, and the real PaddleOCR CPU adapter test.
- Ordinary tests never load OCR models. PostgreSQL tests require explicit `TEST_DATABASE_URL`; real Paddle is separately opt-in with `RUN_REAL_OCR=1`. The real adapter test compares normalized confidence directly to persisted raw `rec_scores`, checks recognizable text and boxes, and verifies provider/model metadata.
- `npm.cmd run lint`: passed. `npm.cmd run build`: TypeScript and Vite build passed. No new browser interaction test was performed; Phase 3 frontend verification is lint/build, while real lifecycle/API behavior is covered separately.
- `.venv/Scripts/python.exe -m alembic -c backend/alembic.ini upgrade head`: succeeded on local PostgreSQL 18.6. `... current`: `0002_ocr_processing (head)`.
- `.venv/Scripts/python.exe backend/scripts/smoke_ocr.py`: passed using a real hidden Uvicorn process, real CPU OCR, HTTP endpoints, and independent PostgreSQL queries. Synthetic PNG, JPEG, and a two-page PDF each completed, returned exact recognizable test phrases, preserved original bytes, persisted valid normalized boxes/provider confidence, reused the matching completed run, and successfully reprocessed into a second retained run with exactly one current result. Live polling observed `UPLOADED`, `PROCESSING`, and `COMPLETED`; the brief `QUEUED` state is verified deterministically in scheduling/API tests rather than falsely claimed as captured by polling.
- Synthetic PDF rendered-page PNGs were visually inspected: correct page-one/page-two text, orientation, legibility, and no clipping. Page order/text association is also asserted by the live smoke script.
- `.venv/Scripts/python.exe backend/scripts/smoke.py`: original ingestion-only HTTP smoke passed for PDF/PNG/JPEG. It now explicitly disables automatic processing in its child server so it still verifies the Phase 1 creation snapshot.
- `pip check`, source compilation, and `git diff --check`: passed. Ignore checks cover `.env`, virtual environment, generated outputs, model cache, and runtime reports; no secrets, models, private documents, or generated OCR artifacts were added to tracked files.

#### Measured real OCR performance (2026-09-18)

Environment: Intel Core i5-1035G1, four physical/eight logical CPUs, 7.78 GiB reported RAM, Windows 11 build 22631, Python 3.12.14, PostgreSQL 18.6. CPU inference uses two threads, no GPU, PaddleOCR 3.3.3/PaddlePaddle 3.2.2 and the official English/mobile models above. Synthetic images are 1000 x 260 pixels; PDF contains two such image pages rendered at 144 DPI. One original run plus one explicit reprocess per format; these are tiny development smoke samples, not quality evaluation or throughput benchmarks.

| Input | Condition | OCR seconds/page | Processing seconds | Upload-to-result seconds | Warm reprocess seconds |
|---|---|---|---|---|---|
| PNG, one page | Cold process; models already cached | 0.869 | 5.631 | 5.832 | 0.999 |
| JPEG, one page | Warm model | 0.802 | 0.828 | 0.920 | 0.804 |
| PDF, two pages | Warm model | 0.843 / 0.774 | 1.680 | 1.806 | 1.699 |

- Per-page times measure provider inference. Processing duration includes storage/preparation/model initialization/OCR and is recorded immediately before the completion transaction; it excludes queue wait and final database commit. Upload-to-result time includes HTTP upload, scheduling, polling, and result retrieval. No latency threshold is imposed.
- Initial standalone compatibility probe, before these measurements, took 23.10 seconds for model initialization plus first downloads, then 0.980/0.816 seconds for two inferences on one synthetic PNG. It returned `DOCUMIND TEST 123` with provider `rec_scores` 0.9974857568740845. This is one line's provider confidence, not an accuracy metric.
- Live script output is retained in ignored `.runtime/phase3-smoke-report.txt`; source-backed summary measurements are recorded here. Synthetic persisted document IDs: PNG `925593e3-90c9-4c37-88d3-51d3fa660033`, JPEG `51684b2d-ab76-476d-82a4-a2468e9a0cf1`, PDF `7f89dec7-4716-4c84-b4e9-ddce495f7ffe`. No real/private user document was used for OCR verification.

#### Phase 3 limitations

- Local, single-process, bounded in-memory execution only. Graceful shutdown drains jobs; hard shutdown/database failure may need the offline recovery command. There is no external queue, automatic restart recovery, cancellation, or hard inference timeout. First use requires network/model cache access; Windows CPU behavior outside the pinned tested environment is not verified.
- English printed text is the target. Handwriting, multilingual text, arbitrary rotated scans, and complex multi-column reading order are unverified. Scores are provider recognition confidence, not calibrated correctness probabilities. OCR quality datasets, CER/WER, classification, extraction, review, and evaluation dashboards remain in their owning future phases.
- The PDF/image parsers and OCR execute in-process; existing upload/page/pixel limits are enforced, but adversarial CPU/memory isolation is not implemented. Rendering keeps raster memory bounded by page rather than loading all page images; normalized text/raw results accumulate across the configured page limit.
- Raw OCR/normalized payloads and rendered artifacts can contain sensitive document text and remain private local development data. No raw-artifact download/viewer endpoint or retention/garbage-collection job was introduced. Filesystem/database commits are not atomic; persistence errors/crashes may leave artifacts for manual reconciliation.
- Existing Starlette/httpx and AnyIO deprecation warnings remain visible. Real Paddle additionally warns that ccache is absent; inference succeeds, and no compiled custom operators were required. No warnings were suppressed to obtain passing tests.
- Phase 3 is complete based on executed tests, real persisted OCR, and documented limitations. Phase 4 is next and has not been started.

### 2026-09-18 — Phase 2 completion and user-reported browser verification

- The user confirmed successful manual Phase 2 verification with locally running PostgreSQL and the application connected to the `documind` database.
- Browser PDF upload works. Metadata is persisted in `public.documents`, including UUID, original filename, detected media type, size, and the expected `UPLOADED` status.
- The frontend lists persisted documents; document data remains server-backed rather than frontend-only.
- The user confirmed that no OCR, AI processing, classification, extraction, review, or future-phase UI was added.
- Marked Phase 2 complete based on this user-reported manual verification and the previously recorded passing frontend lint/build, 57 backend tests, and live HTTP persistence checks. This entry records the user's verification; it does not claim an automated browser session or test run.
- Phase 3 — OCR pipeline and processing jobs — remains not started.

### 2026-09-18 — Local upload database configuration fix

- Investigated a browser upload failure, `Document metadata could not be saved`. The live document-list endpoint also returned HTTP 503. The root `.env` was absent, so default configuration targeted `localhost:5432/documind`, while the existing migrated local database was running at `127.0.0.1:55433/documind_phase2` with 12 records.
- Created an ignored local `.env` pointing to that database and its matching `.runtime/phase2-uploads` storage directory. No credentials or machine-specific configuration were added to tracked example files. Restarted Uvicorn, including stopping the old reload child that retained the previous settings.
- Verified through the frontend proxy: document list HTTP 200, synthetic PDF upload HTTP 201 with `UPLOADED`, and matching persisted detail/list results. The user's original PDF was not accessed or uploaded during verification. Browser acceptance verification was pending at that time and was subsequently confirmed by the user above.
- This fixes local runtime configuration, not backend/frontend application logic. For future starts, keep PostgreSQL running, retain the ignored root `.env`, and use the README backend command; `.env.example` alone is not loaded.

### 2026-09-18 — Phase 2 frontend implementation and HTTP verification

- Added React/Vite/TypeScript/Tailwind, React Router, ESLint, a lockfile, and a neutral responsive application shell with accessible navigation and visible focus states. No component library or frontend test framework was introduced.
- Added `/documents`, `/upload`, and `/documents/:id`, root redirect, and a not-found page. List/detail requests use the existing backend and refetch on navigation/refresh; there is no browser-persisted document cache.
- Added a typed API layer aligned with the Phase 1 response schema and structured errors. `GET /health` powers checking/connected/unavailable status with a manual recheck. It does not claim database readiness.
- Added ten-row pagination using backend limit/offset. An eleventh lookahead row enables Next without assuming a total count. Loading, empty, error, retry, missing-document, and disabled states are implemented.
- Added file picker/drop zone, selected-file summary/removal, extension/empty-file validation, optional configured size feedback, duplicate-submit guard, indeterminate upload/saving state, backend error messages, and persisted metadata/status on success. Success links open the detail page or a freshly fetched list.
- Detail shows original filename, detected media type, size, page count, status, timestamps, UUID, and checksum. Storage paths/keys are not exposed. No fake results, OCR, jobs, or future-phase placeholder UI were added.
- Vite dev/preview proxy forwards `/api` and `/health` to FastAPI. Backend source/configuration was unchanged. README documents URLs, commands, optional size-limit synchronization, proxy configuration, and the remaining browser checklist.
- Commands: `cd frontend; npm.cmd ci` installs locked dependencies, `npm.cmd run dev` serves port 5173, `npm.cmd run lint` checks source, `npm.cmd run build` checks TypeScript and builds, and `npm.cmd run preview` serves port 4173. Use `npm.cmd` when PowerShell execution policy blocks `npm.ps1`.

#### Checks executed

- `npm.cmd install`: succeeded; npm reported zero vulnerabilities. Dependencies and resolved versions are recorded in `frontend/package-lock.json`.
- `npm.cmd run lint`: passed with no warnings after moving formatting helpers out of the component module.
- `npm.cmd run build`: passed (TypeScript + Vite 7.3.6 production build).
- `.venv/Scripts/python.exe -m alembic -c backend/alembic.ini upgrade head`: succeeded against an isolated PostgreSQL 17.11 database.
- `.venv/Scripts/python.exe -m pytest backend/tests -q` with `TEST_DATABASE_URL`: **57 passed**, no skips, two existing upstream deprecation warnings.
- Started real Uvicorn at `127.0.0.1:8000` and Vite at `127.0.0.1:5173`. Live HTTP checks through the Vite proxy passed for `/health`, frontend deep-link fallback, empty list, synthetic PDF/PNG/JPEG uploads, metadata retrieval, structured validation/404 errors, and 12-record pagination with lookahead.
- A fresh HTTP client retrieved identical metadata. Stopping the backend produced a proxy error; restarting it restored health and all persisted records. This verifies real PostgreSQL persistence across backend restart.
- `npm.cmd run preview`: started the production build on port 4173. HTTP checks passed for SPA fallback, emitted JavaScript/CSS assets, proxied health, and persisted document listing. `git diff --check` passed; generated assets, dependencies, environment files, and runtime data are ignored.
- Test-only cluster/data, generated fixtures, HTTP verification script, and uploads are under ignored `.runtime/phase2-*`. The existing Phase 1 cluster was not modified. The test PostgreSQL instance listens only on `127.0.0.1:55433`; this is not the required application setup.
- **Automated browser verification was unavailable:** the UI tool reported no connected apps/browsers, and opening the in-app browser returned `Browser is not available: iab`. HTTP checks alone did not validate browser interactions. The user subsequently confirmed successful manual Phase 2 verification as recorded above, resolving the browser acceptance blocker.

#### Phase 2 limitations

- Upload state is indeterminate; no byte-progress percentage, cancellation, or upload resume is implemented. Navigating away can lose the in-progress confirmation; users should check Documents before retrying a timed-out upload.
- The backend exposes no upload-limit endpoint. Optional frontend size feedback must be configured to match the backend; otherwise the server alone enforces size limits.
- Offset pagination can shift if new documents arrive between pages; there is no total-count API, search, or sorting control.
- No preview/download endpoint, authentication, OCR, AI results, or processing jobs. Existing Phase 1 limitations still apply.
- Production reverse-proxy/SPA hosting remains a later deployment concern. No separate automated visual/accessibility audit was performed; Phase 2 completion incorporates the user's manual verification above.

### 2026-09-17 — Windows pytest temporary-directory permissions regression

- Reproduced all seven original storage-test setup errors under the Windows `admin` account. The traceback stopped in pytest's `getbasetemp()`/`os.scandir()` at `%TEMP%/pytest-of-admin`, before any storage test body executed.
- Confirmed that both processes inherited the same temporary-directory/user-name settings while the shared pytest root and backend pytest cache were owned by `CodexSandboxOffline` with restrictive ACLs. The sandbox account passed the same tests. Unsafe key strings were test labels, not the paths causing the PermissionError.
- Added an early test configuration hook allocating a fresh `TemporaryDirectory` per run, with separate child directories for pytest fixtures and cache. Cleanup touches only that run's allocated directory; existing shared directories/ACLs remain untouched. Explicit `--basetemp` and cache settings are respected. Default cross-run cache persistence is intentionally disabled and documented in README.
- Kept `LocalDocumentStorage` unchanged: only opaque 32-character lowercase hexadecimal keys are accepted, before filesystem access. Expanded tests cover POSIX/Windows traversal, absolute paths, drive-relative paths, UNC/device paths, and a sibling escape target created entirely inside `tmp_path`. Mocked path operations prevent unsafe synthetic targets from reaching the filesystem if validation regresses; descriptive parameter IDs keep test names independent of raw path strings.
- Validation: the complete suite without a database passed under both accounts (**54 passed, 3 explicit PostgreSQL skips**). From `backend/`, `python -m pytest tests -q` with `TEST_DATABASE_URL` configured then passed under the formerly failing Windows account: **57 passed, no skips**, two existing upstream deprecation warnings. The isolated PostgreSQL instance was stopped afterward.
- Changes were limited to `backend/tests/conftest.py`, `backend/tests/test_storage.py`, README, and this progress log. Phase 2 remains not started.

### 2026-09-17 — Phase 1 backend foundation and ingestion

- Implemented Python 3.12/FastAPI, centralized environment configuration, and `GET /health` without a database dependency.
- Added immutable document metadata with UUID IDs, SHA-256 checksums, UTC timestamps, page count, and only `UPLOADED` status.
- Added application create/get/list use cases, small document repository/storage contracts, local opaque-key storage, SQLAlchemy persistence, and Alembic migration `0001_documents` (documents plus Alembic's version table only).
- Implemented PDF/PNG/JPEG multipart upload, content signatures and parser validation, safe display filenames, configurable file/page/pixel limits, and a bounded request body including chunked uploads.
- Added explicit cleanup after failed metadata persistence, including a distinct safe error when cleanup itself fails. API responses omit storage keys and local paths.
- Added generated synthetic fixtures, offline unit/API/storage tests, isolated-schema PostgreSQL integration tests, and a live HTTP smoke script.
- Fixed a PostgreSQL timezone round-trip bug found by the integration test: the database adapter converts session-local timestamps to UTC before constructing domain objects. The test explicitly uses an Asia/Bangkok session.
- Updated README setup/API/test instructions, `.env.example`, and `.gitignore`. No Phase 2 or later features, placeholder jobs, or external queue infrastructure were added.
- No architecture deviation was needed. Pillow/pypdf perform ingestion validation only, without OCR, rendering, or extraction. PostgreSQL binaries were downloaded with permission into ignored `.runtime/` solely for local verification; no system service or Docker configuration was added.

### 2026-09-17 — Documentation synchronization

- Synchronized the canonical lifecycle across documentation: `UPLOADED`, `QUEUED`, `PROCESSING`, `NEEDS_REVIEW`, `COMPLETED`, and `FAILED`. Transitions remain centralized.
- Scoped Phase 1 to validated upload, persistence, metadata retrieval, and a simple `GET /health` returning `{"status": "ok"}`. Phase 1 uses only `UPLOADED` and has no processing/job placeholders.
- Assigned the processing/job boundary to Phase 3 alongside OCR. Successful upload creates the document first; automatic scheduling may then begin. The process endpoint primarily supports retry/reprocess/development.
- Assigned request/correlation IDs, structured logs, advanced observability, and separate liveness/readiness endpoints exclusively to Phase 8.
- Narrowed initial contract extraction to contract number, title, party A, party B, effective date, expiry/termination date, contract value, and governing law, without Phase 5 LLM summarization.
- Replaced unmeasured performance thresholds with hardware/workload-documented measurements and a Phase 8 benchmark report.
- Kept Phase 7 quality evaluation and optional Phases 9/10 in scope without adding application features or infrastructure.

### 2026-09-02 — Phase 0 planning foundation

- Defined the product requirements, initial users, functional scope, non-functional constraints, and explicit exclusions.
- Selected a modular-monolith, ports-and-adapters architecture with domain-level contracts for OCR, classification, extraction, jobs, repositories, and file storage.
- Defined normalized bounding-box and confidence conventions.
- Chose to preserve immutable raw predictions separately from reviewed/corrected values.
- Split delivery into small phases from ingestion through evaluation, packaging, comparison, and RAG.
- Added repository working conventions and phase-level quality gates.
- Confirmed that no application features were implemented in this phase.

## Decisions and assumptions

- English printed documents are the initial target; handwriting and multilingual support are deferred.
- Initial formats are PDF, PNG, and JPEG, with configurable defaults of 20 MB and 50 pages.
- The first deployment is a modular monolith, not microservices.
- PostgreSQL stores metadata and structured/versioned results; original binaries use local storage behind an interface initially.
- Processing/job boundaries begin in Phase 3, with no dispatcher or placeholder job interfaces/classes in Phase 1. A simple in-process background runner may be used; synchronous MVP processing is acceptable when justified by measured performance. External queue infrastructure is not required.
- Authentication and multi-tenancy are not part of the first portfolio release, but reviewer identity and authorization have architectural insertion points.
- Synthetic or redistributable documents will be used for development and evaluation.

## Phase checklist

| Phase | Status | Evidence/notes |
|---|---|---|
| 0. Planning foundation | Complete | Six requested documentation files created |
| 1. Backend foundation and ingestion | Complete | Latest suite: 57 tests passed, including Windows-account regression and PostgreSQL checks; original live HTTP smoke passed |
| 2. Frontend shell and upload | Complete | Lint/build passed; 57 backend tests passed; live proxy/persistence checks passed; user confirmed browser upload, PostgreSQL metadata persistence, server-backed listing, and Phase 2 scope |
| 3. OCR pipeline | Complete | 100 backend tests passed including PostgreSQL and real PaddleOCR; lint/build passed; live PNG/JPEG/two-page PDF OCR persisted and reprocessed; user confirmed real local PDF/image OCR, persistence, run history/current-result behavior, and original-file retention |
| 4. Classification | Complete | 146 tests passed including PostgreSQL/real OCR; lint/build passed; migrated, trained, evaluated 18 held-out texts, and verified persisted real invoice/contract/form classifications plus low-confidence routing |
| 5. Field extraction | Complete | Bilingual extraction for invoice, contract, form; rule-based spatial & regex extractor; 9/9 real fields verified |
| 6. Review and correction | Complete | HITL split-screen & stacked layout, optimistic locking (revision), immutable AI prediction audit trail, 169 tests passed |
| 7. Evaluation | Complete | CER (0.54%), WER (3.23%), Accuracy (100%), Extraction F1 (1.0), zero-fabrication reports/baseline.md, 179 tests passed |
| 8. Packaging and polish | Complete | Dockerfiles, compose.yaml, /health/live & /health/ready, correlation IDs, demo script, ADRs, latency benchmark (186 tests passed) |
| 9. Document comparison | Not started | Optional extension |
| 10. RAG document Q&A | Not started | Optional extension |

## Verification

- Documentation re-read and manual consistency review: completed on 2026-09-17; Phase 1 remains independently demonstrable with no future-phase infrastructure.
- Automated documentation checks: passed for canonical state spelling, removal of stale requirements, balanced code fences, whitespace, all five required elements in each of the 11 phases, Phase 1 health/observability scope, README links, and a documentation-only file inventory.
- Phase 1 backend suite: `.venv/Scripts/python.exe -m pytest backend/tests -q` with `TEST_DATABASE_URL` pointing to the isolated local PostgreSQL instance: **49 passed**, no skips, two upstream deprecation warnings. Without that variable, PostgreSQL tests skip explicitly.
- Database verification: PostgreSQL 17.11; migration upgrade/downgrade/re-upgrade and ORM/schema parity passed. Tests confirmed persistence across application recreation/new database connections and binary cleanup after an actual rejected SQL insert.
- CLI migration: `.venv/Scripts/python.exe -m alembic -c backend/alembic.ini upgrade head` succeeded; `alembic ... current` reported `0001_documents (head)`.
- Live HTTP verification: `.venv/Scripts/python.exe backend/scripts/smoke.py` started Uvicorn, verified `/health`, uploaded synthetic PDF/PNG/JPEG files, and verified create/get/list for each. The script stopped its Uvicorn process afterward.
- Dependency check: `.venv/Scripts/python.exe -m pip check` passed with no broken requirements.
- Source compilation: `python -m compileall -q backend/app backend/migrations backend/scripts backend/tests` passed. Repository inventory and ignore checks confirmed that `.env`, virtual environments, caches, PostgreSQL runtime data, and synthetic uploads are excluded; no secrets or runtime files are tracked. No OCR/job/frontend modules were added.
- The temporary PostgreSQL instance was stopped after verification. Its binaries, test cluster, and three synthetic smoke uploads remain under ignored `.runtime/` for local inspection; it is not an installed service or the application's required setup.
- Phase 1 frontend checks were not applicable at that time. Current Phase 2 verification is recorded above.

## Phase 1 limitations

- Local single-server development storage and no authentication; do not deploy publicly as-is.
- PDF validation checks signature, parsing, page structure/count, and dimensions; it does not render every content stream, scan for malware, or isolate parser CPU/memory usage. Encrypted PDFs and animated images are rejected.
- Handled persistence failures remove stored bytes; abrupt process termination or filesystem cleanup failure can still require manual reconciliation. No cross-system transaction or recovery worker is introduced.
- Request size is bounded; concurrent upload quotas/rate limiting are not implemented.
- Two visible dependency warnings remain: Starlette's TestClient deprecates its `httpx` integration and uses a deprecated AnyIO portal alias. They do not fail the suite and are not suppressed.
- Dependencies must be installed before offline tests run. Real database checks require a local PostgreSQL instance and a test user with schema creation rights.

## Known risks to revisit

- PaddleOCR installation and CPU performance vary by platform; validate early in Phase 3 and document the supported environment.
- Useful model evaluation depends on a sufficiently representative, licensed dataset; begin curating the manifest before Phase 4.
- PDF parsing and image decompression require strict resource limits.
- Confidence values from different stages are not automatically calibrated or comparable.
- Contract extraction is less schema-regular than invoice/form extraction; keep the first contract schema narrow and measurable.

## Next implementation slice

Phase 8 is complete. The core portfolio release of DocuMind AI is 100% complete, fully verified, and ready for demonstration. Optional extensions Phase 9 (Document comparison) and Phase 10 (Grounded document Q&A with RAG) are available if requested.
