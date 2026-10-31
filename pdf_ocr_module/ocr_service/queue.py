"""Database-backed queue; no in-process BackgroundTasks or Redis dependency."""
from datetime import timedelta

from sqlalchemy import and_, or_, select, update

from .db import File, Job, Page, TextIndex, audit, now, uid
from .locking import locked_row

TERMINAL = {"succeeded", "partial_success", "failed", "cancelled"}


def release_file(session, job):
    session.execute(update(File).where(File.id == job.file_id, File.active_job_id == job.id).values(active_job_id=None))


def finish_exhausted(session, job):
    pages = session.scalars(select(Page).where(Page.job_id == job.id)).all()
    success = sum(p.status == "succeeded" for p in pages)
    for page in pages:
        if page.status != "succeeded":
            page.status, page.error = "failed", page.error or "worker_lease_expired"
    job.status = "succeeded" if success == len(pages) else ("partial_success" if success else "failed")
    job.finished_at, job.lease_token, job.lease_until = now(), None, None
    release_file(session, job)


def claim(session_factory, cfg):
    with session_factory.begin() as session:
        stamp = now()
        eligible = or_(and_(Job.status.in_(["queued", "retry_wait"]), Job.available_at <= stamp),
                       and_(Job.status == "running", Job.lease_until < stamp))
        statement = select(Job).where(eligible).order_by(Job.created_at).limit(1)
        if session.bind.dialect.name == "mysql":
            statement = statement.with_for_update(skip_locked=True)
        job = session.scalar(statement)
        if job is None:
            return None
        if job.attempts >= cfg.max_attempts:
            gate = session.execute(update(Job).where(Job.id == job.id, eligible,
                Job.attempts == job.attempts).values(lease_token=uid()))
            if not gate.rowcount:
                return None
            finish_exhausted(session, job)
            return None
        token = uid()
        # CAS also protects SQLite where SELECT FOR UPDATE is unavailable.
        changed = session.execute(update(Job).where(Job.id == job.id, eligible, Job.attempts == job.attempts).values(
            status="running", attempts=job.attempts + 1, lease_token=token,
            lease_until=stamp + timedelta(seconds=cfg.lease_seconds)))
        return (job.id, token) if changed.rowcount else None


def heartbeat(session_factory, cfg, job_id, token):
    with session_factory.begin() as session:
        stamp = now()
        changed = session.execute(update(Job).where(Job.id == job_id, Job.status == "running",
            Job.lease_token == token, Job.lease_until > stamp).values(lease_until=stamp + timedelta(seconds=cfg.lease_seconds)))
        return bool(changed.rowcount)


def locked_job(session, job_id, token):
    job = locked_row(session, Job, Job.id == job_id, Job.status == "running",
                     Job.lease_token == token)
    # Check after acquiring the lock, including any time spent waiting for it.
    return job if job and job.lease_until and job.lease_until > now() else None


def write_index(session, job, page):
    entry = session.scalar(select(TextIndex).where(TextIndex.file_id == job.file_id, TextIndex.page_no == page.page_no))
    if entry is None:
        entry = TextIndex(file_id=job.file_id, page_no=page.page_no)
        session.add(entry)
    entry.job_id, entry.revision, entry.content = job.id, page.revision, page.result["text"]


def save_page(session_factory, job_id, token, page_no, result=None, error=None):
    with session_factory.begin() as session:
        job = locked_job(session, job_id, token)
        if job is None:
            return False
        page = session.scalar(select(Page).where(Page.job_id == job_id, Page.page_no == page_no))
        if page.status == "succeeded":
            return True
        if error:
            page.status, page.error = "failed", error
        else:
            page.status, page.error = "succeeded", None
            page.result, page.revision = result, page.revision + 1
            write_index(session, job, page)
        return True


def complete_attempt(session_factory, cfg, job_id, token):
    with session_factory.begin() as session:
        job = locked_job(session, job_id, token)
        if job is None:
            return
        pages = session.scalars(select(Page).where(Page.job_id == job_id)).all()
        if any(p.status != "succeeded" for p in pages) and job.attempts < cfg.max_attempts:
            job.status = "retry_wait"
            job.available_at = now() + timedelta(seconds=cfg.retry_delay_seconds * 2 ** (job.attempts - 1))
            job.lease_token, job.lease_until = None, None
        else:
            finish_exhausted(session, job)
        audit(session, "worker", "attempt_completed", job.id, status=job.status, attempt=job.attempts)

