# ADR 0001: Modular Monolith Architecture

## Status
Accepted

## Context
DocuMind AI is an Intelligent Document Processing (IDP) portfolio project designed to accept unstructured documents (PDFs, images), run OCR, classify document types, extract structured entities, support human-in-the-loop (HITL) review, and evaluate pipeline quality.

In modern enterprise architectures, IDP pipelines are sometimes implemented across distributed microservices (e.g. separate OCR worker services, classification APIs, extraction daemons, message brokers like Kafka/RabbitMQ). However, for a single-engineer portfolio project with bounded operational requirements, premature microservices introduce:
- Significant deployment complexity (RPC protocols, network retries, split brains).
- High operational resource footprint (multiple containers, message brokers, caching daemons).
- Difficult end-to-end tracing and testing.

## Decision
We chose a **Modular Monolith** architecture with clean Ports & Adapters (Hexagonal Architecture):
- Domain logic (`app/domain/`) defines pure business models, transition states, and repository interfaces without framework dependencies.
- Application use cases (`app/application/`) coordinate business workflows.
- Infrastructure adapters (`app/infrastructure/`) encapsulate PaddleOCR, Scikit-learn, SQLAlchemy, and local file storage behind small domain interfaces (`OCRProvider`, `DocumentClassifier`, `FieldExtractor`, `DocumentRepository`).
- API layer (`app/api/`) deals solely with HTTP transport, serialization, status codes, and dependency wiring.

## Consequences
- **Positive:** Single deployable container or Python process, instant local execution, ultra-fast integration testing with in-process or transactional PostgreSQL rollbacks, zero messaging queue overhead.
- **Positive:** Clear architectural boundaries allow extracting individual components (e.g. OCR worker) into independent microservices in the future without rewriting domain logic.
- **Negative:** Heavy CPU compute (OCR) shares process memory with the API server in single-process mode, requiring thread bounding (`OCR_CPU_THREADS=2`) and queue limits (`OCR_QUEUE_CAPACITY=8`).
