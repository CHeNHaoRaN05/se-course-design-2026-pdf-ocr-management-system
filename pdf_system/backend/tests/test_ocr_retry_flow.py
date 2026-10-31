"""Failed-page UI retry uses a new job ID, preserving the frozen C3 contract."""
from sqlalchemy import select

from .conftest import auth, pdf_bytes, register


def test_failed_page_new_job_retry_has_independent_quota(env):
    _, app, client = env
    assert app.state.ocr_mounted
    from ocr_service.db import TextIndex
    from ocr_service.queue import claim, save_page, complete_attempt
    token = register(client)
    client.headers.update(auth(token))
    file = client.post("/api/v1/files", files={"file": ("two.pdf", pdf_bytes(2), "application/pdf")}).json()
    original = client.post("/api/v1/ocr/jobs", json={"file_id": file["id"]}).json()["id"]
    cfg = app.state.ocr_settings
    cfg.max_attempts = 1
    lease = claim(app.state.ocr_sessions, cfg)
    assert lease[0] == original
    assert save_page(app.state.ocr_sessions, *lease, 1, result={"text": "第一页已识别"})
    assert save_page(app.state.ocr_sessions, *lease, 2, error="ocr_inference_failed")
    complete_attempt(app.state.ocr_sessions, cfg, *lease)
    assert client.post(f"/api/v1/ocr-host/jobs/{original}/settle").status_code == 200
    assert client.get("/api/v1/quota").json()["pages_reserved"] == 0
    assert client.get("/api/v1/quota").json()["pages_used"] == 1

    response = client.post("/api/v1/ocr/jobs", json={"file_id": file["id"], "pages": [2]})
    assert response.status_code == 202
    retry = response.json()["id"]
    assert retry != original
    assert client.get("/api/v1/quota").json()["pages_reserved"] == 1
    lease = claim(app.state.ocr_sessions, cfg)
    assert save_page(app.state.ocr_sessions, *lease, 2, result={"text": "第二页重试成功"})
    complete_attempt(app.state.ocr_sessions, cfg, *lease)
    assert client.post(f"/api/v1/ocr-host/jobs/{retry}/settle").json()["settled"]
    assert not client.post(f"/api/v1/ocr-host/jobs/{retry}/settle").json()["settled"]
    usage = client.get("/api/v1/quota").json()
    assert usage["pages_reserved"] == 0 and usage["pages_used"] == 2
    with app.state.sessions() as session:
        index = {row.page_no: row.job_id for row in session.scalars(select(TextIndex))}
    assert index == {1: original, 2: retry}
