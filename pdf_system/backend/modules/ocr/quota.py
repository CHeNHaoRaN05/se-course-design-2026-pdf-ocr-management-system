"""OCR 与配额的衔接（负责人：丙，调用甲的接口，契约 C3）。

before_enqueue(session, user, file, page_numbers)
    user        : OCR 模块的 Principal（只用 user_id / role）
    file        : OCR 模块的 File ORM 行
    page_numbers: 本次入队页码列表
约定：在 OCR 建任务的**同一事务**内执行；超额抛 HTTPException(429)；**绝不自行 commit**。

由于 OCR 钩子拿不到 job_id，预留流水以 ref_id=None 记账；
任务终态时由 /ocr-host/jobs/{id}/settle 按 job 汇总并幂等结算。
"""
from sqlalchemy import select

from ...models import QuotaLedger, current_month, uid
from ..quota.service import release, reserve, settle

CLOSE_REASON = "job_close"


def make_before_enqueue(settings):
    """闭包持有配置，避免从 session 里反向找 settings。"""
    def before_enqueue(session, user, file, page_numbers) -> None:
        reserve(session, user.user_id, len(page_numbers), ref_id=None, limit=settings.monthly_page_quota)
    return before_enqueue


def _close(session, job_id: str, owner_id: str, succeeded: int) -> bool:
    """幂等标记：同一 job 只结算一次。返回 False 表示已结算过。"""
    exists = session.scalar(select(QuotaLedger.id).where(QuotaLedger.ref_id == job_id,
                                                         QuotaLedger.reason == CLOSE_REASON))
    if exists:
        return False
    session.add(QuotaLedger(id=uid(), user_id=owner_id, month=current_month(), pages=succeeded,
                            reason=CLOSE_REASON, ref_id=job_id))
    return True


def settle_job(session, job_id: str, owner_id: str, *, reserved_pages: int, succeeded_pages: int) -> bool:
    """成功页转已用，失败/未处理页退还额度。"""
    if not _close(session, job_id, owner_id, succeeded_pages):
        return False
    if succeeded_pages > 0:
        settle(session, owner_id, succeeded_pages, ref_id=job_id)
    refund = max(0, reserved_pages - succeeded_pages)
    if refund > 0:
        release(session, owner_id, refund, ref_id=job_id)
    return True


def release_job(session, job_id: str, owner_id: str, *, pages: int) -> bool:
    """任务被取消：全额退款。"""
    if not _close(session, job_id, owner_id, 0):
        return False
    release(session, owner_id, pages, ref_id=job_id)
    return True
