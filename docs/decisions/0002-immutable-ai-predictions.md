# ADR 0002: Immutable AI Predictions and Human-in-the-Loop Audit Trail

## Status
Accepted

## Context
In Intelligent Document Processing (IDP), artificial intelligence models (OCR, classification, entity extraction) produce probabilistic outputs with associated confidence scores. When low-confidence predictions require human correction (HITL), a common naive implementation simply updates the database row of the extracted field with the human-entered text.

This naive approach destroys critical historical data:
1. It obliterates model error history, making subsequent error analysis, fine-tuning, and offline evaluation impossible.
2. It breaks compliance and regulatory audit trails where organizations must prove what the machine generated versus what a human verified or altered.
3. In concurrent multi-user environments, race conditions can cause one reviewer to silently overwrite another reviewer's corrections.

## Decision
1. **Prediction Immutability:** Raw AI predictions stored in `processing_runs` are strictly immutable once committed. Neither API routes nor review services are permitted to execute SQL `UPDATE` operations on raw AI prediction columns.
2. **Dedicated Audit Trail (`reviews` table):** Human reviews, field corrections, and status approvals/rejections are stored as independent versioned records in a dedicated `reviews` table linked by `document_id`.
3. **Optimistic Concurrency Control:** Each document maintains an integer `revision` counter (starting at 1). Review submissions must include `expected_revision`. If a concurrent user has already updated the document, the submission is rejected with HTTP 409 (`STALE_REVISION_CONFLICT`), preventing silent data loss.

## Consequences
- **Positive:** Full audit compliance; ability to compute delta metrics comparing raw AI predictions against ground truth human corrections; guaranteed concurrency protection.
- **Negative:** Slightly increased database storage for storing both before/after states; API queries require joining or fetching the latest review record to display active values.
