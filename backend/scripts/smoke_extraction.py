"""Real HTTP upload -> PaddleOCR -> classifier -> field extractor -> PostgreSQL.

Leaves only synthetic uploads in the configured development database/storage.
Starts/stops its own hidden Uvicorn process.
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
        "Either party may terminate on 2027-09-01.",
        "Changes require written consent from both parties.",
        "Governing law: California",
        "Authorized signatures for both parties: __________",
    ]),
    "form": ("PDF", [
        "COMMUNITY PROGRAM REGISTRATION FORM", "Please complete all fields in block letters.",
        "Full name: John Smith",
        "Email address: john.smith@example.com", "Contact telephone: 555-0199",
        "Preferred session: [ ] Morning  [ ] Afternoon",
        "Emergency contact name: _________________",
        "Applicant signature: _________________",
    ]),
}


def fixture(format: str, lines: list[str]) -> bytes:
    rendered = [part for line in lines for part in wrap(line, width=72)]
    with Image.new("RGB", (1400, 100 + len(rendered) * 60), "white") as image:
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except OSError:
            font = ImageFont.load_default()
        y = 40
        for line in rendered:
            draw.text((60, y), line, fill="black", font=font)
            y += 60
        buffer = BytesIO()
        if format == "PDF":
            image.save(buffer, format="PDF", resolution=144.0)
        else:
            image.save(buffer, format=format)
        return buffer.getvalue()


def wait_result(client: httpx.Client, base: str) -> dict:
    deadline = monotonic() + 90
    while monotonic() < deadline:
        response = client.get(f"{base}/results")
        assert response.status_code == 200, response.text
        payload = response.json()
        if payload["status"] not in ("UPLOADED", "QUEUED", "PROCESSING"):
            return payload
        sleep(0.5)
    raise TimeoutError("Timed out waiting for document processing to finish")


def main() -> None:
    settings = Settings()
    output = ROOT / ".runtime" / "extraction"
    output.mkdir(parents=True, exist_ok=True)
    engine = create_engine(settings.database_url.get_secret_value())

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "backend")
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["OMP_NUM_THREADS"] = "1"
    log = (output / "smoke-server.log").open("wb")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    try:
        base_url = f"http://127.0.0.1:{port}"
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            ready = False
            for _ in range(50):
                try:
                    if client.get("/health").status_code == 200:
                        ready = True
                        break
                except httpx.HTTPError:
                    sleep(0.2)
            if not ready:
                raise RuntimeError("Uvicorn backend failed to start")
            print("PASS real backend startup", flush=True)

            # 1. Invoice
            inv_data = fixture("PNG", SAMPLES["invoice"][1])
            res = client.post("/api/v1/documents", files={"file": ("synthetic-invoice.png", inv_data)})
            assert res.status_code == 201
            doc_id = res.json()["id"]
            result = wait_result(client, f"/api/v1/documents/{doc_id}")
            run = result["current_run"]
            assert run["status"] in ("COMPLETED", "NEEDS_REVIEW")
            assert run["extraction"] is not None
            inv = run["extraction"]["invoice"]
            assert inv is not None
            assert inv["invoice_number"]["value"] == "DO-702"
            assert inv["total"]["value"] == 88.0
            assert inv["currency"]["value"] == "USD"
            print(f"PASS invoice extraction: number={inv['invoice_number']['value']} total={inv['total']['value']} {inv['currency']['value']}", flush=True)

            # 2. Contract
            con_data = fixture("JPEG", SAMPLES["contract"][1])
            res = client.post("/api/v1/documents", files={"file": ("synthetic-contract.jpeg", con_data)})
            assert res.status_code == 201
            doc_id = res.json()["id"]
            result = wait_result(client, f"/api/v1/documents/{doc_id}")
            run = result["current_run"]
            con = run["extraction"]["contract"]
            assert con is not None
            assert con["title"]["value"] == "SERVICE AGREEMENT"
            assert con["party_a"]["value"] == "Demo Garden"
            assert con["party_b"]["value"] == "Sample Maintenance"
            print(f"PASS contract extraction: title={con['title']['value']} parties='{con['party_a']['value']}' & '{con['party_b']['value']}'", flush=True)

            # 3. Form
            form_data = fixture("PDF", SAMPLES["form"][1])
            res = client.post("/api/v1/documents", files={"file": ("synthetic-form.pdf", form_data)})
            assert res.status_code == 201
            doc_id = res.json()["id"]
            result = wait_result(client, f"/api/v1/documents/{doc_id}")
            run = result["current_run"]
            form = run["extraction"]["form"]
            assert form is not None
            assert "REGISTRATION" in form["form_title"]["value"]
            fields = {f["name"]: f["value"] for f in form["fields"]}
            assert "Full name" in fields
            print(f"PASS form extraction: title={form['form_title']['value']} fields_count={len(form['fields'])}", flush=True)

            # Verify in PostgreSQL
            with Session(engine) as session:
                row = session.get(ProcessingRunRow, UUID(run["id"]))
                assert row is not None and row.extraction is not None
                assert row.extraction["document_type"] == "form"
                assert row.extraction_seconds is not None
            print("PASS persisted extraction verified directly in PostgreSQL", flush=True)
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
