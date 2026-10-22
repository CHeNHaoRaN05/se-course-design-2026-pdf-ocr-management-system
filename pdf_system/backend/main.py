"""应用装配（负责人：甲）。

三条纵向功能线各自持有 router + service + schemas，只通过 core/ 共享底座，
彼此不直接 import（唯一例外：乙的文件模块调用丙的 bridge/lifecycle，属契约 C2/C5）。
"""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from .core.config import Settings, get_settings, validate
from .core.database import build_engine, build_session_factory
from .modules.auth.router import router as auth_router
from .modules.files.router import router as files_router
from .modules.ocr.mount import mount_ocr
from .modules.ocr.router import router as ocr_host_router
from .modules.quota.router import router as quota_router
from .modules.reader.router import router as reader_router
from .modules.search.router import router as search_router

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("pdf_system")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    validate(settings)
    engine = build_engine(settings)
    sessions = build_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        app.state.engine.dispose()
        ocr_engine = getattr(app.state, "ocr_engine", None)
        if ocr_engine is not None:
            ocr_engine.dispose()

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.state.settings, app.state.engine, app.state.sessions = settings, engine, sessions
    app.state.ocr_mounted = False

    @app.get("/health", tags=["00 系统"])
    def health():
        return {"status": "ok", "ocr_mounted": app.state.ocr_mounted,
                "database": settings.database_url.split("://", 1)[0]}

    prefix = settings.api_prefix
    app.include_router(auth_router, prefix=prefix)
    app.include_router(quota_router, prefix=prefix)
    app.include_router(files_router, prefix=prefix)
    app.include_router(reader_router, prefix=prefix)
    app.include_router(search_router, prefix=prefix)
    app.include_router(ocr_host_router, prefix=prefix)

    # 丙：挂载独立 OCR 模块（自带 /api/v1/ocr 路由）
    mount_ocr(app, settings)
    return app
