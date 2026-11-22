"""Run the local API, Paddle OCR worker and Vite from a shared configuration."""

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

from backend.core.config import ROOT, get_settings, validate
from backend.scripts.init_db import main as init_db


def wait_for_http(url, process):
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline and process.poll() is None:
        try:
            with urlopen(url, timeout=2) as response:
                return response.read()
        except (URLError, TimeoutError):
            time.sleep(0.5)
    raise RuntimeError(f"Startup failed: {url}")


def main():
    settings = get_settings()
    if not settings.ocr_enabled:
        raise RuntimeError("Set PDF_OCR_ENABLED=true to start the complete local system")
    validate(settings)
    package = settings.ocr_package_dir.resolve()
    node = shutil.which("node")
    frontend = ROOT / "frontend"
    vite = frontend / "node_modules" / "vite" / "bin" / "vite.js"
    if not node or not vite.is_file():
        raise RuntimeError("Install Node and run npm ci in pdf_system/frontend")
    for port in (8000, 5173):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", port))

    ocr_env = {**os.environ, **settings.ocr_env(),
               "OCR_STORAGE": str(settings.storage_dir.resolve()), "OCR_DEVELOPMENT_MODE": "0"}
    # Keep the host working directory for relative SQLite URLs in the local .env.
    ocr_env["PYTHONPATH"] = os.pathsep.join(filter(None, (str(package), ocr_env.get("PYTHONPATH"))))
    subprocess.run(
        [sys.executable, "-c",
         "import paddle; from ocr_service.config import Settings; "
         "cfg = Settings(); "
         "raise SystemExit(None if cfg.detector_weights.is_file() and cfg.recognizer_weights.is_file() "
         "else 'Download the Paddle weights first')"],
        cwd=ROOT, env=ocr_env, check=True,
    )
    init_db()
    processes = []
    api_url = "http://127.0.0.1:8000"
    web_url = "http://127.0.0.1:5173"
    try:
        api = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:create_app", "--factory",
             "--host", "127.0.0.1", "--port", "8000"], cwd=ROOT,
        )
        processes.append(api)
        schema = json.loads(wait_for_http(api_url + "/openapi.json", api))
        if "/api/v1/ocr/jobs" not in schema["paths"]:
            raise RuntimeError("The API started without its OCR routes")
        processes.append(subprocess.Popen(
            [sys.executable, "-m", "ocr_service", "worker"], cwd=ROOT, env=ocr_env,
        ))
        web = subprocess.Popen(
            [node, str(vite), "--host", "127.0.0.1", "--port", "5173", "--strictPort"],
            cwd=frontend, env={**os.environ, "SE_API_TARGET": api_url},
        )
        processes.append(web)
        wait_for_http(web_url, web)
        print(f"Local system ready: {web_url}", flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        raise RuntimeError("A local service stopped. Check the output above.")
    except KeyboardInterrupt:
        pass
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        for process in processes:
            process.wait()


if __name__ == "__main__":
    main()
