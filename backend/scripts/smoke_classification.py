"""Real HTTP upload -> PaddleOCR -> classifier -> PostgreSQL, using synthetic files.

Leaves only synthetic uploads in the configured development database/storage.
Starts/stops its own hidden Uvicorn process. No training or test-set tuning.
"""
from datetime import UTC, datetime
from io import BytesIO
import json
import os
import platform
import socket
import subprocess
import sys
from textwrap import wrap
from time import monotonic, perf_counter, sleep
from uuid import UUID

import httpx
import joblib
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import ROOT, Settings
from app.infrastructure.db.models import ProcessingRunRow

SAMPLES = {
    "invoice": ("PNG", [
        "INVOICE - DEMO OFFICE SUPPLIES", "Bill to Sample Community Center", "Invoice number DO-702",
        "Issue date: 2026-09-01. Payment due: 2026-09-30.",
        "Description       Quantity       Unit price       Amount",
        "Desk lamps              4             20.00           80.00",
        "Subtotal 80.00 USD. Sales tax 8.00 USD.", "Total amount due 88.00 USD.",
        "Please remit payment within thirty days.",
    ]),
    "contract": ("JPEG", [
        "SERVICE AGREEMENT", "Between Demo Garden and Sample Maintenance",
        "This contract is effective September 1, 2026.",
        "Provider shall maintain the grounds for twelve months.",
        "Client shall pay the agreed monthly fee.",
        "Either party may terminate with thirty days written notice.",
        "Changes require written consent from both parties.",
        "Confidentiality obligations survive termination.",
        "Authorized signatures for both parties: __________",
    ]),
    "form": ("PDF", [
        "COMMUNITY PROGRAM REGISTRATION FORM", "Please complete all fields in block letters.",
        "Full name: __________________________",
        "Email address: ______________________", "Contact telephone: __________________",
        "Preferred session: [ ] Morning  [ ] Afternoon",
        "Emergency contact name: ______________", "Special requirements: ________________",
        "Applicant signature: _________________", "Date: __________ Office use only: ______",
    ]),
    "low_confidence": ("PNG", ["ZXQV MNBV QWZX", "KJHX VQZX ZKQP"]),
}


def fixture(format: str, lines: list[str]) -> bytes:
    rendered = [part for line in lines for part in wrap(line, width=72)]
    with Image.new("RGB", (1400, 100 + len(rendered) * 60), "white") as image:
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=32)
        for i, line in enumerate(rendered):
            draw.text((40, 40 + i * 60), line, fill="black", font=font)
        output = BytesIO()
        image.save(output, format, **({"resolution": 144} if format == "PDF" else {}))
        return output.getvalue()


def wait_result(client: httpx.Client, base: str) -> dict:
    deadline = monotonic() + 180
    while monotonic() < deadline:
        response = client.get(base + "/results")
        response.raise_for_status()
        results = response.json()
        if results["status"] == "FAILED":
            raise RuntimeError(f"Processing failed: {results['latest_run']['error_code']}")
        if results["status"] in {"COMPLETED", "NEEDS_REVIEW"}:
            return results
        sleep(.1)
    raise RuntimeError("Smoke waiting guard exceeded; not a performance target")


def main() -> None:
    settings = Settings()
    engine = create_engine(settings.database_url.get_secret_value())
    # Compare API probabilities directly with the persisted sklearn pipeline.
    start = perf_counter()
    bundle = joblib.load(settings.classification_model_path)
    load_seconds = perf_counter() - start
    pipeline = bundle["pipeline"]
    output = ROOT / ".runtime/classification"
    output.mkdir(parents=True, exist_ok=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    log = (output / "smoke-server.log").open("w", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        env={**os.environ, "OCR_AUTO_PROCESS": "true"}, stdout=log, stderr=log,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    measurements = []
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=20) as client:
            deadline = monotonic() + 30
            while monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("Smoke backend exited during startup")
                try:
                    client.get("/health").raise_for_status()
                    break
                except httpx.ConnectError:
                    sleep(.1)
            else:
                raise RuntimeError("Smoke backend did not start")
            print("PASS real backend startup", flush=True)
            for expected, (format, lines) in SAMPLES.items():
                data = fixture(format, lines)
                filename = f"synthetic-{expected}.{format.lower()}"
                (output / filename).write_bytes(data)
                start = perf_counter()
                response = client.post("/api/v1/documents", files={"file": (filename, data)})
                assert response.status_code == 201, response.text
                base = f"/api/v1/documents/{response.json()['id']}"
                result = wait_result(client, base)
                wall_seconds = perf_counter() - start
                run = result["current_run"]
                prediction = run["classification"]
                assert prediction and run["result"]["provider"] == "PaddleOCR"
                ocr_text = "\n".join(p["text"] for p in run["result"]["pages"])
                start = perf_counter()
                raw_scores = pipeline.predict_proba([ocr_text])[0]
                inference_seconds = perf_counter() - start
                scores = dict(zip(pipeline.classes_, map(float, raw_scores), strict=True))
                assert prediction["scores"] == scores
                assert prediction["confidence"] == max(scores.values())
                assert prediction["predicted_type"] == max(scores, key=scores.get)
                for key in ("model_version", "dataset_version", "config_version"):
                    assert prediction[key] == bundle["metadata"][key]
                if expected == "low_confidence":
                    assert prediction["needs_review"] and result["status"] == "NEEDS_REVIEW"
                else:
                    assert prediction["predicted_type"] == expected, prediction
                # Independent connection: persisted JSONB must equal API output.
                with Session(engine) as session:
                    row = session.get(ProcessingRunRow, UUID(run["id"]))
                    assert row.is_current and row.classification["scores"] == scores
                    assert row.classification["model_version"] == prediction["model_version"]
                    assert row.classification["run_id"] == row.result["run_id"] == run["id"]
                assert client.post(base + "/process").json()["id"] == run["id"]
                measurement = {"sample": expected, "format": format, "document_id": response.json()["id"],
                    "status": result["status"], "prediction": prediction, "ocr_text": ocr_text,
                    "upload_to_result_seconds": wall_seconds, "processing_seconds": run["total_seconds"],
                    "classification_stage_seconds": run["classification_seconds"],
                    "independent_inference_seconds": inference_seconds,
                    "ocr_seconds": sum(p["ocr_seconds"] for p in run["result"]["pages"])}
                measurements.append(measurement)
                print(f"PASS {expected}: predicted={prediction['predicted_type']} confidence={prediction['confidence']:.6f} status={result['status']}", flush=True)
        report = {"date": datetime.now(UTC).isoformat(), "platform": platform.platform(),
                  "python": platform.python_version(), "processor": platform.processor(),
                  "cpu_threads": settings.ocr_cpu_threads, "model_load_seconds": load_seconds,
                  "measurements": measurements}
        (output / "smoke.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print("PASS persisted probabilities verified directly against sklearn predict_proba", flush=True)
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        log.close()
        engine.dispose()


if __name__ == "__main__":
    main()
