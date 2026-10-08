#!/bin/sh
set -e

echo "Applying database migrations..."
alembic -c alembic.ini upgrade head

echo "Starting DocuMind AI Backend on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
