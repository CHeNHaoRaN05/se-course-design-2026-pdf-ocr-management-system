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
    database_url: str = field(default_factory=lambda: os.getenv("OCR_DATABASE_URL") or "sqlite:///" + (ROOT / "ocr_data/dev.sqlite3").as_posix())
    storage: Path = field(default_factory=lambda: Path((os.getenv("OCR_STORAGE") or str(ROOT / "ocr_data"))).resolve())
    jwt_secret: str = field(default_factory=lambda: os.getenv("OCR_JWT_SECRET", ""))
    jwt_issuer: str = field(default_factory=lambda: os.getenv("OCR_JWT_ISSUER") or "pdf-system")
    jwt_audience: str = field(default_factory=lambda: os.getenv("OCR_JWT_AUDIENCE") or "ocr-development-only")
    development_mode: bool = field(default_factory=lambda: os.getenv("OCR_DEVELOPMENT_MODE") == "1")
    vendor: Path = field(default_factory=lambda: PACKAGE_ROOT / "third_party/PaddleOCR")
    detector_weights: Path = field(default_factory=lambda: Path(os.getenv("OCR_DET_WEIGHTS", str(PACKAGE_ROOT / "models/text_detector.pdparams"))).resolve())
    recognizer_weights: Path = field(default_factory=lambda: Path(os.getenv("OCR_REC_WEIGHTS", str(PACKAGE_ROOT / "models/text_recognizer.pdparams"))).resolve())
    custom_recognizer: Path | None = field(default_factory=lambda: optional_path("OCR_CUSTOM_REC_WEIGHTS"))
    handwriting_detector: Path | None = field(default_factory=lambda: optional_path("OCR_HANDWRITING_WEIGHTS"))
    torch_python: Path = field(default_factory=lambda: Path(os.getenv("OCR_TORCH_PYTHON", str(ROOT / ".venv-torch/Scripts/python.exe"))).resolve())
    device: str = field(default_factory=lambda: os.getenv("OCR_DEVICE") or "cpu")
    max_upload_bytes: int = field(default_factory=lambda: int(os.getenv("OCR_MAX_UPLOAD_BYTES") or 20 * 1024 * 1024))
    max_pages: int = field(default_factory=lambda: int(os.getenv("OCR_MAX_PAGES") or 100))
    max_pixels: int = field(default_factory=lambda: int(os.getenv("OCR_MAX_PIXELS") or 20_000_000))
    lease_seconds: int = field(default_factory=lambda: int(os.getenv("OCR_LEASE_SECONDS") or 120))
    max_attempts: int = field(default_factory=lambda: int(os.getenv("OCR_MAX_ATTEMPTS") or 3))
    retry_delay_seconds: int = field(default_factory=lambda: int(os.getenv("OCR_RETRY_DELAY_SECONDS") or 15))


    def __post_init__(self):
        for name in ("max_upload_bytes", "max_pages", "max_pixels", "lease_seconds", "max_attempts"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds must not be negative")
        if self.development_mode and self.jwt_audience != "ocr-development-only":
            raise ValueError("Development API requires isolated OCR_JWT_AUDIENCE=ocr-development-only")
