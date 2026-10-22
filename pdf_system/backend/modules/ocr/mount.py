"""把独立 OCR 模块挂进主系统（负责人：丙）。

要点：
  1. 先把主系统配置注入为 OCR_* 环境变量，保证两侧同库、同存储、同密钥；
  2. 用 dependency_overrides 让 OCR 复用主系统的登录解析（停用用户立即失效）；
  3. 传入 before_enqueue 配额钩子；
  4. 缺 Paddle 环境时降级为「未挂载」，主系统其余功能照常可用。
"""
import logging
import os
import sys
from pathlib import Path

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

log = logging.getLogger(__name__)


def mount_ocr(app, settings) -> bool:
    from .bridge import set_ready

    set_ready(False)
    if not settings.ocr_enabled:
        log.info("OCR 模块已在配置中关闭")
        return False

    package_dir = Path(settings.ocr_package_dir)
    if not (package_dir / "ocr_service").is_dir():
        log.warning("未找到 OCR 模块目录：%s", package_dir / "ocr_service")
        return False

    sys.path.insert(0, str(package_dir))
    for key, value in settings.ocr_env().items():
        os.environ[key] = value  # 覆盖，避免遗留环境变量造成两侧漂移

    try:
        from ocr_service.api import install
        from ocr_service.auth import current_user as ocr_current_user
        from ocr_service.config import Settings as OcrSettings
        from ocr_service.schemas import JobCreate  # noqa: F401  仅用于确认包可用
    except Exception as exc:  # Paddle / 依赖缺失时必须让主系统继续启动
        log.warning("OCR 模块加载失败，已降级：%s", exc)
        return False

    from ...core.principal import bearer, resolve_principal
    from .quota import make_before_enqueue

    ocr_settings = OcrSettings()
    ocr_settings.jwt_secret = settings.jwt_secret
    install(app, ocr_settings, before_enqueue=make_before_enqueue(settings))

    def host_principal(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        try:
            principal = resolve_principal(request, credentials)
        except HTTPException as exc:
            raise exc
        from ocr_service.auth import Principal as OcrPrincipal
        return OcrPrincipal(principal.user_id, principal.role)

    app.dependency_overrides[ocr_current_user] = host_principal
    app.state.ocr_mounted = True
    set_ready(True)
    log.info("OCR 模块已挂载：%s", package_dir / "ocr_service")
    return True
