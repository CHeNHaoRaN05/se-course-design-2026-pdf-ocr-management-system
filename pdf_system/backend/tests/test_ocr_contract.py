"""跨线契约测试（C1/C2/C3/C5，丙）。

仅在 OCR 模块成功挂载时运行（需要 cv2 等推理侧依赖；Paddle 权重本身不需要，
因为 install() 只建数据库连接，推理引擎是懒加载的）。
"""
import pytest
from sqlalchemy import func, select

from .conftest import auth, make_env, png_bytes, register

import cv2  # required CI dependency; missing dependency must fail collection


@pytest.fixture
def ocr_env(tmp_path):
    """配额压到 1 页，便于直接触发 429。"""
    settings, app, client = make_env(tmp_path, monthly_page_quota=1)
    assert app.state.ocr_mounted, f"OCR 模块未挂载：{settings.ocr_package_dir}"
    return settings, app, client


def _upload(client, token, name):
    response = client.post("/api/v1/files", headers=auth(token),
                           files={"file": (name, png_bytes(), "image/png")})
    assert response.status_code == 201, response.text
    return response.json()


def test_c2_upload_writes_ocr_mirror(ocr_env):
    """C2：上传即写 ocr_files 镜像，且 id/storage_key 与主文件一致。"""
    _, app, client = ocr_env
    token = register(client)
    file = _upload(client, token, "one.png")

    from ocr_service.db import File as OcrFile
    with app.state.sessions() as session:
        mirror = session.get(OcrFile, file["id"])
    assert mirror is not None
    assert mirror.storage_key and mirror.page_count == 1
    assert mirror.owner_id  # 归属随主文件


def test_c1_main_token_calls_ocr_api(ocr_env):
    """C1：主系统签发的令牌必须能直接调 OCR 原生接口（dependency_overrides 生效）。"""
    _, app, client = ocr_env
    token = register(client)
    file = _upload(client, token, "one.png")

    response = client.post("/api/v1/ocr/jobs", headers=auth(token), json={"file_id": file["id"]})
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "queued"


def test_c3_quota_reserved_on_enqueue_then_429(ocr_env):
    """C3：入队预留配额；超额必须 429。"""
    _, app, client = ocr_env
    token = register(client)
    first = _upload(client, token, "one.png")
    second = _upload(client, token, "two.png")

    assert client.post("/api/v1/ocr/jobs", headers=auth(token),
                       json={"file_id": first["id"]}).status_code == 202
    assert client.get("/api/v1/quota", headers=auth(token)).json()["pages_reserved"] == 1

    over = client.post("/api/v1/ocr/jobs", headers=auth(token), json={"file_id": second["id"]})
    assert over.status_code == 429, over.text


def test_c5_soft_delete_cancels_job(ocr_env):
    """C5：软删除要取消未终态任务。"""
    _, app, client = ocr_env
    token = register(client)
    file = _upload(client, token, "one.png")
    job_id = client.post("/api/v1/ocr/jobs", headers=auth(token),
                         json={"file_id": file["id"]}).json()["id"]

    assert client.delete(f"/api/v1/files/{file['id']}", headers=auth(token)).status_code == 200

    from ocr_service.db import Job
    with app.state.sessions() as session:
        assert session.get(Job, job_id).status == "cancelled"


def test_c5_purge_clears_ocr_side(ocr_env):
    """C5：彻底删除要清掉 ocr_jobs / ocr_files / pdf_text_index。"""
    _, app, client = ocr_env
    token = register(client)
    file = _upload(client, token, "one.png")
    client.post("/api/v1/ocr/jobs", headers=auth(token), json={"file_id": file["id"]})

    assert client.delete(f"/api/v1/files/{file['id']}/purge", headers=auth(token)).status_code == 204

    from ocr_service.db import File as OcrFile, Job, TextIndex
    with app.state.sessions() as session:
        assert session.scalar(select(func.count(Job.id)).where(Job.file_id == file["id"])) == 0
        assert session.get(OcrFile, file["id"]) is None
        assert session.scalar(select(func.count(TextIndex.id))
                              .where(TextIndex.file_id == file["id"])) == 0


def test_c5_purge_tolerates_job_without_quota_reservation(ocr_env):
    """升级路径回归：options 里没有 _quota 的历史任务，彻底删除不得 500。

    现场表现是 DELETE /files/{id}/purge 返回 500（ValueError: Quota reservation
    missing），删不掉文件。对账由 reconcile_terminal 负责，删除本身必须幂等完成。
    """
    _, app, client = ocr_env
    token = register(client)
    file = _upload(client, token, "legacy.png")

    from ocr_service.db import File as OcrFile, Job
    import uuid
    with app.state.sessions.begin() as session:
        mirror = session.get(OcrFile, file["id"])
        session.add(Job(id=uuid.uuid4().hex, file_id=file["id"], generation=0,
                        owner_id=mirror.owner_id, status="succeeded",
                        options={"pages": [1]}, attempts=1))

    assert client.delete(f"/api/v1/files/{file['id']}", headers=auth(token)).status_code == 200
    assert client.post(f"/api/v1/files/{file['id']}/restore", headers=auth(token)).status_code == 200
    assert client.delete(f"/api/v1/files/{file['id']}", headers=auth(token)).status_code == 200
    assert client.delete(f"/api/v1/files/{file['id']}/purge", headers=auth(token)).status_code == 204
