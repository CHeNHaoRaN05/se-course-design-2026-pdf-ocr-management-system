"""Opt-in REAL Paddle + HTTP + separate worker smoke (not a 200-page benchmark)."""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
import httpx
import pytest
from ocr_service.config import Settings
from ocr_service.model_files import verify_official
from .documents import image_bytes

pytestmark = pytest.mark.real_ocr


def test_real_host_http_worker_search(tmp_path):
    if os.getenv("RUN_REAL_OCR") != "1":
        pytest.skip("RUN_REAL_OCR=1 plus Paddle and official weights required; no accuracy claim")
    cfg = Settings()
    verify_official(cfg)  # Explicit opt-in fails, rather than skips, on missing/bad weights.
    root = Path(__file__).resolve().parents[3]
    env = dict(os.environ, PDF_DATABASE_URL="sqlite:///"+(tmp_path/"db.sqlite3").as_posix(),
        PDF_STORAGE_DIR=str(tmp_path/"storage"), PDF_JWT_SECRET="integration-test-"+"x"*40,
        PDF_OCR_PACKAGE_DIR=str(root/"pdf_ocr_module"), OCR_STORAGE=str(tmp_path/"storage"),
        OCR_DATABASE_URL="sqlite:///"+(tmp_path/"db.sqlite3").as_posix(),
        OCR_DET_WEIGHTS=str(cfg.detector_weights), OCR_REC_WEIGHTS=str(cfg.recognizer_weights),
        PYTHONPATH=os.pathsep.join([str(root/"pdf_system"),str(root/"pdf_ocr_module")]))
    setup = "from backend.main import create_app; from backend.models import Base; from ocr_service.db import Base as O; a=create_app(); Base.metadata.create_all(a.state.engine); O.metadata.create_all(a.state.engine)"
    subprocess.run([sys.executable,"-c",setup],env=env,check=True,timeout=60)
    with socket.socket() as binding:
        binding.bind(("127.0.0.1",0))
        port = binding.getsockname()[1]
    with (tmp_path/"http.log").open("wb") as log:
        server = subprocess.Popen([sys.executable,"-m","uvicorn","backend.main:create_app","--factory",
            "--host","127.0.0.1","--port",str(port)],env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}",trust_env=False,timeout=30) as c:
                deadline=time.monotonic()+30
                while True:
                    try:
                        health=c.get("/health")
                        if health.status_code==200:
                            assert health.json()["ocr_mounted"]
                            break
                    except httpx.ConnectError:
                        pass
                    if time.monotonic()>deadline or server.poll() is not None:
                        pytest.fail("HTTP startup failed; inspect http.log")
                    time.sleep(.2)
                token=c.post("/api/v1/auth/register",json={"email":"real@example.com","password":"secret12345"}).json()["access_token"]
                c.headers["Authorization"]="Bearer "+token
                uploaded=c.post("/api/v1/files",files={"file":("equipment.png",image_bytes(),"image/png")})
                assert uploaded.status_code==201,uploaded.text
                job=c.post("/api/v1/ocr/jobs",json={"file_id":uploaded.json()["id"]}).json()["id"]
                subprocess.run([sys.executable,"-m","ocr_service","worker","--once"],env=env,check=True,timeout=300)
                assert c.get(f"/api/v1/ocr/jobs/{job}").json()["status"]=="succeeded"
                assert c.get("/api/v1/search",params={"q":"设备"}).json()["items"]
                quota=c.get("/api/v1/quota").json()
                assert quota["pages_reserved"]==0 and quota["pages_used"]==1
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=10)
