"""主系统侧的 OCR 辅助端点（负责人：丙）。

OCR 自身的 15 个接口由 ocr_service 直接挂载在 /api/v1/ocr 下，前端可直连；
这里只补 OCR 模块不提供的「宿主侧」能力：能力探测、配额结算、镜像同步、统计汇总。
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.database import get_session
from ...core.errors import bad_request, conflict, not_found
from ...core.principal import Principal, current_user, owned_file, require_editor
from ..quota.service import usage as quota_usage
from .lifecycle import TERMINAL, ocr_usage
from .quota import settle_job

router = APIRouter(prefix="/ocr-host", tags=["03 OCR 与检索·丙"])


def _require_mounted(request: Request) -> None:
    if not getattr(request.app.state, "ocr_mounted", False):
        raise conflict("OCR 模块未挂载，请检查 Paddle 运行环境与 OCR_PACKAGE_DIR")


@router.get("/capabilities", response_model=dict)
def capabilities(request: Request, session: Session = Depends(get_session), user: Principal = Depends(current_user)):
    mounted = getattr(request.app.state, "ocr_mounted", False)
    return {"mounted": mounted, "storage": str(request.app.state.settings.ocr_storage_dir),
            "device": request.app.state.settings.ocr_device,
            "quota_per_month": request.app.state.settings.monthly_page_quota,
            "quota": quota_usage(session, user.user_id)}


@router.get("/usage", response_model=dict)
def usage(request: Request, session: Session = Depends(get_session), user: Principal = Depends(current_user)):
    _require_mounted(request)
    return {"quota": quota_usage(session, user.user_id), "ocr": ocr_usage(session, user.user_id)}


@router.post("/files/{file_id}/sync", response_model=dict)
def sync_file(file_id: str, request: Request, session: Session = Depends(get_session),
              user: Principal = Depends(require_editor)):
    """重建 OCR 适配层镜像行（上传失败后手动补救）。"""
    _require_mounted(request)
    record = owned_file(session, file_id, user)
    from .bridge import ensure_ocr_file
    ensure_ocr_file(session, record)
    session.commit()
    return {"file_id": file_id, "synced": True}


@router.get("/files/{file_id}/jobs", response_model=dict)
def file_jobs(file_id: str, request: Request, session: Session = Depends(get_session),
              user: Principal = Depends(current_user)):
    """返回该文件最近一次 OCR 任务，供前端直接跳到结果页。"""
    _require_mounted(request)
    owned_file(session, file_id, user)
    from .bridge import latest_job
    job = latest_job(session, file_id)
    return {"job_id": job.id if job else None, "status": job.status if job else None}


@router.post("/jobs/{job_id}/settle", response_model=dict)
def settle(job_id: str, request: Request, session: Session = Depends(get_session),
           user: Principal = Depends(require_editor)):
    """任务终态后结算配额：成功页计费用，失败页退额度。幂等。"""
    _require_mounted(request)
    from ocr_service.db import Job, Page

    job = session.get(Job, job_id)
    if job is None:
        raise not_found()
    if job.owner_id != user.user_id and not user.is_admin:
        raise not_found()
    if job.status not in TERMINAL:
        raise conflict("任务尚未结束，暂不结算")
    succeeded = session.scalar(select(func.count(Page.id)).where(Page.job_id == job_id, Page.status == "succeeded")) or 0
    reserved = len(job.options.get("pages", []) or [])
    changed = settle_job(session, job_id, job.owner_id, reserved_pages=reserved, succeeded_pages=succeeded)
    session.commit()
    return {"job_id": job_id, "reserved_pages": reserved, "succeeded_pages": succeeded, "settled": changed}
