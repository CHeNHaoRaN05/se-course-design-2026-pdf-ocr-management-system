"""OCR 侧生命周期（负责人：丙，契约 C5）。

供乙的文件模块调用：
  cancel_tasks(session, file_id)        软删除时取消未完成任务
  purge_file(session, settings, file_id) 彻底删除时清理任务 / 页 PNG / 全文索引
"""
import logging
import shutil
from pathlib import Path

from sqlalchemy import delete, select, update

log = logging.getLogger(__name__)

TERMINAL = {"succeeded", "partial_success", "failed", "cancelled"}


def cancel_tasks(session, file_id: str) -> int:
    """取消该文件所有未终态任务并释放文件锁。"""
    from ocr_service.db import File as OcrFile, Job, now

    from ocr_service.locking import locked_row
    from .quota import release_job
    ids = session.scalars(select(Job.id).where(Job.file_id == file_id).order_by(Job.id)).all()
    changed = 0
    for ident in ids:
        job = locked_row(session, Job, Job.id == ident)
        if job and job.status not in TERMINAL:
            job.status, job.finished_at = "cancelled", now()
            job.lease_token, job.lease_until = None, None
            session.flush()
            release_job(session, job.id, job.owner_id, pages=len(job.options.get("pages", [])))
            changed += 1
    session.execute(update(OcrFile).where(OcrFile.id == file_id).values(active_job_id=None))
    return changed



def purge_file(session, settings, file_id: str) -> None:
    """彻底清理：索引 → 页结果 → 任务 → 页 PNG → 镜像行。"""
    from ocr_service.db import File as OcrFile, Job, Page, TextIndex

    from ocr_service.accounting import settle_terminal
    from ...core.file_cleanup import after_commit_remove
    from ocr_service.media import safe_path
    cancel_tasks(session, file_id)
    for job in session.scalars(select(Job).where(Job.file_id == file_id)):
        settle_terminal(session, job)
    session.execute(delete(TextIndex).where(TextIndex.file_id == file_id))
    job_ids = [row for row in session.scalars(select(Job.id).where(Job.file_id == file_id))]
    if job_ids:
        session.execute(delete(Page).where(Page.job_id.in_(job_ids)))
        session.execute(delete(Job).where(Job.id.in_(job_ids)))
        storage = Path(settings.ocr_storage_dir)
        for job_id in job_ids:
            after_commit_remove(session, safe_path(storage, f"pages/{job_id}"), directory=True)
    session.execute(delete(OcrFile).where(OcrFile.id == file_id))
    log.info("purged OCR data for file=%s jobs=%d", file_id, len(job_ids))


def ocr_usage(session, user_id: str) -> dict:
    """OCR 侧统计：任务状态分布与成功页数。"""
    from ocr_service.db import Job, Page
    from sqlalchemy import func

    statuses = dict(session.execute(
        select(Job.status, func.count()).where(Job.owner_id == user_id).group_by(Job.status)).all())
    succeeded = session.scalar(
        select(func.count(Page.id)).join(Job).where(Job.owner_id == user_id, Page.status == "succeeded")) or 0
    return {"jobs_by_status": statuses, "recognized_page_results": succeeded}
