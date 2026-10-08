# Requirements

## 1. Purpose and scope

DocuMind AI helps a user convert scanned business documents into structured, traceable, and correctable data. The initial supported document types are invoices, contracts, and forms.

This document describes the target product. Delivery is incremental according to `roadmap.md`; a target requirement is not necessarily implemented yet.

## 2. Users and primary workflow

The initial user is a reviewer processing a small collection of business documents.

1. The reviewer uploads a PDF or image.
2. The system validates and stores it, then persists a document in `UPLOADED` state. Phase 1 ends with upload, persistence, and metadata retrieval.
3. From Phase 3, processing may be automatically queued after document creation. OCR is introduced in Phase 3, classification in Phase 4, and extraction in Phase 5. The normal user flow should not require a separate process-button action.
4. The reviewer sees values, confidence, and highlighted source regions.
5. The reviewer corrects errors and submits the review.
6. The system retains raw predictions and reviewed values for audit and evaluation.

## 3. Functional requirements

### FR-1 Document ingestion

- Accept PDF, PNG, and JPEG uploads.
- Reject unsupported, empty, oversized, malformed, or misleading files with a clear error.
- Compute a content checksum and store original filename, detected media type, size, page count when known, and timestamps.
- Assign an opaque document identifier; never use a client filename as a storage path.
- Expose document metadata and processing status.

### FR-2 Processing lifecycle

- Use only the canonical states `UPLOADED`, `QUEUED`, `PROCESSING`, `NEEDS_REVIEW`, `COMPLETED`, and `FAILED`.
- Phase 1 only needs `UPLOADED`; `QUEUED` and active processing states become relevant from Phase 3.
- Centralize state transitions in domain rules coordinated by application services. API routes and frontend components must not invent status values independently.
- Phase 1 must not implement a job dispatcher or placeholder job classes/interfaces. Phase 3 introduces the processing/job boundary alongside OCR.
- Record failure details suitable for troubleshooting without leaking sensitive content to clients.
- Make processing retryable and avoid producing duplicate current results on retry.
- Keep document creation separate from processing execution so processing can run in the background later. Synchronous processing is acceptable during the MVP if measured performance is reasonable; no external queue or worker infrastructure is required.
- From Phase 3, automatic processing may be queued after successful document creation. `POST /api/v1/documents/{document_id}/process` is primarily for manual retry, reprocessing, or development, not the normal upload workflow.

### FR-3 OCR

- Render PDFs into ordered pages and normalize image orientation/quality where useful.
- Produce page text and ordered OCR tokens/lines.
- Associate OCR elements with page number, normalized bounding geometry, and provider confidence.
- Preserve raw provider output or a reproducible reference to it for debugging.

### FR-4 Classification

- Predict exactly one initial class: `invoice`, `contract`, or `form`.
- Return class probabilities or scores, selected class, model/version identifier, and decision threshold.
- Route low-confidence predictions to human review.
- Support replacing the baseline classifier without changing route or application-service code.

### FR-5 Field extraction

- Use a document-type-specific schema.
- Initial invoice fields: invoice number, issue date, due date, supplier, customer, subtotal, tax, total, and currency.
- Initial contract fields: contract number, title, party A, party B, effective date, expiry/termination date, contract value, and governing law.
- Keep Phase 5 contract extraction narrow and measurable using source-backed fields; it does not include LLM summarization. Any future contract summarization is deferred to a later optional LLM/RAG extension and is not a current roadmap requirement.
- Initial form fields: form title and detected label/value pairs.
- Return each field's normalized value, original evidence text, page number, normalized bounding box(es), confidence, and extractor/model version.
- Represent missing fields explicitly rather than inventing values.

### FR-6 Review and correction

- Display the source page alongside extracted fields.
- Highlight the evidence box for a selected field.
- Allow correction, addition, removal, and explicit confirmation of fields and document type.
- Record who/what changed a value, timestamp, previous value, and new value.
- Preserve immutable raw predictions separately from the current reviewed result.
- Prevent accidental overwrite when two stale review sessions submit changes.

### FR-7 Persistence and retrieval

- Store metadata, lifecycle state, OCR output, classifications, extractions, review history, evaluation metadata, and model versions in PostgreSQL as appropriate.
- Store original and rendered document binaries through a storage interface; use local storage first and allow object storage later.
- List and retrieve documents and their current processing/review state.
- Delete or retain data according to a documented development retention policy in a later phase.

### FR-8 Evaluation

- Evaluate OCR on a labeled sample using character error rate (CER) and word error rate (WER).
- Evaluate classification with accuracy, macro precision/recall/F1, per-class metrics, and a confusion matrix.
- Evaluate extraction using per-field exact/normalized match and precision/recall/F1 where applicable.
- Track dataset version, model/configuration version, sample count, evaluation date/method, and aggregate results.
- Keep evaluation data separate from training/development data; never report training metrics as test performance or fabricate benchmark results. Phase 4 establishes classification evaluation; Phase 7 consolidates OCR, classification, and extraction evaluation.

### FR-9 Later extensions

- Compare two documents and report meaningful field/text differences with evidence.
- Answer grounded questions over processed documents using RAG, returning page/region citations and declining unsupported answers.
- These extensions must consume existing normalized document/OCR/extraction contracts rather than bypass them.

## 4. Non-functional requirements

### Security and privacy

- Validate detected content type and enforce configurable upload size/page limits.
- Sanitize filenames, isolate storage paths, and guard PDF/image parsers against resource exhaustion.
- Do not log document contents, extracted personal data, secrets, or local storage paths by default.
- Configure allowed browser origins; authentication/authorization is deferred but must have a clear insertion point.
- Use parameterized database access and environment-provided credentials.

### Reliability and correctness

- State transitions and review updates are transactional.
- Reprocessing records provider/model/configuration versions.
- Results remain traceable from a structured value to source document, page, text, and geometry.
- API errors have stable machine-readable codes.

### Measured performance benchmarks

Record real performance as each capability becomes available; consolidate a reproducible benchmark report in Phase 8. Document hardware, software/model versions, workload sizes, sample counts, measurement method, and cold/warm model conditions where relevant. Measure:

- API latency, including upload and metadata latency, with file-transfer time identified separately.
- OCR time per page and total processing time per document once processing exists.
- Document list latency at documented record counts.

No unmeasured latency or throughput number is a hard acceptance criterion. Hard targets may be proposed later only after real measurements exist: measured performance > invented target numbers.

Upload defaults remain a maximum of 20 MB and 50 pages, both configurable; these are validation limits, not performance targets.

### Maintainability

- AI frameworks are confined to infrastructure adapters.
- Domain/application tests run without downloading AI models or requiring a GPU.
- Provider interfaces and stored model versions allow deterministic test doubles and future upgrades.
- Public Python and TypeScript boundaries are typed.

### Usability and accessibility

- UI communicates upload/processing progress, errors, low confidence, and unsaved changes.
- Review interactions support keyboard use and do not rely on color alone.
- Confidence is shown as decision support, not as a guarantee of correctness.

### Health and observability

- Phase 1 provides only `GET /health`, returning HTTP 200 with `{"status": "ok"}` when the application is running. It does not certify database readiness.
- Phase 8 owns request/correlation IDs, structured logs, and advanced observability. Logs include document ID, job ID where available, duration, state transition, and model version where relevant.
- Phase 8 adds `/health/live` and `/health/ready` to distinguish process liveness from dependency readiness; these are not Phase 1 requirements.
- From Phase 3, processing failures retain safe error details without document contents. This basic failure handling does not require Phase 8 logging infrastructure.

## 5. Data and labeling assumptions

- Development uses a small, versioned, representative dataset of synthetic or redistributable documents.
- Every evaluation sample has a manifest containing document type, source/license, split, and ground truth location.
- Bounding-box ground truth uses the same normalized coordinate convention as the domain model.
- English is the initial language; multilingual OCR is a later enhancement.
- Handwriting support is not guaranteed in the initial release.

## 6. Out of scope for the initial portfolio release

- Production multi-tenant authentication, billing, and organization management
- Legally binding electronic signatures or legal interpretation
- Automatic actions based solely on extracted data
- Training large foundation models from scratch
- High-availability distributed infrastructure
- Guaranteed extraction for arbitrary document layouts or languages

## 7. Product success criteria

- A reviewer can process and correct all three document types end to end.
- Every extracted value can be traced to evidence on a page or marked as derived/missing.
- A model implementation can be swapped using configuration/dependency wiring without changing HTTP routes or application use cases.
- Evaluation results are reproducible from a versioned test manifest.
- A clean checkout can be run and tested using documented commands by the containerization phase.
