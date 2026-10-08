# DocuMind AI — Portfolio & Interview Demonstration Script

This document outlines a structured 5-to-10 minute presentation walkthrough of the DocuMind AI Intelligent Document Processing platform for technical interviews, portfolio demonstrations, and reviews.

---

## 1. Executive Summary & Architecture (1 Minute)

- **Problem:** Enterprise organizations manually process unstructured invoices, contracts, and registration forms, suffering from human error and high operational costs.
- **Solution:** DocuMind AI — an end-to-end, production-ready IDP platform combining OCR, machine learning classification, layout-aware entity extraction, and human-in-the-loop review.
- **Architectural Philosophy:**
  - **Modular Monolith:** Clean domain boundaries (Ports & Adapters) preventing premature microservice overhead while enabling straightforward containerized deployment.
  - **Zero Data Leakage:** Rigorous separation of training and evaluation datasets with mathematically verified metrics.
  - **Immutable Predictions:** Machine-generated AI results are immutable for compliance; human corrections are persisted in a versioned audit trail.

---

## 2. Live Demo Walkthrough (5 Minutes)

### Step 1: Upload & Pipeline Ingestion
1. Navigate to `http://localhost:3000` (or local `http://localhost:5173`).
2. Point out the left sidebar navigation, bilingual language switcher (`🇬🇧 EN` / `🇻🇳 VN`), and real-time processing statistics.
3. Drag and drop a sample business invoice (e.g. `Sales Invoice.pdf` or synthetic PNG).
4. Demonstrate the multi-stage progression:
   $$\text{UPLOADED} \longrightarrow \text{QUEUED} \longrightarrow \text{PROCESSING} \longrightarrow \text{NEEDS\_REVIEW / COMPLETED}$$

### Step 2: Automated AI Processing
1. Open the document detail page.
2. Highlight the three coordinated AI stages:
   - **OCR Transcription:** High-fidelity text extraction with normalized bounding box coordinates $(x, y, w, h)$.
   - **Document Classification:** Real-time ML classification into `invoice`, `contract`, or `form` with confidence scoring.
   - **Structured Field Extraction:** Bóc tách các trường trọng yếu (Invoice number, dates, parties, subtotal, tax, total) in both English and Vietnamese.

### Step 3: Human-in-the-Loop Review Workspace
1. Switch to the **HITL Review Workspace**.
2. Demonstrate the two view modes:
   - **Split-Screen Mode (Song song / Chia đôi):** Document canvas on the left, structured correction form on the right.
   - **Stacked Mode (Trên - Dưới):** Full-width document viewer on top, 2-column extraction form underneath for documents with wide headers.
3. Hover over an extracted field to demonstrate **bidirectional bounding box highlighting** on the document image.
4. Modify an extracted total amount to demonstrate change tracking, diff badges, and audit persistence.
5. Click **Approve & Sync** to finalize the review. Show that the document lifecycle transitions to `COMPLETED` and the revision counter increments.

### Step 4: Quality & Evaluation Metrics Dashboard
1. Navigate to the **Evaluation & Metrics Dashboard**.
2. Explain the measured baseline results from [reports/baseline.md](file:///d:/New%20folder%20(2)/reports/baseline.md):
   - **OCR:** CER 0.54%, WER 3.23%.
   - **Classification:** 100% Test Accuracy (Macro F1: 1.0) on held-out split.
   - **Extraction:** 100% Exact Match on 42 structured field opportunities across English and Vietnamese documents.

---

## 3. Automated Terminal Demo (1 Minute)

For quick demonstration in a terminal without opening a browser:

```bash
# Ensure backend is running
uvicorn app.main:app --app-dir backend --port 8000

# In another terminal, run automated demo
python backend/scripts/demo.py
```
