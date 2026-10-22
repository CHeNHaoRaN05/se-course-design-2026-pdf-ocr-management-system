import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = Path(__file__).resolve().parent


def optional_path(name):
    value = os.getenv(name)
    return Path(value).resolve() if value else None


@dataclass
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv("OCR_DATABASE_URL", "sqlite:///./ocr_data/dev.sqlite3"))
    storage: Path = field(default_factory=lambda: Path(os.getenv("OCR_STORAGE", str(ROOT / "ocr_data"))).resolve())
    jwt_secret: str = field(default_factory=lambda: os.getenv("OCR_JWT_SECRET", ""))
    jwt_issuer: str = "pdf-system"
    jwt_audience: str = "ocr-api"
    vendor: Path = field(default_factory=lambda: PACKAGE_ROOT / "third_party/PaddleOCR")
    detector_weights: Path = field(default_factory=lambda: Path(os.getenv("OCR_DET_WEIGHTS", str(PACKAGE_ROOT / "models/text_detector.pdparams"))).resolve())
    recognizer_weights: Path = field(default_factory=lambda: Path(os.getenv("OCR_REC_WEIGHTS", str(PACKAGE_ROOT / "models/text_recognizer.pdparams"))).resolve())
    custom_recognizer: Path | None = field(default_factory=lambda: optional_path("OCR_CUSTOM_REC_WEIGHTS"))
    handwriting_detector: Path | None = field(default_factory=lambda: optional_path("OCR_HANDWRITING_WEIGHTS"))
    torch_python: Path = field(default_factory=lambda: Path(os.getenv("OCR_TORCH_PYTHON", str(ROOT / ".venv-torch/Scripts/python.exe"))).resolve())
    device: str = field(default_factory=lambda: os.getenv("OCR_DEVICE", "cpu"))
    max_upload_bytes: int = 20 * 1024 * 1024
    max_pages: int = 100
    max_pixels: int = 20_000_000
    lease_seconds: int = 120
    max_attempts: int = 3
    retry_delay_seconds: int = 15

