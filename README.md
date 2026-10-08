# DocuMind AI

DocuMind AI is an incremental portfolio project for intelligent document processing. It will turn scanned PDFs and images into reviewable structured data: OCR text, document type, extracted fields, source bounding boxes, confidence scores, and human corrections.

The project is deliberately designed as a realistic one-student system. Each phase produces a demonstrable vertical slice while keeping AI libraries isolated from API and business logic.

## Planned capabilities

- Upload PDF and image business documents
- OCR with page- and token-level geometry
- Classify invoices, contracts, and forms
- Extract document-specific structured fields
- Display evidence bounding boxes and confidence
- Review, correct, and audit results
- Persist documents, predictions, and corrections
- Evaluate OCR, classification, and extraction quality
- Later compare documents and answer questions using retrieval-augmented generation (RAG)

## Technology direction

| Area | Stack |
|---|---|
| Frontend | React, Vite, TypeScript, TailwindCSS |
| Backend | Python 3.12, FastAPI |
| AI/document processing | PaddleOCR, OpenCV, scikit-learn and/or PyTorch when justified |
| Data | PostgreSQL; local file storage initially behind an abstraction |
| Infrastructure | Docker and Docker Compose in a later phase |
| Quality | pytest, frontend lint and production build checks |

## Architecture at a glance

The backend follows ports-and-adapters boundaries:

```text
React client -> FastAPI routes -> application services -> domain contracts
                                      |                    ^
                                      v                    |
                          repositories / job interface / AI ports
                                      |                    ^
                                      v                    |
                          PostgreSQL, file storage, PaddleOCR,
                          OpenCV, classifiers and extractors
```

FastAPI routes do not call AI libraries directly. OCR, classification, and extraction are providers selected through dependency injection, allowing a model or vendor to be replaced without rewriting the API or use cases.

See [requirements](docs/requirements.md), [architecture](docs/architecture.md), [roadmap](docs/roadmap.md), and [progress](docs/progress.md).

## Current status

Phases 1-4 implement validated upload, PostgreSQL metadata, the React upload/list/detail workflow, real PaddleOCR, and OCR-text classification as invoice, contract, or form. Uploads automatically schedule OCR and classification after creation. Versioned results are persisted; the detail page labels classifications as machine predictions and displays their probabilities. Phase 5 has not started. See [progress](docs/progress.md) for measured verification and limitations.

## Intended repository layout

```text
backend/
  app/
    api/              # HTTP routes and schemas
    application/      # use cases and orchestration
    domain/           # business entities and provider contracts
    infrastructure/   # database, storage, and AI adapters
  tests/
frontend/
  src/
docs/
```

Exact files are introduced only in their roadmap phase.

## Development approach

1. Work on only the current roadmap phase.
2. Add tests with each behavior.
3. Use synthetic or redistributable sample documents.
4. Record meaningful decisions and progress.
5. Keep raw machine predictions separate from reviewed values.

## Run the backend

Prerequisites: 64-bit Python 3.12 and a running PostgreSQL server (verified with PostgreSQL 17 and 18). Create a local database/user with permission to apply migrations. Commands below use PowerShell from the repository root. Keep an existing `.env`; copy the example only on first setup.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e './backend[test]'
Copy-Item .env.example .env
```

Edit `.env` with your local database URL and password. It is ignored by Git. Relative storage directories resolve from the repository root; default limits are 20 MiB per file, 50 PDF pages, and 25 million image pixels. Environment variables override `.env`. The multipart request envelope has an additional 64 KiB allowance; the exact file size is checked separately.

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python.exe backend/scripts/train_classifier.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Visit `http://127.0.0.1:8000/docs` for the interactive API. `/health` reports application liveness only; the server can start without a reachable database, but document operations require a migrated database.

Run one Uvicorn process for this local in-process OCR runner. After updating an existing checkout, reinstall backend dependencies, apply migrations, and restart the backend. Model initialization happens on the first OCR job, not during `/health`.

| Endpoint | Behavior |
|---|---|
| `GET /health` | HTTP 200 with `{"status":"ok"}`; no database check |
| `POST /api/v1/documents` | Multipart `file`; HTTP 201 with metadata |
| `GET /api/v1/documents?limit=50&offset=0` | Newest first, limit 1–100 |
| `GET /api/v1/documents/{id}` | Metadata or stable 404 error |
| `POST /api/v1/documents/{id}/process` | HTTP 202; retry failed/unprocessed documents or reuse an already completed matching run |
| `POST /api/v1/documents/{id}/process?reprocess=true` | HTTP 202; create a new attempt, preserving previous results |
| `GET /api/v1/documents/{id}/results` | Live status, latest attempt, current OCR and machine classification |

```powershell
curl.exe -F 'file=@C:/samples/synthetic.pdf' http://127.0.0.1:8000/api/v1/documents
```

Content inspection determines the media type, regardless of supplied filename/MIME. Filenames are sanitized display metadata, and storage keys/paths are excluded from responses. Errors use `{"error":{"code":"DOCUMENT_NOT_FOUND","message":"Document not found."}}`. Upload failures return 413 for limits, 415 for unsupported formats, 422 for empty/malformed/encrypted documents, and 503 for storage/database availability errors.

## Phase 3 OCR setup and behavior

The verified Windows CPU stack is pinned: PaddleOCR 3.3.3, PaddlePaddle 3.2.2, PaddleX 3.3.13, NumPy 2.2.6, OpenCV contrib 4.10.0.84, and pypdfium2 5.13.0. This deliberately uses a fixed PaddleOCR 3.3 release family and matching PaddleX dependency range, not a floating latest release. Python 3.12 Windows x64 wheels were verified before installation, and actual inference was tested. The upstream [Windows installation guide](https://www.paddlepaddle.org.cn/documentation/docs/install/pip/windows-pip_en.html) documents supported Python/platform combinations; the pinned stack used here is recorded in `backend/pyproject.toml`.

Two official models are used: `PP-OCRv5_mobile_det` and `en_PP-OCRv5_mobile_rec`. Inference is local CPU work, with two threads by default and MKL-DNN disabled. Document orientation classification, unwarping, and text-line orientation models are disabled. The first job needs network access to download the official models; subsequent jobs can use the cached files. Downloads and model initialization can take longer than inference. Model weights remain in ignored `.runtime/paddlex` by default. Existing `PADDLE_PDX_CACHE_HOME`/`HF_HOME` environment overrides take precedence; set them before starting the backend if needed. No uploaded document is sent to the model hosting service.

PDF pages render sequentially at 144 DPI with pypdfium2, whose wheel bundles PDFium without an external Poppler install. [PDFium requires serialized access across threads](https://pypdfium2.readthedocs.io/en/stable/python_api.html#incompatibility-with-threading); the adapter uses a process-local lock and explicitly releases page/bitmap resources. PDF raster dimensions are checked against `MAX_IMAGE_PIXELS` before allocation. PNG/JPEG use EXIF orientation correction; OpenCV performs the RGB-to-BGR conversion required by the OCR input. No enhancement or thresholding pipeline is added.

Settings are documented in `.env.example`:

| Setting | Default | Purpose |
|---|---|---|
| `OCR_AUTO_PROCESS` | `true` | Schedule after upload commits; set `false` for explicit manual processing |
| `OCR_PDF_DPI` | `144` | PDF render resolution, bounded to 72-300 |
| `OCR_CPU_THREADS` | `2` | Paddle CPU inference threads |
| `OCR_QUEUE_CAPACITY` | `8` | Maximum accepted jobs, including the running job |
| `OCR_CACHE_DIR` | `.runtime/paddlex` | Official model cache; never commit weights |

Upload returns its committed `UPLOADED` creation snapshot. Get/detail/results returns live status as it advances through `QUEUED` -> `PROCESSING` -> `COMPLETED`, `NEEDS_REVIEW`, or `FAILED`. Polling can miss the short-lived `QUEUED` state. Queue saturation or scheduling failure never deletes an uploaded file; a committed run is marked `FAILED`, or the document remains `UPLOADED` if run reservation itself failed. Both can be retried. An active run returns HTTP 409 `INVALID_PROCESSING_TRANSITION`; an unknown document returns 404; manual scheduling failure returns 503 `SCHEDULING_FAILED`.

`GET .../results` returns `latest_run` and `current_run` (both null before any run). A failed reprocess is visible as the latest attempt while the previous successful result remains current. Each result includes one-based pages, rendered pixel dimensions, ordered lines/page text, normalized `{x,y,width,height}` boxes, actual Paddle `rec_scores`, package/model identity, and a SHA-256 fingerprint of the model artifacts. Scores describe line recognition confidence, not calibrated accuracy. No word confidence, classification, extraction, or review result is invented. Opaque artifact references and raw Paddle objects are excluded from public responses; raw JSON and rendered PNGs are stored privately through the storage interface.

Migration `0002_ocr_processing` adds `processing_runs` with JSONB config/OCR payloads and canonical lifecycle support. The logical idempotency context is `(document_id, pipeline_version)`, with a config fingerprint check and monotonically increasing attempts. A completed matching request reuses its run; `reprocess=true`, failed attempts, or changed configuration create a new attempt. Row locks and partial unique indexes prevent concurrent active/current runs. Previous successful payloads are retained; only the current-result flag changes.

This runner is local and non-durable. Graceful shutdown drains accepted jobs; forced termination or a database outage during completion can leave `QUEUED`/`PROCESSING` records. Stop **all** backend instances, then run this recovery command before restarting and retrying affected documents:

```powershell
.\.venv\Scripts\python.exe backend/scripts/recover_processing.py --backend-stopped
```

It marks interrupted runs `FAILED` without deleting files or successful results. It must not run alongside active OCR jobs. There are no external queues, automatic crash retries, hard inference timeouts, multi-process workers, or public raw-artifact endpoints in Phase 3. A hard process crash can leave orphaned artifacts requiring manual cleanup. Handwriting, arbitrary rotated scans, complex reading order, and multilingual OCR are not verified.

## Phase 4 classification: train, evaluate, run

The baseline uses scikit-learn **1.7.2**, TF-IDF word unigrams/bigrams and multinomial Logistic
Regression (`lbfgs`, L2, `C=1`, `max_iter=1000`, seed 42, no class weighting). TF-IDF uses
`min_df=1`, `max_df=1.0`, sublinear term frequency and L2 normalization. The same persisted
pipeline calls `normalize_text` during training and inference: lowercase and collapse whitespace.
There is no stemming or stop-word removal. The default vectorizer tokenization retains word/number
tokens of at least two characters; punctuation is preserved by normalization but not used as a
separate word feature. The adapter obtains probabilities directly from
[LogisticRegression.predict_proba](https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.LogisticRegression.html#sklearn.linear_model.LogisticRegression.predict_proba),
mapped using `classes_`, and selects an argmax. OCR recognition confidence is never combined with them.

The [versioned manifest](data/manifests/classification-v1.json) contains 63 synthetic English texts:
45 train / 18 held-out test, balanced by class. [Dataset notes](data/manifests/README.md) explain
sources, licensing, split checks, and limitations. No model training happens during API requests.

Run from the repository root after installing the updated backend dependencies:

```powershell
.\.venv\Scripts\python.exe backend/scripts/train_classifier.py
$classificationModel = Get-Content .runtime/classification/baseline.metadata.json -Raw | ConvertFrom-Json
.\.venv\Scripts\python.exe backend/scripts/evaluate_classifier.py --model-version $classificationModel.model_version --dataset-version classification-synthetic-en-v1
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python.exe backend/scripts/smoke_classification.py
```

Training writes ignored `baseline.joblib` and `baseline.metadata.json` under
`.runtime/classification`. Evaluation writes `evaluation.json` there and prints accuracy, macro
and per-class precision/recall/F1, confusion matrix (rows actual, columns predicted), sample count,
versions and timings. Evaluation rejects a mismatched named version or changed manifest. It never
fits on test data. Use `--manifest` and `--artifact` to name another local version; evaluation also
accepts `--output`. The default decision threshold is **0.60**; `train_classifier.py --threshold`
changes the recorded policy/config/model identity. Do not adjust it against the held-out test set.

Metadata records complete vectorizer/classifier parameters, label mapping, dataset digest,
training-only digest, code hashes, dependency versions, seed, timestamp, sample distribution and
fit duration. The model version hashes the training identity; timestamps/timings are excluded.
For the measured environment use Python 3.12, scikit-learn 1.7.2, NumPy 2.2.6, SciPy 1.18.1 and
joblib 1.6.0 (also recorded in the artifact). Library/platform changes can change coefficients;
retrain and reevaluate rather than presenting old measurements as new results.

`CLASSIFICATION_MODEL_PATH` defaults to `.runtime/classification/baseline.joblib`; relative paths
resolve from the repository root. Load only artifacts produced locally by this training command
or from a trusted source: joblib loading executes Python serialization and is not an uploaded
document format. **Stop/restart the backend after training/replacing an artifact.** The startup
artifact fingerprint is part of processing configuration; a changed file creates a new attempt
after restart. A file replaced before lazy loading is rejected. An already loaded model stays
fixed until restart. `/health` remains a liveness check even when the classifier artifact is absent;
processing then records `CLASSIFICATION_FAILED`. Train the artifact and restart to resolve it.

Migration `0003_classification` adds nullable JSONB `classification` and numeric
`classification_seconds` columns to existing `processing_runs`, plus consistency checks.
The payload includes document/run IDs, predicted class, all three probabilities, selected confidence,
threshold, model identifier/version, dataset/config versions, and UTC creation time. No new tables
or field-extraction structures are added. Older OCR-only runs retain `classification: null` and can
be reprocessed with the new pipeline.

`GET .../results` exposes classification at `current_run.classification` and, when present, at
`latest_run.classification`. API `needs_review` derives from confidence below the persisted threshold.
A successful run has run status `COMPLETED`; its document status is `NEEDS_REVIEW` below 0.60 or
`COMPLETED` otherwise. Exactly 0.60 passes the threshold. This untuned demonstration policy is not
a calibrated error probability; a low-confidence prediction can still be correct. The UI provides
no correction/review editor in Phase 4.

Successful OCR is saved before classification. Missing/failed OCR never invokes the classifier.
Empty or punctuation-only OCR produces `CLASSIFICATION_EMPTY_TEXT`, a failed attempt, and no label.
Other classification errors are safely reported as `CLASSIFICATION_FAILED`. The new OCR remains
available under the latest attempt; an earlier fully successful result stays current. Classification,
document state and the current pointer commit together. Matching completed/needs-review requests
reuse the current run. `?reprocess=true` runs OCR and classification again, preserving previous
predictions; Phase 4 does not add a separate classify-only endpoint.

The smoke command starts a hidden Uvicorn process, uploads separate generated invoice PNG,
contract JPEG and form PDF samples, and verifies real PaddleOCR, real classification, metadata,
and independent PostgreSQL persistence. It compares every probability with direct `predict_proba`
on the exact saved OCR text, checks a low-confidence unrelated-text case, and stops its server.
Synthetic files, logs and `smoke.json` remain in ignored `.runtime/classification`; synthetic
document rows remain in the configured development database. This is integration verification,
not held-out quality evaluation. Detailed real measurements are in [progress](docs/progress.md).

## Run the Phase 2 frontend

Prerequisites: Node.js 22.12+ (verified with Node.js 24.13.0) and npm. Start the migrated backend as above at `http://127.0.0.1:8000`, then open a second PowerShell terminal:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open `http://127.0.0.1:5173`. PowerShell examples use `npm.cmd` to work when execution policy blocks `npm.ps1`; `npm` works in other shells. Pages are `/documents`, `/upload`, and `/documents/:id`. Opening `/` redirects to Documents. A refresh or navigation to Documents fetches current server data; nothing is persisted in browser storage.

Vite proxies `/api` and `/health` to the backend, avoiding cross-origin browser requests in local development. No backend CORS change is needed. To change the backend address, copy `frontend/.env.example` to `frontend/.env`, set `API_PROXY_TARGET`, and restart Vite. `/health` indicates application liveness only, not database readiness. The status indicator checks on page load and when **Recheck** is selected.

The backend enforces all content, size, page, and pixel limits. Frontend validation checks selection, extension, and nonempty files. An optional `VITE_MAX_UPLOAD_BYTES` provides earlier size feedback; if enabled, it must equal backend `MAX_UPLOAD_BYTES`. If omitted, size validation remains server-side. Restart/rebuild after changing frontend environment values. No secrets belong in frontend environment variables.

```powershell
cd frontend
npm.cmd run lint
npm.cmd run build
npm.cmd run preview
```

Preview serves the production build at `http://127.0.0.1:4173` and uses the same API proxy configuration. A future production host must provide SPA fallback for frontend routes and route `/api` and `/health` to FastAPI; deployment is deferred to Phase 8.

### Browser verification checklist

With the frontend, backend, and PostgreSQL running:

1. Open Documents and confirm the backend status is **connected**. With an empty database, confirm the empty state.
2. Open Upload Document. Submit without a file and select an unsupported/empty file to check feedback.
3. Select or drop one synthetic PDF, PNG, or JPEG. Upload it; confirm the saving state and creation metadata with `UPLOADED` status. With automatic OCR enabled, open details to see live processing status.
4. Open its detail page, expand Technical details, and refresh. Confirm the same ID; status and updated timestamp may change. Active jobs refresh every two seconds until completion/failure; Refresh status can be used manually.
5. Open Documents and refresh. Confirm the uploaded file is listed. With more than ten files, check Previous/Next.
6. Confirm keyboard access to navigation, file picker, upload, detail links, and technical details. Check a narrow viewport.
7. Stop the backend, select Recheck/Refresh list, and confirm useful unavailable/error states. Restart it and retry.

For a synthetic image, run this from the repository root (the output is ignored by Git):

```powershell
.\.venv\Scripts\python.exe -c "from pathlib import Path; from PIL import Image; Path('.runtime').mkdir(exist_ok=True); Image.new('RGB', (100, 100), 'white').save('.runtime/synthetic-upload.png')"
```

Uploads show an indeterminate saving state, not a percentage. Stay on the page while uploading. A timed-out request may already have saved a document: check Documents before retrying. No document preview/download endpoint or OCR/result UI is included in Phase 2.

## Tests and live verification

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

The ordinary suite uses synthetic files, a clearly test-only OCR provider, and real local storage/rendering/validation. PostgreSQL checks explicitly skip unless `TEST_DATABASE_URL` is set. Use a disposable test database; its user must be able to create/drop schemas. Each test migrates and removes only its own randomly named schema. Ordinary tests never download models or require a GPU/network; the explicitly opted-in real OCR test below may download official models.

Tests use a fresh, automatically cleaned temporary directory and cache per run. This avoids Windows ACL conflicts when an IDE user and a sandbox account inherit the same `TEMP`/`USERNAME`. Existing shared pytest directories are neither deleted nor granted broader permissions. Explicit `--basetemp` and `-o cache_dir=...` settings are respected; choose dedicated test-only directories you own. The default cache is temporary, so cross-run features such as `--lf` require an explicit persistent `cache_dir`. Unsafe-key tests treat Windows/POSIX path examples as strings and guard filesystem calls; actual escape-target fixtures live only inside `tmp_path`.

```powershell
$env:TEST_DATABASE_URL = 'postgresql+psycopg://documind:replace-me@localhost:5432/documind_test'
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

The ingestion smoke script uses `DATABASE_URL`/`.env`, starts and stops its own Uvicorn process with automatic OCR disabled, and leaves three synthetic PDF/PNG/JPEG uploads in the configured development database/storage:

```powershell
.\.venv\Scripts\python.exe backend/scripts/smoke.py
```

Run the small real adapter test explicitly (CPU, with model downloads on first use):

```powershell
$env:RUN_REAL_OCR = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests/test_paddle.py -q
Remove-Item Env:RUN_REAL_OCR
```

After migrating a local development database, exercise real HTTP upload, automatic OCR, PostgreSQL results, confidence provenance, idempotency, and reprocessing:

```powershell
.\.venv\Scripts\python.exe backend/scripts/smoke_ocr.py
```

It generates PNG/JPEG and a two-page PDF, leaves synthetic uploads/results for inspection, prints measured per-page/total durations and hardware context, and stops its own server. The waiting deadline in this smoke script is a test guard, not a throughput target. `ocr_seconds` measures provider inference per page; `total_seconds` measures processing from claim through preparation/model initialization/OCR to immediately before the completion write, excluding queue wait and final DB commit. The script also measures HTTP upload-to-result time. These smoke results are not OCR quality benchmarks; no accuracy/CER/WER claims are made.

Upload validation checks parsing/page structure, not malware safety; Phase 3 additionally renders accepted PDFs during processing. Filesystem and database writes cannot be atomic: handled failures trigger cleanup, but an abrupt process crash, uncertain commit, or failed filesystem deletion can require manual reconciliation. Do not expose this unauthenticated development API publicly.
