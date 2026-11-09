"""Start the unchanged main API with a disposable SQLite database and OCR disabled.

For local frontend integration checks only. Temporary data is removed on shutdown.
Requires the Python dependencies from pdf_system/requirements.txt.
"""
import secrets
import sys
import tempfile
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.core.config import Settings
from backend.main import create_app
from backend.models import Base


def main():
    with tempfile.TemporaryDirectory(prefix="pdf-frontend-smoke-") as directory:
        root = Path(directory)
        settings = Settings(
            _env_file=None,
            database_url=f"sqlite:///{root / 'smoke.sqlite3'}",
            storage_dir=root / "storage",
            ocr_storage=root / "storage",
            jwt_secret=secrets.token_urlsafe(48),
            ocr_enabled=False,
        )
        app = create_app(settings)
        Base.metadata.create_all(app.state.engine)
        print("Disposable frontend smoke API: http://127.0.0.1:8000 (OCR disabled)", flush=True)
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    main()
