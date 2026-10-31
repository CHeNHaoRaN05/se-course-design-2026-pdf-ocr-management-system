"""Search filters must never expand the caller's visible file set."""
from datetime import datetime

import pytest
from sqlalchemy import select

from .conftest import auth, png_bytes, register


@pytest.fixture
def indexed(env):
    _, app, client = env
    assert app.state.ocr_mounted, "Search integration tests require OCR dependencies"
    from backend.models import File, Tag, User
    from ocr_service.db import Job, TextIndex
    alice = register(client)
    bob = register(client, "bob@example.com")
    ids = []
    for index, token in enumerate([alice, alice, alice, bob]):
        response = client.post("/api/v1/files", headers=auth(token),
                               files={"file": (f"report{index}.png", png_bytes(), "image/png")})
        assert response.status_code == 201
        ids.append(response.json()["id"])
    with app.state.sessions.begin() as session:
        for index, file_id in enumerate(ids):
            file = session.get(File, file_id)
            file.created_at = datetime(2026, 10, 30 + index % 2, 0, 0)
            file.tags = [Tag(owner_id=file.owner_id, name="实验"), Tag(owner_id=file.owner_id, name="归档")]
            if index == 2:
                file.deleted_at = datetime(2026, 10, 31)
            job = Job(file_id=file_id, owner_id=file.owner_id, generation=1,
                      options={}, status="succeeded")
            session.add(job)
            session.flush()
            session.add(TextIndex(file_id=file_id, page_no=1, job_id=job.id, revision=2,
                                  content="显微镜登记 100%_\\ <script>alert(1)</script>"))
    return app, client, alice, bob, ids


def hits(client, token, **params):
    response = client.get("/api/v1/search", headers=auth(token), params={"q": "显微镜", **params})
    assert response.status_code == 200, response.text
    return response.json()["items"]


def test_combined_filters_and_inclusive_dates(indexed):
    _, client, alice, _, ids = indexed
    assert {h["file_id"] for h in hits(client, alice)} == set(ids[:2])
    result = hits(client, alice, file_id=ids[0], tag="实验", date_from="2026-10-30", date_to="2026-10-30")
    assert len(result) == 1 and result[0]["revision"] == 2
    assert hits(client, alice, file_id=ids[0], date_from="2026-10-31") == []
    assert hits(client, alice, tag="不存在") == []
    assert len(hits(client, alice, tag="归档")) == 2  # EXISTS must not duplicate pages
    assert len(hits(client, alice, q="100%_\\")) == 2  # literal LIKE metacharacters


def test_foreign_deleted_and_missing_files_are_not_searchable(indexed):
    _, client, alice, bob, ids = indexed
    for file_id in [ids[2], ids[3], "0" * 32]:
        assert hits(client, alice, file_id=file_id, tag="实验") == []
    assert [h["file_id"] for h in hits(client, bob)] == [ids[3]]
    response = client.get("/api/v1/search/suggest?q=report", headers=auth(alice))
    assert {f["file_id"] for f in response.json()["items"]} == set(ids[:2])


def test_admin_filters_and_stable_pagination(indexed):
    app, client, alice, _, ids = indexed
    from backend.models import User
    with app.state.sessions.begin() as session:
        session.scalar(select(User).where(User.email == "alice@example.com")).role = "admin"
    result = hits(client, alice, file_id=ids[3])
    assert len(result) == 1
    assert hits(client, alice, file_id=ids[2]) == []
    all_hits = hits(client, alice)
    assert hits(client, alice, limit=1, offset=1) == all_hits[1:2]


@pytest.mark.parametrize("params", [
    {"q": " "}, {"q": "x" * 101}, {"tag": " "}, {"file_id": "' OR 1=1"},
    {"date_from": "2026-11-01", "date_to": "2026-10-01"},
    {"date_from": "invalid"}, {"date_to": "9999-12-31"}, {"offset": -1},
])
def test_invalid_filters(indexed, params):
    _, client, alice, _, _ = indexed
    assert client.get("/api/v1/search", headers=auth(alice), params={"q": "镜", **params}).status_code == 422


def test_sql_parameters_are_data(indexed):
    _, client, alice, _, _ = indexed
    assert hits(client, alice, tag="' OR 1=1 --") == []
    assert hits(client, alice, q="' OR 1=1 --") == []


def test_ocr_disabled_returns_empty(tmp_path):
    from .conftest import make_env
    _, _, client = make_env(tmp_path, ocr_enabled=False)
    token = register(client)
    assert client.get("/api/v1/search?q=测试", headers=auth(token)).json() == {
        "backend": "ocr_not_ready", "items": []}
