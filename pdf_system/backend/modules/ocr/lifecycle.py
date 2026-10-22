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

    statement = update(Job).where(Job.file_id == file_id, Job.status.not_in(TERMINAL)).values(
        status="cancelled", lease_token=None, lease_until=None, finished_at=now())
    changed = session.execute(statement).rowcount
    session.execute(update(OcrFile).where(OcrFile.id == file_id).values(active_job_id=None))
    return changed


def purge_file(session, settings, file_id: str) -> None:
    """彻底清理：索引 → 页结果 → 任务 → 页 PNG → 镜像行。"""
    from ocr_service.db import File as OcrFile, Job, Page, TextIndex

    job_ids = [row for row in session.scalars(select(Job.id).where(Job.file_id == file_id))]
    if job_ids:
        session.execute(delete(TextIndex).where(TextIndex.file_id == file_id))
        session.execute(delete(Page).where(Page.job_id.in_(job_ids)))
        session.execute(delete(Job).where(Job.id.in_(job_ids)))
        storage = Path(settings.ocr_storage_dir)
        for job_id in job_ids:
            shutil.rmtree(storage / "pages" / job_id, ignore_errors=True)
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
