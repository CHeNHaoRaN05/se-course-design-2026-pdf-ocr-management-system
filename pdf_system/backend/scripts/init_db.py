"""初始化数据库：主系统表 + OCR 模块表（负责人：甲，丙提供 OCR 侧建表）。

    python -m backend.scripts.init_db
"""
from backend.core.config import get_settings, validate
from backend.core.database import build_engine
from backend.models import Base


def main() -> None:
    settings = get_settings()
    validate(settings)
    engine = build_engine(settings)
    Base.metadata.create_all(engine)
    print("主系统表已建立（已存在的表不会被迁移）")

    # OCR 模块使用自己的 DeclarativeBase，需要在同库单独建一次
    import os
    import sys
    from pathlib import Path
    package_dir = Path(settings.ocr_package_dir)
    if (package_dir / "ocr_service").is_dir():
        sys.path.insert(0, str(package_dir))
        for key, value in settings.ocr_env().items():
            os.environ[key] = value
        from ocr_service.db import Base as OcrBase
        OcrBase.metadata.create_all(engine)
        print("OCR 模块表已建立")
    else:
        print(f"跳过 OCR 建表：未找到 {package_dir / 'ocr_service'}")


if __name__ == "__main__":
    main()
