"""分享与协作接口测试（甲，FR-SHR-01/02/03 + FR-USER-06 权限闸门）。

依赖 conftest.make_env：独立 SQLite + 真实 app（OCR 未挂载时自动跳过）。
不依赖 Paddle 环境。
"""
from .conftest import auth, png_bytes, register


def _upload(client, token: str) -> str:
    resp = client.post("/api/v1/files", headers=auth(token),
                       files={"file": ("n.png", png_bytes(), "image/png")})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_create_and_list_share(client):
    token = register(client)
    file_id = _upload(client, token)
    created = client.post("/api/v1/share", headers=auth(token),
                          json={"file_id": file_id, "allow_download": True})
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["token"] and body["share_url"].endswith(body["token"])
    listing = client.get("/api/v1/share", headers=auth(token))
    assert listing.status_code == 200 and len(listing.json()) == 1


def test_share_requires_ownership(client):
    owner = register(client, "owner@example.com")
    other = register(client, "other@example.com")
    file_id = _upload(client, owner)
    resp = client.post("/api/v1/share", headers=auth(other), json={"file_id": file_id})
    assert resp.status_code == 404  # 越权统一 404


def test_public_token_access_and_stats(client):
    token = register(client)
    file_id = _upload(client, token)
    created = client.post("/api/v1/share", headers=auth(token),
                          json={"file_id": file_id, "allow_download": True})
    share_token = created.json()["token"]
    # 被分享者凭 token 访问，无需 JWT
    got = client.get(f"/api/v1/share/token/{share_token}")
    assert got.status_code == 200
    # 访问统计递增
    stats = client.get(f"/api/v1/share/{created.json()['id']}/stats", headers=auth(token))
    assert stats.json()["visit_count"] == 1


def test_access_code_enforced(client):
    token = register(client)
    file_id = _upload(client, token)
    created = client.post("/api/v1/share", headers=auth(token),
                          json={"file_id": file_id, "access_code": "1234", "allow_download": False})
    share_token = created.json()["token"]
    assert client.get(f"/api/v1/share/token/{share_token}").status_code == 404       # 缺码
    assert client.get(f"/api/v1/share/token/{share_token}?code=0000").status_code == 404  # 错码
    meta = client.get(f"/api/v1/share/token/{share_token}?code=1234")
    assert meta.status_code == 200 and meta.json()["id"] == file_id                # 正确码仅元数据


def test_cancel_share(client):
    token = register(client)
    file_id = _upload(client, token)
    created = client.post("/api/v1/share", headers=auth(token), json={"file_id": file_id})
    sid = created.json()["id"]
    assert client.delete(f"/api/v1/share/{sid}", headers=auth(token)).status_code == 204
    assert client.get(f"/api/v1/share/token/{created.json()['token']}").status_code == 404


def test_change_role_requires_admin(client):
    token = register(client, "plain@example.com")
    me = client.get("/api/v1/auth/me", headers=auth(token)).json()
    resp = client.patch(f"/api/v1/auth/users/{me['id']}/role",
                        headers=auth(token), json={"role": "admin"})
    assert resp.status_code == 403  # 普通用户无权改角色
