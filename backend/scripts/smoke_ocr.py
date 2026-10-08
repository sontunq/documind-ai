"""Real Phase 3 HTTP/CPU/PostgreSQL smoke test on generated, non-sensitive files.

Run against a migrated development DATABASE_URL. Leaves synthetic documents and
their artifacts for inspection. Starts/stops its own hidden Uvicorn process.
"""
from io import BytesIO
import json
import os
import platform
import socket
import subprocess
import sys
from time import monotonic, perf_counter, sleep
from uuid import UUID

import httpx
from PIL import Image, ImageDraw, ImageFont
import psutil
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.infrastructure.db.models import ProcessingRunRow
from app.infrastructure.db.repository import SQLDocumentRepository
from app.infrastructure.storage.local import LocalDocumentStorage


def synthetic_image(text: str) -> Image.Image:
    image = Image.new("RGB", (1000, 260), "white")
    ImageDraw.Draw(image).text((40, 50), text, fill="black", font=ImageFont.load_default(size=44))
    return image


def fixtures():
    for format in ("PNG", "JPEG"):
        with synthetic_image("DOCUMIND TEST 123") as image:
            stream = BytesIO()
            image.save(stream, format)
        yield "synthetic." + format.lower(), stream.getvalue(), ["DOCUMIND TEST 123"]
    with synthetic_image("DOCUMIND PAGE ONE") as first, synthetic_image("DOCUMIND PAGE TWO") as second:
        stream = BytesIO()
        first.save(stream, "PDF", save_all=True, append_images=[second], resolution=144)
        yield "synthetic.pdf", stream.getvalue(), ["DOCUMIND PAGE ONE", "DOCUMIND PAGE TWO"]


def completed(client, base):
    deadline = monotonic() + 180
    observed = []
    while monotonic() < deadline:
        response = client.get(base + "/results")
        response.raise_for_status()
        results = response.json()
        if not observed or observed[-1] != results["status"]:
            observed.append(results["status"])
        if results["status"] == "FAILED":
            raise RuntimeError(f"OCR failed: {results['latest_run']['error_code']}")
        if results["status"] in {"COMPLETED", "NEEDS_REVIEW"}:
            return results["current_run"], observed
        sleep(.1)
    raise RuntimeError("Smoke-test waiting deadline exceeded (not a performance acceptance target)")


def main():
    settings = Settings()
    engine = create_engine(settings.database_url.get_secret_value())
    storage = LocalDocumentStorage(settings.document_storage_dir)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        env={**os.environ, "OCR_AUTO_PROCESS": "true"},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    measurements = []
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=20) as client:
            for _ in range(200):
                if process.poll() is not None:
                    raise RuntimeError("Uvicorn exited before startup")
                try:
                    response = client.get("/health")
                    response.raise_for_status()
                    break
                except httpx.ConnectError:
                    sleep(.1)
            else:
                raise RuntimeError("Backend did not start")
            print("PASS: real Uvicorn startup and /health", flush=True)
            for index, (filename, data, expected) in enumerate(fixtures()):
                start = perf_counter()
                response = client.post("/api/v1/documents", files={"file": (filename, data)})
                assert response.status_code == 201, response.text
                doc = response.json()
                assert doc["status"] == "UPLOADED"
                upload_seconds = perf_counter() - start
                base = f"/api/v1/documents/{doc['id']}"
                run, observed = completed(client, base)
                wall_seconds = perf_counter() - start
                pages = run["result"]["pages"]
                assert len(pages) == len(expected)
                for number, (page, phrase) in enumerate(zip(pages, expected, strict=True), start=1):
                    assert page["number"] == number and phrase in page["text"].upper(), page["text"]
                    for line in page["lines"]:
                        assert 0 <= line["confidence"] <= 1
                        box = line["box"]
                        assert 0 <= box["x"] <= box["x"] + box["width"] <= 1
                        assert 0 <= box["y"] <= box["y"] + box["height"] <= 1
                # Check real committed rows from an independent DB connection.
                with Session(engine) as session:
                    persisted = session.get(ProcessingRunRow, UUID(run["id"]))
                    assert persisted.is_current and persisted.status == "COMPLETED"
                    assert [p["text"] for p in persisted.result["pages"]] == [p["text"] for p in pages]
                    with storage.open(persisted.result["raw_output_reference"]) as source:
                        raw_pages = json.load(source)["pages"]
                    for page, raw in zip(pages, raw_pages, strict=True):
                        assert [line["confidence"] for line in page["lines"]] == raw["output"]["res"]["rec_scores"]
                    original = SQLDocumentRepository(session).get(UUID(doc["id"]))
                    with storage.open(original.storage_key) as source:
                        assert source.read() == data
                cached = client.post(base + "/process")
                assert cached.status_code == 202 and cached.json()["id"] == run["id"]
                reprocess = client.post(base + "/process?reprocess=true")
                assert reprocess.status_code == 202, reprocess.text
                new_run, _ = completed(client, base)
                assert new_run["id"] != run["id"] and new_run["attempt"] == 2
                with Session(engine) as session:
                    rows = list(session.scalars(select(ProcessingRunRow).where(ProcessingRunRow.document_id == UUID(doc["id"]))))
                    assert len(rows) == 2 and sum(r.is_current for r in rows) == 1
                    assert all(row.result for row in rows)
                measurement = {
                    "filename": filename, "document_id": doc["id"], "page_count": len(pages),
                    "condition": "cold process; cached model files" if index == 0 else "warm model",
                    "observed_states": [doc["status"], *observed],
                    "upload_http_seconds": upload_seconds, "upload_to_result_seconds": wall_seconds,
                    "processing_seconds": run["total_seconds"],
                    "ocr_seconds_per_page": [p["ocr_seconds"] for p in pages],
                    "warm_reprocess_seconds": new_run["total_seconds"],
                    "provider": run["result"]["provider"], "provider_version": run["result"]["provider_version"],
                    "engine_version": run["result"]["engine_version"], "model_version": run["result"]["model_version"],
                    "text": [p["text"] for p in pages],
                }
                measurements.append(measurement)
                print("PASS:", json.dumps(measurement), flush=True)
        report = {
            "platform": platform.platform(), "python": platform.python_version(),
            "processor": platform.processor(), "logical_cpus": os.cpu_count(),
            "physical_cpus": psutil.cpu_count(logical=False), "ram_gib": psutil.virtual_memory().total / 1024**3,
            "cpu_threads": settings.ocr_cpu_threads, "pdf_dpi": settings.ocr_pdf_dpi,
            "measurements": measurements,
        }
        print(json.dumps(report, indent=2), flush=True)
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        engine.dispose()


if __name__ == "__main__":
    main()
