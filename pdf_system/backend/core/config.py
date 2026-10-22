"""全局配置（负责人：甲）。

约定：主系统与 OCR 模块共用同一个数据库、同一个存储目录、同一把 JWT 密钥，
因此这里负责把自身配置**注入为 OCR_* 环境变量**，保证两侧不漂移（契约 C1/C2/C3）。
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/core/config.py -> backend/core -> backend -> pdf_system
ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PDF_", env_file=str(ROOT / ".env"), env_file_encoding="utf-8")

    app_name: str = "PDF 文件显示与管理系统"
    api_prefix: str = "/api/v1"

    # ---- 数据库（生产用 mysql+pymysql://user:pwd@host/pdf_system?charset=utf8mb4）----
    database_url: str = "sqlite:///" + (ROOT / "data" / "dev.sqlite3").as_posix()
    database_echo: bool = False

    # ---- 鉴权（claims 必须与 OCR 模块一致）----
    jwt_secret: str = ""
    jwt_issuer: str = "pdf-system"
    jwt_audience: str = "ocr-api"
    jwt_expire_minutes: int = 120

    # ---- 存储（与 OCR_STORAGE 指向同一目录）----
    storage_dir: Path = ROOT / "data" / "storage"
    max_upload_bytes: int = 20 * 1024 * 1024
    max_pages: int = 100
    max_pixels: int = 20_000_000

    # ---- 配额（甲）----
    monthly_page_quota: int = 500

    # ---- OCR 模块装配（丙）----
    ocr_enabled: bool = True
    ocr_package_dir: Path = WORKSPACE / "pdf_ocr_module"
    ocr_storage: Path | None = None  # 默认与主存储同目录
    ocr_device: str = "cpu"

    @property
    def ocr_storage_dir(self) -> Path:
        return self.ocr_storage or self.storage_dir

    def ocr_env(self) -> dict[str, str]:
        """导出给 ocr_service 的环境变量；缺失的能力由 OCR 模块自行关闭。"""
        return {
            "OCR_DATABASE_URL": self.database_url,
            "OCR_STORAGE": str(self.ocr_storage_dir),
            "OCR_JWT_SECRET": self.jwt_secret,
            "OCR_DEVICE": self.ocr_device,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate(settings: Settings) -> None:
    """启动自检：把配置错误挡在启动期，而不是第一次请求。"""
    if len(settings.jwt_secret) < 32:
        raise RuntimeError("PDF_JWT_SECRET 未设置或短于 32 字符；OCR 模块会拒绝启动")
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.ocr_storage_dir.mkdir(parents=True, exist_ok=True)
