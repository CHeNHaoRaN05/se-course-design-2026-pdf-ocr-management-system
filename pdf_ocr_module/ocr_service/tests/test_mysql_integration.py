"""Real MySQL 8 regressions. MYSQL_TEST_URL needs CREATE/DROP test DB rights."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text, update, func
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from pymysql.constants import CLIENT

from ocr_service.config import Settings
from ocr_service.db import Base, File, Job, Page, TextIndex, now
from ocr_service.queue import claim, heartbeat, save_page, complete_attempt
from ocr_service.accounting import settle_terminal
from backend.models import Base as HostBase, QuotaAccount, QuotaLedger, current_month
from backend.modules.quota.service import reserve

pytestmark = pytest.mark.mysql


@pytest.fixture
def mysql(tmp_path):
    raw = os.getenv("MYSQL_TEST_URL")
    if not raw:
        pytest.skip("MYSQL_TEST_URL required for real MySQL 8 acceptance")
    url = make_url(raw)
    name = "line03_test_" + uuid4().hex
    admin = create_engine(url.set(database="mysql"), pool_pre_ping=True)
    with admin.begin() as c:
        c.execute(text(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4"))
    engine = create_engine(url.set(database=name), connect_args={"client_flag": 0}, pool_pre_ping=True)
    try:
        HostBase.metadata.create_all(engine)
        Base.metadata.create_all(engine)
        with engine.connect() as c:
            assert not c.connection.driver_connection.client_flag & CLIENT.FOUND_ROWS
        cfg = Settings(database_url=str(url), storage=tmp_path, jwt_secret="x"*40, max_attempts=1)
        yield SimpleNamespace(engine=engine, sessions=sessionmaker(engine, expire_on_commit=False), cfg=cfg)
    finally:
        engine.dispose()
        assert name.startswith("line03_test_") and len(name) == len("line03_test_")+32
        with admin.begin() as c:
            c.execute(text(f"DROP DATABASE `{name}`"))
        admin.dispose()


def seed(mysql, count=1):
    ids = []
    with mysql.sessions.begin() as s:
        for _ in range(count):
            ident, file_id = uuid4().hex, uuid4().hex
            s.add(File(id=file_id, owner_id="owner", name="中文设备.pdf", storage_key="uploads/test.bin",
                       media_type="application/pdf", sha256="a"*64, size=1, page_count=1, active_job_id=ident))
            s.flush()
            reserve(s, "owner", 1, ref_id=ident, limit=100)
            s.add(Job(id=ident, file_id=file_id, owner_id="owner", generation=1,
                      available_at=now()-timedelta(seconds=2), options={"pages":[1], "_quota":{"month":current_month(),"pages":1}}))
            s.flush()
            s.add(Page(job_id=ident, page_no=1))
            ids.append(ident)
    return ids


def test_mysql_datetime_zero_precision_heartbeat_without_found_rows(mysql, monkeypatch):
    seed(mysql)
    lease = claim(mysql.sessions, mysql.cfg)
    stamp = now().replace(microsecond=100000)
    deadline = stamp.replace(microsecond=0)+timedelta(seconds=mysql.cfg.lease_seconds+1)
    with mysql.sessions.begin() as s:
        s.execute(update(Job).where(Job.id == lease[0]).values(lease_until=deadline))
    monkeypatch.setattr("ocr_service.queue.now", lambda: stamp)
    for _ in range(4):
        assert heartbeat(mysql.sessions, mysql.cfg, *lease)
    with mysql.sessions() as s:
        assert s.get(Job, lease[0]).lease_until == deadline
    monkeypatch.setattr("ocr_service.queue.now", lambda: deadline+timedelta(seconds=1))
    assert not heartbeat(mysql.sessions, mysql.cfg, *lease)


def test_mysql_skip_locked_claims_other_job(mysql):
    ids = seed(mysql, 2)
    with mysql.sessions.begin() as held:
        first = held.scalar(select(Job).where(Job.id == ids[0]).with_for_update())
        with ThreadPoolExecutor(1) as pool:
            lease = pool.submit(claim, mysql.sessions, mysql.cfg).result(timeout=10)
        assert lease and lease[0] != first.id and lease[0] in ids


def test_mysql_worker_ngram_and_server_settlement(mysql):
    seed(mysql)
    lease = claim(mysql.sessions, mysql.cfg)
    assert save_page(mysql.sessions, *lease, 1, result={"text":"中文设备借用登记"})
    complete_attempt(mysql.sessions, mysql.cfg, *lease)
    with mysql.sessions() as s:
        assert s.scalar(text("SELECT count(*) FROM pdf_text_index WHERE MATCH(content) AGAINST ('设备' IN NATURAL LANGUAGE MODE)")) == 1
        a = s.get(QuotaAccount, ("owner", current_month()))
        assert (a.pages_reserved, a.pages_used) == (0,1)
        assert s.scalar(select(func.count()).select_from(QuotaLedger).where(QuotaLedger.reason == "job_close")) == 1


def test_mysql_ten_concurrent_closes_are_idempotent(mysql):
    ident = seed(mysql)[0]
    with mysql.sessions.begin() as s:
        s.get(Job, ident).status = "succeeded"
        s.scalar(select(Page).where(Page.job_id==ident)).status = "succeeded"
    def close(_):
        with mysql.sessions.begin() as s:
            return settle_terminal(s, s.get(Job, ident))
    with ThreadPoolExecutor(10) as pool:
        assert sum(pool.map(close, range(10))) == 1
    with mysql.sessions() as s:
        a = s.get(QuotaAccount, ("owner", current_month()))
        assert (a.pages_reserved,a.pages_used) == (0,1)


def test_mysql_concurrent_first_account_reserve(mysql):
    import threading
    from fastapi import HTTPException
    barrier = threading.Barrier(8)
    def attempt(_):
        barrier.wait(timeout=10)
        try:
            with mysql.sessions.begin() as s:
                reserve(s, "race", 20, ref_id=None, limit=100)
            return 200
        except HTTPException as exc:
            return exc.status_code
    with ThreadPoolExecutor(8) as pool:
        result=list(pool.map(attempt, range(8)))
    assert result.count(200)==5 and result.count(429)==3


def test_mysql_cross_month_charges_original_account(mysql):
    ident=seed(mysql)[0]
    with mysql.sessions.begin() as s:
        # Simulate a job reserved last month, still open when this month starts.
        s.execute(update(QuotaAccount).values(month="2025-12"))
        s.execute(update(QuotaLedger).values(month="2025-12"))
        job=s.get(Job,ident)
        job.options={**job.options,"_quota":{"month":"2025-12","pages":1}}
        job.status="succeeded"
        s.scalar(select(Page).where(Page.job_id==ident)).status="succeeded"
    with mysql.sessions.begin() as s:
        assert settle_terminal(s,s.get(Job,ident))
    with mysql.sessions() as s:
        a=s.get(QuotaAccount,("owner","2025-12"))
        assert (a.pages_reserved,a.pages_used)==(0,1)
        assert s.get(QuotaAccount,("owner",current_month())) is None


def test_mysql_host_search_returns_literal_context_not_ngram_only_match(mysql):
    from backend.models import File as HostFile
    from backend.core.principal import Principal
    from backend.modules.search.service import search
    from backend.modules.ocr.bridge import set_ready
    ident=seed(mysql)[0]
    with mysql.sessions.begin() as s:
        job=s.get(Job,ident)
        f=s.get(File,job.file_id)
        s.add(HostFile(id=f.id,owner_id=f.owner_id,name=f.name,storage_key=f.storage_key,
                      media_type=f.media_type,sha256=f.sha256,size=f.size,page_count=1))
        s.add(TextIndex(file_id=f.id,job_id=ident,page_no=1,revision=1,
                        content="prefix "*60+"设备 abxcd abcdef ABCxyz"))
    set_ready(True)
    with mysql.sessions() as s:
        _, hits=search(s,Principal("owner"),"设备",limit=20,offset=0)
        assert len(hits)==1 and "设备" in hits[0]["snippet"]
        assert search(s,Principal("owner"),"abcd",limit=20,offset=0)[1]
        assert search(s,Principal("owner"),"abcxyz",limit=20,offset=0)[1]==[]
        assert search(s,Principal("owner"),"12",limit=20,offset=0)[1]==[]
