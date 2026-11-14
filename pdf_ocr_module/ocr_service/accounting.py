"""Host quota settlement usable by a separate worker, without importing the host.

The existing host tables are reflected; this module never creates/migrates them.
All changes participate in the caller's transaction. No frontend callback is needed.
"""
from hashlib import sha256

from sqlalchemy import MetaData, Table, inspect, select, update

from .db import Job, Page, now, uid
from .locking import locked_row


def close_reservation(session, job_id, owner_id, month, reserved, succeeded):
    if not 0 <= succeeded <= reserved:
        raise ValueError("Invalid reservation settlement")
    meta = MetaData()
    accounts = Table("quota_accounts", meta, autoload_with=session.connection())
    ledger = Table("quota_ledger", meta, autoload_with=session.connection())
    where = (accounts.c.user_id == owner_id, accounts.c.month == month)
    # Acquire a write lock before reading the idempotency marker, on both dialects.
    session.execute(update(accounts).where(*where).values(updated_at=accounts.c.updated_at))
    account = session.execute(select(accounts).where(*where).with_for_update()).mappings().first()
    marker = session.execute(select(ledger.c.id).where(
        ledger.c.ref_id == job_id, ledger.c.reason == "job_close").with_for_update()).first()
    if marker:
        return False
    if account is None or account["pages_reserved"] < reserved:
        raise ValueError("Quota reservation missing; reconciliation required")
    stamp = now()
    session.execute(update(accounts).where(*where).values(
        pages_reserved=accounts.c.pages_reserved-reserved,
        pages_used=accounts.c.pages_used+succeeded, updated_at=stamp))
    for pages, reason in [(-succeeded, "settle_reserve"), (succeeded, "settle_used"),
                          (-(reserved-succeeded), "release")]:
        if pages:
            session.execute(ledger.insert().values(id=uid(), user_id=owner_id, month=month,
                pages=pages, reason=reason, ref_id=job_id, created_at=stamp))
    session.execute(ledger.insert().values(
        id=sha256(("ocr-close:"+job_id).encode()).hexdigest()[:32],
        user_id=owner_id, month=month, pages=succeeded, reason="job_close", ref_id=job_id, created_at=stamp))
    return True


def settle_terminal(session, job):
    job = locked_row(session, Job, Job.id == job.id)
    if job is None or job.status not in {"succeeded", "partial_success", "failed", "cancelled"}:
        return False
    reservation = job.options.get("_quota")
    if reservation is None:
        # Upgrade path: old hosted jobs reserved in their creation month without ref_id.
        if not inspect(session.connection()).has_table("quota_accounts"):
            return False  # explicitly isolated development/test service
        reservation = {"month": job.created_at.strftime("%Y-%m"), "pages": len(job.options.get("pages", []))}
    success = 0 if job.status == "cancelled" else len(session.scalars(
        select(Page.id).where(Page.job_id == job.id, Page.status == "succeeded")).all())
    return close_reservation(session, job.id, job.owner_id, reservation["month"], reservation["pages"], success)
