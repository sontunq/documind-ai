# DocuMind AI — Setup & Deployment Guide

This guide covers running DocuMind AI in two modes:
1. **Docker Compose Quickstart** (Recommended for evaluation & demos).
2. **Local Python/Node Development** (Recommended for code modification & active development).

---

## System Requirements

- **Operating System:** Windows 10/11, macOS, or Ubuntu Linux 22.04+
- **CPU:** 2+ physical cores (Intel Core i5 / AMD Ryzen 5 or better)
- **RAM:** Minimum 8 GB recommended (16 GB for optimal Docker performance)
- **Disk Space:** ~5 GB free space for dependencies, OCR model caches, and database

---

## Option 1: Docker Compose Quickstart

The entire stack (PostgreSQL 17, FastAPI backend, React/Nginx frontend) can be launched with a single command.

### 1. Clone & Configure
Ensure Docker Desktop or Docker Engine is running on your machine:

```bash
# Clone the repository
git clone <repository_url>
cd "DocuMind AI"

# Copy sample environment configuration
cp .env.example .env
```

### 2. Launch Services
```bash
docker compose up --build -d
```

### 3. Verify Health
Wait 10–15 seconds for database migrations to apply automatically:

- **Frontend Application:** Open `http://localhost:3000` (or `http://localhost:80` depending on port mapping)
- **Backend API & Swagger Docs:** Open `http://localhost:8000/docs`
- **Readiness Probe:** `curl http://localhost:8000/health/ready` -> `{"status": "ready", "database": "connected"}`

### 4. Stop Services
```bash
docker compose down
```

---

## Option 2: Local Development Setup

### 1. Prerequisites
- **Python:** 3.12.x (`python --version`)
- **Node.js:** 20.x or 22.x (`node --version`)
- **PostgreSQL:** 16.x or 17.x/18.x running locally

### 2. Backend Setup
```bash
# Navigate to workspace root
cd "d:/New folder (2)"

# Create virtual environment (if not already present)
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install backend dependencies in editable mode
pip install -e backend/

# Configure local .env
cp .env.example .env
# Edit .env to set DATABASE_URL=postgresql+psycopg://postgres:<your_password>@127.0.0.1:5432/documind

# Run database migrations to head
alembic -c backend/alembic.ini upgrade head

# Start FastAPI development server
uvicorn app.main:app --app-dir backend --reload --port 8000
```

### 3. Frontend Setup
In a separate terminal:

```bash
cd frontend

# Install npm dependencies
npm install

# Start Vite development server
npm run dev
```

Open `http://localhost:5173` in your browser. The Vite development proxy forwards all `/api` and `/health` requests to `http://localhost:8000`.

---

## Operational Probes & Health Checks

| Endpoint | Probe Type | Purpose | HTTP Status |
|---|---|---|---|
| `GET /health` | Basic Ping | Verifies server process is accepting HTTP traffic | 200 OK |
| `GET /health/live` | Liveness | Kubernetes/container liveness probe; checks process health | 200 OK |
| `GET /health/ready` | Readiness | Container readiness probe; validates live database connectivity (`SELECT 1`) | 200 OK or 503 Service Unavailable |
