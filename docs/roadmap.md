# Incremental Roadmap

## Roadmap rules

- Complete phases in order and keep each phase independently demonstrable.
- Do not introduce a library or service until the current phase needs it.
- The listed files are expected, not immutable; document meaningful changes.
- A phase is complete only when its acceptance criteria and tests pass and `progress.md` is updated.
- Canonical lifecycle states are `UPLOADED`, `QUEUED`, `PROCESSING`, `NEEDS_REVIEW`, `COMPLETED`, and `FAILED`. Phase 1 only needs `UPLOADED`; `QUEUED` and active processing states begin in Phase 3. Domain transition rules remain centralized; API/frontend code must not invent states.
- Phases 9 and 10 are optional extensions after the core portfolio release.

## Phase 0 — Planning foundation

**Objective:** Establish scope, architecture boundaries, delivery phases, and working conventions before application code exists.

**Features:** Product requirements; replaceable AI architecture; testing strategy; phased implementation plan; progress log; repository instructions.

**Expected files/modules:** `README.md`, `docs/requirements.md`, `docs/architecture.md`, `docs/roadmap.md`, `docs/progress.md`.

**Acceptance criteria:** All six documents exist; terminology and phase ordering agree; no backend/frontend feature implementation is added; AI providers are separated from application/API code in the design.

**Tests that must pass:** Documentation links resolve; a manual consistency review finds no later feature required by an earlier phase; repository contains no application source or secrets.

## Phase 1 — Backend foundation and document ingestion

**Objective:** Deliver the smallest working backend slice that safely accepts a document and persists retrievable metadata.

**Features:** Python project and FastAPI app; centralized configuration; a simple `GET /health` endpoint returning HTTP 200 with `{"status": "ok"}`; PostgreSQL connection and initial migration; document entity with `UPLOADED` state; local `DocumentStorage` interface and adapter; validated streaming PDF/PNG/JPEG upload; create/get/list metadata endpoints; stable errors; tests. Phase 1 ends after validated upload, persistence, and retrieval. Do not add a job dispatcher, placeholder job classes/interfaces, OCR, or frontend.

**Expected files/modules:** `backend/pyproject.toml`, `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/api/`, `backend/app/application/documents.py`, `backend/app/domain/documents.py`, `backend/app/domain/ports.py` (document repository/storage only), `backend/app/infrastructure/db/`, `backend/app/infrastructure/storage/`, `backend/migrations/`, `backend/tests/`, `.env.example`.

**Acceptance criteria:** A supported synthetic file returns HTTP 201 with a UUID document ID and `UPLOADED` state; bytes are stored under an opaque key; metadata survives an app restart; get/list return the record; invalid type/size returns a stable 4xx error; routes depend on application services, not concrete storage/database code; a failed metadata commit does not leave an untracked permanent upload; `/health` returns the documented response without requiring a database readiness check. The phase is independently demonstrable without processing infrastructure.

**Tests that must pass:** `pytest` unit tests for document/value validation, initial `UPLOADED` state, and create/list/get use cases; API integration tests for `GET /health` (HTTP 200, `{"status": "ok"}`), valid upload, malformed/unsupported/oversized upload, not found, and persistence; storage contract tests including cleanup on failure; migration upgrade test against PostgreSQL.

## Phase 2 — Frontend shell and upload experience

**Objective:** Provide a clean browser workflow for uploading and tracking persisted documents.

**Features:** React/Vite/TypeScript/Tailwind setup; typed API client; upload drop zone/file picker; document list/detail; validation, loading, progress, empty, and error states; accessible navigation.

**Expected files/modules:** `frontend/package.json`, `frontend/vite.config.ts`, `frontend/src/app/`, `frontend/src/features/documents/`, `frontend/src/components/`, `frontend/src/lib/api/`, frontend lint/TypeScript/Tailwind configuration.

**Acceptance criteria:** A user can upload a supported file and see its persisted metadata/status; unsupported files receive useful feedback; refresh retains the server-backed list; primary flow is keyboard usable; no OCR/result UI is faked.

**Tests that must pass:** `npm run lint`; `npm run build`; focused component tests for upload validation/status rendering if a test runner is introduced; backend API tests remain green.

## Phase 3 — OCR pipeline and processing jobs

**Objective:** Convert uploaded documents into normalized, traceable text and geometry without coupling use cases to PaddleOCR.

**Features:** Page rendering and OpenCV preprocessing; `OCRProvider` contract; PaddleOCR adapter; deterministic test-only fake adapter; processing-run records and centralized state transitions; first introduction of the processing/job boundary, including `ProcessingJobDispatcher` when scheduling is used; OCR persistence and retrieval; retries and failure reporting. Automatic processing may be queued after document creation using a simple in-process runner. Synchronous MVP execution is acceptable if measured performance is reasonable and the processing use case remains callable by a future worker. No external queue infrastructure is required. The process endpoint mainly serves manual retry/reprocess/development.

**Expected files/modules:** `backend/app/domain/ocr.py`, processing/job contracts as used, `backend/app/application/process_document.py`, `backend/app/infrastructure/ocr/paddle.py`, `backend/app/infrastructure/imaging/`, `backend/app/infrastructure/jobs/` if an in-process runner is used, database migration, OCR/result API schemas, `backend/tests/fixtures/documents/`.

**Acceptance criteria:** Processing a small PDF and image produces ordered page text, normalized boxes, meaningful provider confidence, and provider version; document creation succeeds before processing is attempted; enabled automatic processing requires no second user action; scheduling failure preserves the uploaded document for retry; centralized state transitions cover `QUEUED` when scheduled, `PROCESSING`, completion/review, and `FAILED`; a provider failure produces safe diagnostics; retry does not duplicate the current run; non-adapter tests use fake OCR without model downloads. Record the chosen execution mode and measured OCR time per page/total processing time; background execution keeps uploads independent of OCR, while synchronous execution must be justified by measurements.

**Tests that must pass:** Unit tests for geometry normalization, centralized state transitions, orchestration, idempotent retry, and failure paths; adapter smoke test on a tiny redistributable fixture; API integration tests for upload-to-processing using a fake provider, retained upload on scheduling failure when scheduling is enabled, and manual retry/reprocess; existing tests and frontend checks.

## Phase 4 — Baseline document classification

**Objective:** Classify OCR output as invoice, contract, or form with a simple, measurable baseline.

**Features:** Versioned labeled dataset manifest; text feature pipeline using scikit-learn (for example TF-IDF plus logistic regression); training/evaluation CLI; `DocumentClassifier` contract and artifact adapter; probabilities/scores and low-confidence threshold; classification persistence and API/UI display.

**Expected files/modules:** `backend/app/domain/classification.py`, `backend/app/infrastructure/classification/`, `backend/app/application/classify_document.py`, `backend/scripts/train_classifier.py`, `data/manifests/`, model metadata/artifact location, migration, frontend status/type components.

**Acceptance criteria:** Pipeline classifies all three types; artifact and dataset/config versions are recorded; low score marks a document for review; swapping the classifier with a fake requires only dependency wiring; training and evaluation avoid test-set leakage; UI labels predictions as machine-generated.

**Tests that must pass:** Unit tests for threshold/routing and orchestration; classifier serialization and tiny-fixture prediction tests; deterministic metric test; API schema/integration tests; `pytest`, `npm run lint`, and `npm run build`.

## Phase 5 — Structured field extraction

**Objective:** Produce explainable, document-type-specific fields linked to OCR evidence.

**Features:** Typed field schemas; `FieldExtractor` contract; baseline rule/layout extractors using labels, regex, spatial relationships, and normalization; invoice, contract, and form extraction; evidence text/boxes and confidence; versioned persistence; result API.

The initial contract fields are contract number, title, party A, party B, effective date, expiry/termination date, contract value, and governing law. Phase 5 excludes LLM summarization; extraction remains source-backed and measurable.

**Expected files/modules:** `backend/app/domain/extraction.py`, `backend/app/application/extract_fields.py`, `backend/app/infrastructure/extraction/`, schema definitions per document type, normalization utilities, migration, result endpoints/schemas.

**Acceptance criteria:** Representative fixtures yield expected core fields; every predicted field has provider/version, confidence, and evidence geometry or an explicit `derived` marker; missing values remain missing; routes/application services do not import extractor libraries; reruns preserve old raw runs and identify the current one.

**Tests that must pass:** Table-driven tests for field schemas and normalization; extractor tests for all three types including missing/ambiguous fields; orchestration tests with a fake extractor; API contract and persistence tests; all prior quality gates.

## Phase 6 — Visual review and correction

**Objective:** Let a person verify evidence and create an auditable corrected result.

**Features:** Page image endpoint/viewer; normalized bounding-box overlays; field editor; document-type correction; low-confidence highlighting; add/remove/confirm actions; review event history; optimistic concurrency; unsaved-change protection.

**Expected files/modules:** `backend/app/domain/review.py`, `backend/app/application/review_document.py`, review migration/routes/schemas, `frontend/src/features/review/`, page viewer and overlay components.

**Acceptance criteria:** Selecting a field highlights the correct page region at different display sizes; corrections do not mutate raw predictions; submitted review records before/after values and revision; stale submissions receive a conflict; corrected values reload as the current reviewed result; keyboard users can complete the core review.

**Tests that must pass:** Domain/application tests for audit events, revisions, and merge rules; API tests for valid review, invalid fields, and stale revision conflict; frontend component tests for box scaling and editor states; one end-to-end fake-AI upload-to-review test; lint/build and backend suite.

## Phase 7 — Evaluation and model reporting

**Objective:** Make OCR, classification, and extraction quality reproducible and visible.

**Features:** Versioned evaluation manifest/split; CER/WER; classification accuracy, macro/per-class precision/recall/F1 and confusion matrix; extraction normalized match and per-field precision/recall/F1; evaluation CLI/report; baseline results and limitations.

**Expected files/modules:** `backend/app/evaluation/`, `backend/scripts/evaluate.py`, `data/evaluation/README.md`, `reports/baseline.md` (small text artifacts only), metric tests.

**Acceptance criteria:** One command evaluates a named dataset/model configuration; report records dataset/model/config versions, sample counts, evaluation date/method, hardware/context, measured metrics, errors, and limitations; metrics distinguish raw predictions from reviewed truth; evaluation data remains separate from training/development data and training metrics are not presented as test performance; failures identify bad manifest entries. Phase 7 consolidates quality evaluation across all three AI stages, extending the classification baseline from Phase 4 without fabricated results.

**Tests that must pass:** Hand-calculated CER/WER tests; classification confusion-matrix/metric tests; extraction normalization and per-field metric tests; manifest validation and leakage checks; full repository quality gates.

## Phase 8 — Packaging, resilience, and portfolio polish

**Objective:** Make the end-to-end system reproducible, observable, and ready to demonstrate.

**Features:** Dockerfiles and Docker Compose; migration/startup workflow; persistent database/upload volumes; configuration documentation; request/correlation IDs across API and processing; structured logs and advanced observability; `/health/live` and `/health/ready` operational endpoints; retry limits; sample-data/demo script; architecture decision records and screenshots; measured performance benchmark report. This phase exclusively owns the advanced observability infrastructure.

**Expected files/modules:** `compose.yaml`, `backend/Dockerfile`, `frontend/Dockerfile`, `.dockerignore`, `.env.example`, `docs/setup.md`, `docs/demo.md`, `docs/decisions/`, `reports/performance.md`, logging/health modules.

**Acceptance criteria:** A clean machine with Docker can start the stack from documented commands; migrations apply; data survives container restart; demo processes and reviews samples for all three types; secrets are not baked into images; failure/retry behavior is visible and bounded; request/correlation IDs connect safe structured logs across API/processing; liveness and readiness distinguish a running process from unavailable dependencies. The benchmark report records hardware, versions, workload/sample counts, measurement method, API/upload/metadata latency, OCR time per page, total processing time per document, and document list latency. Hard targets may be introduced only after real measurements exist.

**Tests that must pass:** Image builds; Compose configuration validation; container health checks including unavailable-dependency readiness behavior; request/correlation propagation and log-redaction checks; end-to-end smoke test; migration from an empty database; documented benchmark execution with recorded measurements, without invented pass/fail latency thresholds; `pytest`, frontend lint/build, and secret/large-artifact repository check.

## Phase 9 — Document comparison (optional extension)

**Objective:** Compare two processed documents using existing normalized outputs and show attributable differences.

**Features:** Select documents; schema-aware field diff; text-section similarity/diff; added/removed/changed results; evidence links; comparison persistence only if useful.

**Expected files/modules:** comparison domain/application modules, API routes/schemas, `frontend/src/features/comparison/`, optional migration.

**Acceptance criteria:** Compatible documents show deterministic field changes with both source references; incompatible types are handled clearly; comparison consumes normalized results rather than rerunning/bypassing the pipeline; no legal conclusions are implied.

**Tests that must pass:** Unit tests for added/removed/changed/normalized values; API tests for valid and invalid pairs; frontend rendering tests; end-to-end comparison fixture; all prior gates.

## Phase 10 — Grounded document Q&A with RAG (optional extension)

**Objective:** Answer questions over reviewed documents with verifiable page-level evidence.

**Features:** Chunking and metadata strategy; embedding/vector retrieval behind ports; ingestion versioning; grounded answer provider; page/box citations; unsupported-answer behavior; small retrieval/answer evaluation set.

**Expected files/modules:** RAG domain ports, ingestion/retrieval/answer application services, infrastructure embedding/vector/LLM adapters, Q&A API, `frontend/src/features/qa/`, evaluation fixtures and report.

**Acceptance criteria:** Answers cite retrieved document/page evidence; an unsupported question returns an explicit insufficient-evidence response; reprocessing invalidates/version-controls stale chunks; API/application code is provider-independent; document access checks have an insertion point before retrieval.

**Tests that must pass:** Chunking and citation-mapping tests; retrieval tests on a tiny deterministic corpus; prompt/answer contract tests with a fake provider; unsupported-answer test; API and frontend tests; RAG evaluation plus all prior gates.
