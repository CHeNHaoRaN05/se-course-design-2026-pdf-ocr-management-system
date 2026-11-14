"""C3: reserve in enqueue transaction, settle on the server at terminal state."""
from sqlalchemy import select
from ...models import QuotaLedger, current_month
from ..quota.service import reserve

CLOSE_REASON = "job_close"


def make_before_enqueue(settings):
    def before_enqueue(session, user, file, page_numbers):
        reserve(session, file.owner_id, len(page_numbers), ref_id=file.active_job_id,
                limit=settings.monthly_page_quota)
        month = session.scalar(select(QuotaLedger.month).where(
            QuotaLedger.ref_id == file.active_job_id, QuotaLedger.reason == "reserve"))
        session.info["ocr_reservation"] = {"month": month, "pages": len(page_numbers)}
    return before_enqueue


def settle_job(session, job_id, owner_id, *, reserved_pages, succeeded_pages):
    from ocr_service.accounting import settle_terminal
    from ocr_service.db import Job
    from ocr_service.locking import locked_row
    job = locked_row(session, Job, Job.id == job_id, Job.owner_id == owner_id)
    if job is None:
        return False
    return settle_terminal(session, job)


def release_job(session, job_id, owner_id, *, pages):
    return settle_job(session, job_id, owner_id, reserved_pages=pages, succeeded_pages=0)
