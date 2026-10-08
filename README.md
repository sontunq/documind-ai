# DocuMind AI — Intelligent Document Processing (IDP) Platform

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6.svg)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17%2B-336791.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)

**DocuMind AI** is an enterprise-grade Intelligent Document Processing (IDP) platform designed to ingest, process, and extract structured business data from unstructured scans and digital PDFs (Invoices, Contracts, and Forms). 

The platform features an end-to-end pipeline combining **OCR line geometry**, **machine learning classification**, **spatial heuristic field extraction**, an interactive **Human-in-the-Loop (HITL) review workspace**, and **rigorous empirical evaluation**.

---

## ⚡ Quick Start & Setup Guide

Whether you are a recruiter, reviewer, or developer, you can get the full system up and running in minutes using either **Docker Compose** or **Local Setup**.

---

### Option 1: Run with Docker (1-Command Setup — Recommended)

> [!TIP]
> The fastest way to explore the project. Automatically provisions PostgreSQL, backend services, and the React frontend with Nginx.

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/sontunq/documind-ai.git
   cd documind-ai
   ```

2. **Launch all services:**
   ```bash
   docker compose up --build -d
   ```

3. **Access the platform:**
   - 🌐 **Web Application:** [http://localhost:5173](http://localhost:5173) (Interactive UI, HITL Workspace, Metrics Dashboard)
   - 📑 **Swagger API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs) (Interactive OpenAPI documentation)
   - 🩺 **Health Readiness Probe:** [http://localhost:8000/health/ready](http://localhost:8000/health/ready)

4. **Stop the environment:**
   ```bash
   docker compose down
   ```

---

### Option 2: Local Development Setup (Without Docker)

**Prerequisites:**
- **Python 3.12** (64-bit)
- **Node.js 20+** or **22+** with `npm`
- **PostgreSQL 16+** running locally

---

#### 1. Database Setup
Create a PostgreSQL database for DocuMind:
```sql
-- In your PostgreSQL terminal (psql)
CREATE DATABASE documind;
```

---

#### 2. Backend Setup
Open a terminal in the project root:

```powershell
# 1. Create and activate a Python virtual environment
python -m venv .venv

# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux / macOS:
# source .venv/bin/activate

# 2. Install backend dependencies & development packages
pip install --upgrade pip
pip install -e "./backend[test]"

# 3. Configure environment variables
Copy-Item .env.example .env
```

Open `.env` and configure your local PostgreSQL connection string:
```ini
DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/documind
```

Run database migrations and train the initial classification model:
```powershell
# 4. Apply database migrations
python -m alembic -c backend/alembic.ini upgrade head

# 5. Train baseline ML classifier (< 2 seconds)
python backend/scripts/train_classifier.py

# 6. Start the FastAPI backend server
python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```
*Backend is now running at `http://localhost:8000` (API Docs: `http://localhost:8000/docs`).*

---

#### 3. Frontend Setup
Open a **second terminal** in the project root:

```powershell
# 1. Navigate to the frontend directory
cd frontend

# 2. Install frontend dependencies
npm install

# 3. Start the Vite development server
npm run dev
```
*Frontend is now running at `http://localhost:5173`.*

---

### 🎬 How to Test & Demo the System

1. **Via Web Browser:**
   - Go to [http://localhost:5173](http://localhost:5173).
   - Click **Upload & Ingestion** to drag-and-drop any PDF invoice, contract, or form.
   - Switch language at the top right pill (`[ 🇻🇳 VI | 🇬🇧 EN ]`).
   - Open **HITL Review Workspace** to inspect bounding boxes and edit structured fields.

2. **Via Automated CLI Demo Script:**
   You can run an automated script that tests the entire end-to-end pipeline (health check $\rightarrow$ synthetic invoice ingestion $\rightarrow$ OCR $\rightarrow$ ML classification $\rightarrow$ field extraction $\rightarrow$ human review audit trail):
   ```powershell
   python backend/scripts/demo.py
   ```

---

## 🌟 Key Capabilities

### 1. Robust Document Ingestion & Validation
- Ingests multi-page **PDF**, **PNG**, and **JPEG** files up to 20 MiB.
- Magic-byte content inspection and strict format validation (rejects malicious/corrupted files).
- Secure storage with SHA-256 deduplication and opaque storage identifiers.

### 2. High-Precision OCR & Spatial Geometry
- Powered by **PaddleOCR** with local CPU inference.
- Extracts token- and line-level text with normalized bounding boxes `(x, y, width, height)` in `[0.0, 1.0]` coordinates.
- Preserves raw recognition confidence scores per line.

### 3. Machine Learning Document Classification
- Categorizes documents into **Invoice**, **Contract**, or **Form**.
- Lightweight TF-IDF + Multinomial Logistic Regression model executing in **< 2 ms** with confidence scoring and fallback thresholds.

### 4. Bilingual Structured Field Extraction (English & Vietnamese)
- **Invoices**: Invoice number, issue date, due date, supplier, customer, line totals, VAT tax rate/amount, and total payment.
- **Contracts**: Contract number, title, Party A & Party B, effective date, expiry date, contract value, and governing law.
- **Forms**: Form titles, key-value label pairs, and checkbox inputs.
- Handles Vietnamese diacritics, thousand-dot currency formats (`20.000.000 VNĐ`), and multi-column tabular layouts.

### 5. Human-in-the-Loop (HITL) Visual Review Workspace
- **Dual Viewport Layouts**: Switch effortlessly between **Split-screen** (side-by-side) and **Stacked** (top-down) views.
- **Interactive Bounding Box Overlays**: Color-coded by confidence (Green >90%, Amber 70-90%, Red <70%), bidirectionally synchronized with form fields on hover and focus.
- **Auditable & Immutable**: Original AI predictions are permanently preserved. Corrections are saved in a separate revision-controlled audit trail with optimistic concurrency protection.
- **Bilingual Interface**: One-click language switching between **English (EN)** and **Vietnamese (VI)**.

### 6. Production Observability & Resilience
- **Distributed Tracing**: Automatic `X-Correlation-ID` and `X-Request-ID` propagation across all asynchronous operations.
- **Structured JSON Logging**: Standardized JSON log events with sensitive text and password redaction.
- **Operational Health Probes**: Dedicated `/health/live` (process liveness) and `/health/ready` (database readiness ping).

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2 |
| **Database** | PostgreSQL 17 / 18, JSONB for flexible schema storage |
| **AI / ML** | PaddleOCR, OpenCV, scikit-learn, pypdfium2 |
| **Frontend** | React 18, Vite, TypeScript, TailwindCSS, Lucide Icons, Recharts |
| **DevOps & Containers** | Docker, Docker Compose, Nginx (Alpine multi-stage build) |
| **Testing** | pytest, pytest-asyncio, ESLint, TypeScript compiler |

---

## 🏗️ System Architecture

DocuMind AI follows **Clean Architecture (Ports and Adapters)** principles to decouple core business logic from external frameworks:

```text
React Client (TypeScript + TailwindCSS)
                │
                ▼ HTTP / JSON (Correlation IDs)
FastAPI Routes & Schemas  (backend/app/api)
                │
                ▼ Use Cases & Orchestration
Application Services     (backend/app/application)
                │
                ▼ Domain Entities & Business Rules
Domain Models & Ports    (backend/app/domain)
                │
                ▼ Adapters & Infrastructure
Infrastructure Layer     (backend/app/infrastructure)
   ├── PostgreSQL (SQLAlchemy Repository & Alembic Migrations)
   ├── OCR Adapter (PaddleOCR + pypdfium2)
   ├── Classifier Adapter (scikit-learn TF-IDF pipeline)
   ├── Field Extractor (Spatial Heuristic & Normalization Engine)
   └── Local File Storage
```

---

## 🧪 Testing & Quality Gates

The project maintains rigorous automated test suites across all layers.

### Run Backend Tests (180+ tests)
```powershell
# Run unit & domain tests
.\.venv\Scripts\pytest backend/tests

# Run integration tests against PostgreSQL
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:password@localhost:5432/documind_test"
.\.venv\Scripts\pytest backend/tests
```

### Run Frontend Linting & Build
```powershell
cd frontend
npm run lint
npm run build
```

---

## 📊 Evaluation & Performance Benchmarks

DocuMind AI adheres to a strict **zero-fabrication policy**: all evaluation numbers are measured directly on test sets and real hardware.

### 1. Quality Metrics (Baseline Evaluation)
To run the automated model evaluation across OCR, Classification, and Extraction:
```powershell
.\.venv\Scripts\python backend/scripts/evaluate.py
```

| Task | Metric | Measured Value | Dataset / Test Size |
|---|---|:---:|---|
| **OCR** | Character Error Rate (CER) | **0.54%** | Bilingual evaluation set |
| **OCR** | Word Error Rate (WER) | **3.23%** | Bilingual evaluation set |
| **Classification** | Test Accuracy | **100%** | 18 held-out test samples |
| **Classification** | Macro F1-Score | **1.0000** | Balanced (Invoice, Contract, Form) |
| **Field Extraction** | Exact Match Ratio | **100%** | 42 evaluated ground-truth fields |
| **Field Extraction** | Macro F1-Score | **1.0000** | English & Vietnamese documents |

*Detailed report: [`reports/baseline.md`](reports/baseline.md)*

### 2. Latency Benchmarks
Benchmarked locally on Intel Core i5 (8 logical cores, Windows 11):
- **Document Upload API:** Mean **104.32 ms**
- **Metadata Retrieval:** Mean **33.08 ms**
- **Document List Pagination:** Mean **24.67 ms**
- **ML Classification:** **1.84 ms**
- **Rule-based Extraction:** **0.87 ms**
- **PaddleOCR Inference:** ~800 ms per page (CPU)

*Detailed report: [`reports/performance.md`](reports/performance.md)*

---

## 📂 Repository Structure

```text
documind-ai/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI routes, Pydantic schemas, error handlers
│   │   ├── application/     # Use case orchestrators (Process, Review, Extract)
│   │   ├── core/            # Configuration & structured logging / observability
│   │   ├── domain/          # Pure entities, value objects, ports, lifecycle rules
│   │   ├── evaluation/      # CER, WER, and F1 metric algorithms & runners
│   │   ├── infrastructure/  # PostgreSQL repo, PaddleOCR, scikit-learn, extraction
│   │   └── main.py          # FastAPI application factory & lifespan wiring
│   ├── migrations/          # Alembic database migration scripts (0001 - 0005)
│   ├── scripts/             # CLI tools (train, evaluate, demo, benchmark)
│   └── tests/               # 180+ pytest test suite
├── frontend/
│   ├── src/
│   │   ├── components/      # Header, Sidebar, LanguageSwitcher, Feedback
│   │   ├── features/        # Review workspace, Upload, Metadata, Extraction
│   │   ├── lib/             # API client, i18n localization dictionaries
│   │   └── routes/          # DocumentsPage, UploadPage, DocumentPage
│   ├── nginx.conf           # Production Nginx reverse-proxy configuration
│   └── Dockerfile           # Multi-stage production container build
├── data/                    # Evaluation manifests and synthetic test datasets
├── docs/                    # Technical documentation, setup guide, and ADRs
├── compose.yaml             # Multi-service Docker Compose topology
├── Dockerfile               # Backend production container
└── README.md                # Project overview and setup guide
```

---

## 📑 Architecture Decisions

For deep dives into design rationale and trade-offs, refer to the Architecture Decision Records (ADRs):
- [`0001-modular-monolith.md`](docs/decisions/0001-modular-monolith.md): Modular Monolith vs. Microservices.
- [`0002-immutable-ai-predictions.md`](docs/decisions/0002-immutable-ai-predictions.md): Immutable AI outputs and separate audit trail.
- [`0003-hybrid-extraction.md`](docs/decisions/0003-hybrid-extraction.md): Machine learning classification combined with spatial rule extraction.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
Synthetic evaluation sample data is released under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
