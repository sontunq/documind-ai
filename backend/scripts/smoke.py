"""Live HTTP smoke check against a migrated DATABASE_URL.

Starts/stops its own Uvicorn process and leaves three synthetic uploads in the
configured database/storage for inspection. Run only against a development DB.
"""
from io import BytesIO
import socket
import os
import subprocess
import sys
import time

import httpx
from PIL import Image
from pypdf import PdfWriter


def main() -> None:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env={**os.environ, "OCR_AUTO_PROCESS": "false"},
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=10) as client:
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError("Uvicorn exited before startup")
                try:
                    response = client.get("/health")
                    response.raise_for_status()
                    assert response.json() == {"status": "ok"}
                    break
                except httpx.ConnectError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Uvicorn did not become available")
            print("PASS: Uvicorn startup and GET /health over HTTP")
            pdf = BytesIO()
            writer = PdfWriter()
            writer.add_blank_page(width=100, height=100)
            writer.write(pdf)
            fixtures = [("synthetic.pdf", "application/pdf", pdf.getvalue())]
            for format, media, extension in [("PNG", "image/png", "png"), ("JPEG", "image/jpeg", "jpg")]:
                output = BytesIO()
                Image.new("RGB", (32, 32), "white").save(output, format=format)
                fixtures.append((f"synthetic.{extension}", media, output.getvalue()))
            for filename, media, data in fixtures:
                response = client.post("/api/v1/documents", files={"file": (filename, data, media)})
                assert response.status_code == 201, response.text
                document = response.json()
                assert document["status"] == "UPLOADED"
                assert document["media_type"] == media
                assert client.get(f"/api/v1/documents/{document['id']}").json() == document
                assert document in client.get("/api/v1/documents").json()
                print(f"PASS: {filename} upload/create/get/list")
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    main()
