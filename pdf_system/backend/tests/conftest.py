"""测试脚手架：每个模块拿到一份独立的 SQLite 库与存储目录。

注意：OCR 模块能否挂载取决于本机是否装了 cv2 等推理依赖；
未挂载时 test_ocr_contract.py 会整体跳过，主系统的测试不受影响（这正是降级设计的意义）。
"""
import io
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# tests/conftest.py -> tests -> backend -> pdf_system -> se_course_design
WORKSPACE = Path(__file__).resolve().parents[3]
OCR_PACKAGE_DIR = WORKSPACE / "pdf_ocr_module"

SECRET = "test-secret-please-change-0123456789abcdef"


def png_bytes(width: int = 40, height: int = 30) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(buf, format="PNG")
    return buf.getvalue()


def pdf_bytes(pages: int = 3, width: int = 300, height: int = 400) -> bytes:
    """多页 PDF 样本；/files/{id}/pages 依赖真实 PDF。"""
    from PIL import Image
    images = [Image.new("RGB", (width, height), "white") for _ in range(pages)]
    buf = io.BytesIO()
    images[0].save(buf, format="PDF", save_all=True, append_images=images[1:])
    return buf.getvalue()


def make_env(tmp_path: Path, **overrides) -> tuple:
    """构造一个独立应用实例。返回 (settings, app, client)。"""
    from backend.core.config import Settings
    from backend.core.database import build_engine
    from backend.main import create_app
    from backend.models import Base

    kwargs = dict(
        database_url=f"sqlite:///{tmp_path / 'test.sqlite3'}",
        storage_dir=tmp_path / "storage",
        jwt_secret=SECRET,
        ocr_package_dir=OCR_PACKAGE_DIR,
        ocr_enabled=True,
    )
    kwargs.update(overrides)
    settings = Settings(**kwargs)
    app = create_app(settings)
    engine = build_engine(settings)
    Base.metadata.create_all(engine)
    if getattr(app.state, "ocr_mounted", False):
        sys.path.insert(0, str(settings.ocr_package_dir))
        from ocr_service.db import Base as OcrBase
        OcrBase.metadata.create_all(engine)
    return settings, app, TestClient(app)


@pytest.fixture
def env(tmp_path):
    return make_env(tmp_path)


@pytest.fixture
def client(env):
    return env[2]


def register(client, email: str = "alice@example.com", password: str = "secret12345") -> str:
    response = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
