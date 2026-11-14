"""Regression evidence for the November line-03 review (real transactions)."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import os
import threading

import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy import select, func

from .conftest import auth, make_env, png_bytes, register
from backend.models import QuotaAccount, QuotaLedger, User, current_month
from backend.modules.quota import service as quota


def enqueue(app, client, pages=1):
    token = register(client)
    client.headers.update(auth(token))
    from .conftest import pdf_bytes
    f = client.post("/api/v1/files", files={"file": ("review.pdf", pdf_bytes(pages), "application/pdf")}).json()
    r = client.post("/api/v1/ocr/jobs", json={"file_id": f["id"]})
    assert r.status_code == 202, r.text
    return f["id"], r.json()["id"]


def test_cancel_and_purge_refund_without_frontend(env):
    _, app, client = env
    file_id, job_id = enqueue(app, client)
    assert client.post(f"/api/v1/ocr/jobs/{job_id}/cancel").status_code == 200
    assert client.get("/api/v1/quota").json()["pages_reserved"] == 0
    another = client.post("/api/v1/ocr/jobs", json={"file_id": file_id}).json()["id"]
    assert client.delete(f"/api/v1/files/{file_id}/purge").status_code == 204
    assert client.get("/api/v1/quota").json()["pages_reserved"] == 0
    with app.state.sessions() as s:
        assert s.scalar(select(func.count()).select_from(QuotaLedger).where(QuotaLedger.ref_id == another,
                       QuotaLedger.reason == "job_close")) == 1


def test_server_settles_and_retry_returns_new_id(env):
    _, app, client = env
    _, ident = enqueue(app, client, 2)
    from ocr_service.queue import claim, save_page, complete_attempt
    app.state.ocr_settings.max_attempts = 1
    lease = claim(app.state.ocr_sessions, app.state.ocr_settings)
    save_page(app.state.ocr_sessions, *lease, 1, result={"text": "done"})
    save_page(app.state.ocr_sessions, *lease, 2, error="failed")
    complete_attempt(app.state.ocr_sessions, app.state.ocr_settings, *lease)
    usage = client.get("/api/v1/quota").json()
    assert (usage["pages_reserved"], usage["pages_used"]) == (0, 1)
    retry = client.post(f"/api/v1/ocr/jobs/{ident}/retry")
    assert retry.status_code == 202, retry.text
    assert retry.json()["id"] != ident and retry.json()["options"]["pages"] == [2]
    usage = client.get("/api/v1/quota").json()
    assert (usage["pages_reserved"], usage["pages_used"]) == (1, 1)


def test_cross_month_terminal_and_concurrent_close(env, monkeypatch):
    _, app, client = env
    monkeypatch.setattr(quota, "current_month", lambda: "2026-01")
    _, ident = enqueue(app, client, 2)
    from ocr_service.db import Job, Page
    from ocr_service.accounting import settle_terminal
    with app.state.ocr_sessions.begin() as s:
        job = s.get(Job, ident)
        job.status = "partial_success"
        s.scalar(select(Page).where(Page.job_id == ident, Page.page_no == 1)).status = "succeeded"
    monkeypatch.setattr(quota, "current_month", lambda: "2026-02")
    barrier = threading.Barrier(10)
    def finish(_):
        barrier.wait(timeout=10)
        with app.state.ocr_sessions.begin() as s:
            return settle_terminal(s, s.get(Job, ident))
    with ThreadPoolExecutor(max_workers=10) as pool:
        assert sum(pool.map(finish, range(10))) == 1
    with app.state.sessions() as s:
        a = s.scalar(select(QuotaAccount).where(QuotaAccount.month == "2026-01"))
        assert (a.pages_reserved, a.pages_used) == (0, 1)
        assert s.scalar(select(func.count()).select_from(QuotaLedger).where(QuotaLedger.reason == "job_close")) == 1
        assert s.scalar(select(QuotaAccount).where(QuotaAccount.month == "2026-02")) is None


def test_first_account_concurrent_reservations(env):
    _, app, _ = env
    barrier = threading.Barrier(8)
    def reserve(_):
        barrier.wait(timeout=10)
        try:
            with app.state.sessions.begin() as s:
                quota.reserve(s, "concurrent", 20, ref_id=None, limit=100)
            return 200
        except HTTPException as e:
            return e.status_code
    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(reserve, range(8)))
    assert codes.count(200) == 5 and codes.count(429) == 3


@pytest.mark.parametrize("method", [quota.reserve, quota.release, quota.settle])
def test_quota_rejects_negative_and_zero_has_no_ledger(env, method):
    _, app, _ = env
    kwargs = {"ref_id": None, **({"limit": 100} if method is quota.reserve else {})}
    with app.state.sessions.begin() as s:
        with pytest.raises(ValueError):
            method(s, "boundary", -5, **kwargs)
        method(s, "boundary", 0, **kwargs)
        assert s.scalar(select(func.count()).select_from(QuotaLedger)) == 0


def test_release_ledger_matches_actual_movement(env):
    _, app, _ = env
    with app.state.sessions.begin() as s:
        quota.reserve(s, "ledger", 1, ref_id="r", limit=100)
        quota.release(s, "ledger", 5, ref_id="r")
        s.flush()
        assert s.scalar(select(QuotaLedger.pages).where(QuotaLedger.reason == "release")) == -1
        assert s.get(QuotaAccount, ("ledger", current_month())).pages_reserved == 0


def test_trash_not_searchable_through_either_route(env):
    _, app, client = env
    file_id, ident = enqueue(app, client)
    from ocr_service.db import TextIndex
    with app.state.sessions.begin() as s:
        s.add(TextIndex(file_id=file_id, job_id=ident, page_no=1, revision=1, content="private marker"))
    assert len(client.get("/api/v1/ocr/search?q=marker").json()["items"]) == 1
    assert client.delete(f"/api/v1/files/{file_id}").status_code == 200
    for route in ("/api/v1/search", "/api/v1/ocr/search"):
        assert client.get(route, params={"q": "marker"}).json()["items"] == []
    assert client.get(f"/api/v1/ocr/files/{file_id}/content").status_code == 404


def test_missing_version_and_jti_rejected(env):
    settings, _, client = env
    token = register(client)
    claims = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], audience=settings.jwt_audience)
    for key in ("jti", "tv"):
        altered = {k:v for k,v in claims.items() if k != key}
        invalid = jwt.encode(altered, settings.jwt_secret, algorithm="HS256")
        assert client.get("/api/v1/auth/me", headers=auth(invalid)).status_code == 401


def test_expiry_and_explicit_mount_config(tmp_path, monkeypatch):
    with pytest.raises(RuntimeError, match="JWT_EXPIRE"):
        make_env(tmp_path / "bad", jwt_expire_minutes=0)
    monkeypatch.setenv("OCR_MAX_PAGES", "3")
    before = dict(os.environ)
    _, app, _ = make_env(tmp_path / "ok", max_pages=50, jwt_issuer="review-host", jwt_audience="review-api")
    assert app.state.ocr_mounted
    assert app.state.ocr_settings.max_pages == 50
    assert app.state.ocr_settings.jwt_issuer == "review-host"
    assert app.state.ocr_settings.jwt_audience == "review-api"
    assert dict(os.environ) == before


def test_mount_failure_rolls_back_routes_and_environment(tmp_path, monkeypatch):
    import ocr_service.api as api
    original = api.install
    def broken(app, *a, **k):
        original(app, *a, **k)
        raise ValueError("simulate install failure")
    monkeypatch.setattr(api, "install", broken)
    before = dict(os.environ)
    _, app, client = make_env(tmp_path)
    assert client.get("/health").json()["ocr_mounted"] is False
    assert not any(r.path.startswith("/api/v1/ocr/") for r in app.routes)
    assert dict(os.environ) == before


def test_search_rejects_blank_unknown_and_large_offset(env):
    _, _, client = env
    client.headers.update(auth(register(client)))
    for path in ("/api/v1/search/suggest?q=%20", "/api/v1/search?q=x&offset=10001",
                 "/api/v1/ocr/search?q=x&offset=10001", "/api/v1/search?q=x&mode=phrase"):
        assert client.get(path).status_code == 422


def test_cross_line_read_endpoints_enforce_permissions(env):
    _, app, client = env
    file_id, _ = enqueue(app, client)
    assert client.delete(f"/api/v1/files/{file_id}").status_code == 200
    assert [f["id"] for f in client.get("/api/v1/files/trash").json()] == [file_id]
    for route in ("/api/v1/auth/users", "/api/v1/audit"):
        assert client.get(route).status_code == 403
    other = register(client, "other@example.com")
    assert client.get("/api/v1/files/trash", headers=auth(other)).json() == []
    with app.state.sessions.begin() as s:
        s.scalar(select(User).where(User.email == "alice@example.com")).role = "admin"
    users = client.get("/api/v1/auth/users")
    assert users.status_code == 200 and len(users.json()) == 2
    assert all("password_hash" not in u for u in users.json())
    assert client.get("/api/v1/audit").status_code == 200


def test_reconciliation_does_not_need_browser(env):
    _, app, client = env
    _, ident = enqueue(app, client)
    from ocr_service.db import Job
    from backend.modules.ocr.mount import reconcile_terminal
    with app.state.ocr_sessions.begin() as s:
        s.get(Job, ident).status = "cancelled"
    reconcile_terminal(app.state.ocr_sessions)
    assert client.get("/api/v1/quota").json()["pages_reserved"] == 0
    reconcile_terminal(app.state.ocr_sessions)
    with app.state.sessions() as s:
        assert s.scalar(select(func.count()).select_from(QuotaLedger).where(QuotaLedger.reason == "job_close")) == 1


def test_purge_rolls_back_database_and_physical_file(env):
    _, app, client = env
    file_id, ident = enqueue(app, client)
    from backend.models import File
    from backend.modules.files.service import purge
    from backend.core.principal import Principal
    from ocr_service.db import Job
    with app.state.sessions() as s:
        record=s.get(File,file_id)
        path=app.state.settings.storage_dir/record.storage_key
        owner=record.owner_id
    with app.state.sessions() as s:
        purge(s,app.state.settings,file_id,Principal(owner))
        assert path.exists()
        s.rollback()
    with app.state.sessions() as s:
        assert s.get(File,file_id) is not None
        assert s.get(Job,ident).status=="queued"
    assert path.exists()


def test_admin_enqueue_charges_file_owner(env):
    _, app, client = env
    file_id, ident = enqueue(app,client)
    assert client.post(f"/api/v1/ocr/jobs/{ident}/cancel").status_code==200
    admin_token=register(client,"admin@example.com")
    with app.state.sessions.begin() as s:
        admin=s.scalar(select(User).where(User.email=="admin@example.com"))
        admin.role="admin"
        admin_id=admin.id
    response=client.post("/api/v1/ocr/jobs",json={"file_id":file_id},headers=auth(admin_token))
    assert response.status_code==202
    with app.state.sessions() as s:
        assert s.get(QuotaAccount,(admin_id,current_month())) is None
    assert client.get("/api/v1/quota").json()["pages_reserved"]==1
