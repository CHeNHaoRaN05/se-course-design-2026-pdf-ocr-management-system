from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

from sqlalchemy import select, update
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Session
from sqlalchemy.sql.dml import Update

from ocr_service.db import Job, Page, TextIndex, now
from ocr_service.locking import locked_row
from ocr_service.queue import claim, save_page
from ocr_service.worker import Worker
from .test_inventory_workflow import API, InventoryEngine, enqueue, upload


def test_mysql_uses_locking_read_not_noop_rowcount():
    session = Mock()
    session.bind.dialect.name = "mysql"
    locked_row(session, Job, Job.id == "job")
    statement = session.scalar.call_args.args[0]
    assert "FOR UPDATE" in str(statement.compile(dialect=mysql.dialect()))
    session.execute.assert_not_called()


def test_noop_rowcount_zero_does_not_reject_worker_or_correction(service, monkeypatch):
    original = Session.execute
    def execute(session, statement, *args, **kwargs):
        result = original(session, statement, *args, **kwargs)
        # Model drivers configured to report changed rows for an id=id lock.
        if isinstance(statement, Update) and set(statement._values) == {statement.table.c.id}:
            return SimpleNamespace(rowcount=0)
        return result
    monkeypatch.setattr(Session, "execute", execute)
    task = enqueue(service, upload(service))
    Worker(service.config, service.sessions, InventoryEngine()).run_once()
    page = service.client.get(f"{API}/jobs/{task}/pages/1").json()
    assert page["status"] == "succeeded"
    blocks = page["result"]["blocks"]
    blocks[0]["text"] = "事务内校对"
    response = service.client.patch(f"{API}/jobs/{task}/pages/1",
                                   json={"expected_revision": 1, "blocks": blocks})
    assert response.status_code == 200, response.text
    with service.sessions() as session:
        assert session.scalar(select(TextIndex.content)) == "事务内校对"
        assert session.scalar(select(Page.revision)) == 2


def test_expired_lease_rejected_without_replacement(service):
    task = enqueue(service, upload(service))
    lease = claim(service.sessions, service.config)
    with service.sessions.begin() as session:
        session.execute(update(Job).where(Job.id == task).values(lease_until=now() - timedelta(seconds=1)))
    assert not save_page(service.sessions, *lease, 1, error="late")
    with service.sessions() as session:
        assert session.scalar(select(Page.status)) == "pending"
        assert session.scalar(select(TextIndex.id)) is None


def test_active_job_prevents_correction_and_failed_revision_keeps_index(service):
    document = upload(service)
    task = enqueue(service, document)
    Worker(service.config, service.sessions, InventoryEngine()).run_once()
    page = service.client.get(f"{API}/jobs/{task}/pages/1").json()
    body = {"expected_revision": 99, "blocks": page["result"]["blocks"]}
    assert service.client.patch(f"{API}/jobs/{task}/pages/1", json=body).status_code == 409
    enqueue(service, document)
    body["expected_revision"] = 1
    assert service.client.patch(f"{API}/jobs/{task}/pages/1", json=body).status_code == 409
    with service.sessions() as session:
        assert session.scalar(select(TextIndex.revision)) == 1
