"""Mount OCR with explicit configuration, rollback and terminal reconciliation."""
import asyncio
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path
from fastapi import Depends

log = logging.getLogger(__name__)


def reconcile_terminal(sessions):
    from sqlalchemy import exists, select
    from ocr_service.db import Job
    from ocr_service.accounting import settle_terminal
    from ...models import QuotaLedger
    with sessions() as session:
        ids = session.scalars(select(Job.id).where(
            Job.status.in_(["succeeded", "partial_success", "failed", "cancelled"]),
            ~exists(select(QuotaLedger.id).where(QuotaLedger.ref_id == Job.id,
                                                QuotaLedger.reason == "job_close"))).limit(100)).all()
    for ident in ids:
        try:
            with sessions.begin() as session:
                job = session.get(Job, ident)
                if job:
                    settle_terminal(session, job)
        except Exception:
            log.exception("Quota reconciliation failed for job=%s", ident)


def mount_ocr(app, settings):
    from .bridge import set_ready
    set_ready(False)
    if not settings.ocr_enabled:
        return False
    package_dir = str(Path(settings.ocr_package_dir).resolve())
    if not (Path(package_dir) / "ocr_service").is_dir():
        log.warning("OCR package unavailable: %s", package_dir)
        return False
    added = package_dir not in sys.path
    routes, overrides = list(app.router.routes), dict(app.dependency_overrides)
    prior_state = dict(app.state._state)
    if added:
        sys.path.insert(0, package_dir)
    try:
        from ocr_service.api import install
        from ocr_service.auth import current_user as ocr_current_user, Principal as OcrPrincipal
        from ocr_service.config import Settings as OcrSettings
        from ...core.principal import bearer, resolve_principal
        from fastapi import Request
        from fastapi.security import HTTPAuthorizationCredentials
        from .quota import make_before_enqueue
        cfg = OcrSettings(database_url=settings.database_url, storage=settings.storage_dir.resolve(),
            jwt_secret=settings.jwt_secret, jwt_issuer=settings.jwt_issuer, jwt_audience=settings.jwt_audience,
            device=settings.ocr_device, max_upload_bytes=settings.max_upload_bytes,
            max_pages=settings.max_pages, max_pixels=settings.max_pixels, development_mode=False)
        install(app, cfg, before_enqueue=make_before_enqueue(settings))
        def host_principal(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
            principal = resolve_principal(request, credentials)
            return OcrPrincipal(principal.user_id, principal.role)
        app.dependency_overrides[ocr_current_user] = host_principal
        app.state.ocr_hosted = True
        app.state.ocr_mounted = True
        previous_lifespan = app.router.lifespan_context
        @asynccontextmanager
        async def lifespan(application):
            stop = asyncio.Event()
            async def reconcile():
                while not stop.is_set():
                    try:
                        await asyncio.to_thread(reconcile_terminal, app.state.ocr_sessions)
                    except Exception:
                        log.exception("OCR settlement sweep failed")
                    try:
                        await asyncio.wait_for(stop.wait(), timeout=30)
                    except asyncio.TimeoutError:
                        pass
            async with previous_lifespan(application):
                task = asyncio.create_task(reconcile())
                try:
                    yield
                finally:
                    stop.set()
                    await task
        app.router.lifespan_context = lifespan
        set_ready(True)
        return True
    except Exception:
        engine = getattr(app.state, "ocr_engine", None)
        if engine is not None and engine is not prior_state.get("ocr_engine"):
            engine.dispose()
        app.router.routes[:] = routes
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        app.state._state.clear()
        app.state._state.update(prior_state)
        if added:
            sys.path.remove(package_dir)
        log.exception("OCR mount failed; host remains available")
        return False
