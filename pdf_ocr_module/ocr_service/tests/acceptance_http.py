"""Fresh generated inputs; actual HTTP server and separately launched OCR worker."""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time

import httpx

from ocr_service.config import PACKAGE_ROOT, ROOT, Settings
from ocr_service.db import Base, database, uid
from .conftest import authorization
from .documents import image_bytes, pdf_bytes


def main():
    directory = PACKAGE_ROOT / ".verification" / uid()
    directory.mkdir(parents=True)
    cfg = Settings(storage=directory, database_url="sqlite:///" + (directory / "service.sqlite3").as_posix(),
                   jwt_secret=secrets.token_hex(32))
    engine, _ = database(cfg)
    Base.metadata.create_all(engine)
    engine.dispose()
    with socket.socket() as binding:
        binding.bind(("127.0.0.1", 0))
        port = binding.getsockname()[1]
    env = dict(os.environ, OCR_STORAGE=str(directory), OCR_DATABASE_URL=cfg.database_url, OCR_JWT_SECRET=cfg.jwt_secret,
               OCR_HANDWRITING_WEIGHTS="", OCR_CUSTOM_REC_WEIGHTS="")
    records = []
    with (directory / "server.log").open("wb") as log:
        server = subprocess.Popen([sys.executable, "-m", "uvicorn", "ocr_service.api:create_app", "--factory",
            "--host", "127.0.0.1", "--port", str(port)], env=env, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}/api/v1/ocr", headers=authorization(cfg), trust_env=False, timeout=30) as client:
                deadline = time.monotonic() + 30
                while True:
                    try:
                        if client.get("/capabilities").status_code == 200:
                            break
                    except httpx.ConnectError:
                        pass
                    if time.monotonic() > deadline or server.poll() is not None:
                        raise RuntimeError("API startup failed; inspect server.log")
                    time.sleep(.25)
                for filename, payload, pages in [("equipment.png", image_bytes(8), None), ("register.pdf", pdf_bytes(), [2, 3])]:
                    (directory / filename).write_bytes(payload)
                    uploaded = client.post("/files", files={"file": (filename, payload)})
                    assert uploaded.status_code == 201, uploaded.text
                    doc = uploaded.json()["id"]
                    assert client.get(f"/files/{doc}/content", headers={"Range": "bytes=0-15"}).status_code == 206
                    job = client.post("/jobs", json={"file_id": doc, "pages": pages, "tables": True}).json()["id"]
                    start = time.monotonic()
                    with (directory / (filename + ".worker.log")).open("wb") as worker_log:
                        subprocess.run([sys.executable, "-m", "ocr_service", "worker", "--once"], cwd=ROOT, env=env,
                            stdout=worker_log, stderr=subprocess.STDOUT, timeout=180, check=True)
                    state = client.get(f"/jobs/{job}").json()
                    assert state["status"] == "succeeded", state
                    results = client.get(f"/jobs/{job}/pages").json()
                    assert all("设备" in p["result"]["text"] for p in results), results
                    assert all(p["result"]["tables"] for p in results)
                    for fmt in ["txt", "json", "csv", "html", "xlsx"]:
                        response = client.get(f"/jobs/{job}/export?format={fmt}")
                        assert response.status_code == 200
                        (directory / (filename + "." + fmt)).write_bytes(response.content)
                    records.append({"document": filename, "pages": [p["page_no"] for p in results], "status": state["status"],
                        "blocks": [len(p["result"]["blocks"]) for p in results], "tables": [len(p["result"]["tables"]) for p in results],
                        "seconds": round(time.monotonic() - start, 2)})
                    print(json.dumps(records[-1], ensure_ascii=False), flush=True)
                assert len(client.get("/search?q=设备").json()["items"]) == 3
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=10)
    report = {"status": "passed", "fixture_kind": "generated_equipment_register", "database": "sqlite",
              "processes": "HTTP API and independent worker", "samples": records, "search_hits": 3,
              "artifacts": directory.relative_to(PACKAGE_ROOT).as_posix(), "accuracy_benchmark": False}
    (PACKAGE_ROOT / "docs/acceptance-result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
