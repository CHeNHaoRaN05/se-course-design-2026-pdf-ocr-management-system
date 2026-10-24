"""分享与协作接口详尽测试（甲，FR-SHR-01/02/03 + 异常分支）。

依赖 conftest.make_env：独立 SQLite + 真实 app（OCR 未挂载时自动跳过），不依赖 Paddle。
owner 侧需 JWT；被分享者侧凭 token 旁路访问（无需 JWT），错误/过期/错码统一 404。
"""
from datetime import datetime, timedelta

from .conftest import auth, png_bytes, register


def _upload(client, token: str) -> str:
    resp = client.post("/api/v1/files", headers=auth(token),
                       files={"file": ("n.png", png_bytes(), "image/png")})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _share(client, token, file_id, **kw):
    return client.post("/api/v1/share", headers=auth(token),
                      json={"file_id": file_id, **kw})


# ---------------- 创建 / 列表 ----------------
def test_create_and_list(client):
    token = register(client)
    fid = _upload(client, token)
    created = _share(client, token, fid, allow_download=True)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["token"] and body["share_url"].endswith(body["token"])
    assert body["visit_count"] == 0
    listing = client.get("/api/v1/share", headers=auth(token))
    assert listing.status_code == 200 and len(listing.json()) == 1


def test_create_requires_ownership(client):
    owner = register(client, "owner@example.com")
    other = register(client, "other@example.com")
    fid = _upload(client, owner)
    assert _share(client, other, fid).status_code == 404  # 越权统一 404


def test_create_invalid_file_id(client):
    token = register(client)
    assert _share(client, token, "no-such-file").status_code == 404


def test_create_expired_at_past(client):
    token = register(client)
    fid = _upload(client, token)
    past = (datetime.now() - timedelta(days=1)).isoformat()
    r = _share(client, token, fid, expires_at=past)
    assert r.status_code == 422  # bad_request：expires_at_must_be_future


# ---------------- 详情 / 取消 / 权限 ----------------
def test_detail_and_ownership(client):
    token = register(client)
    fid = _upload(client, token)
    sid = _share(client, token, fid).json()["id"]
    assert client.get(f"/api/v1/share/{sid}", headers=auth(token)).status_code == 200
    other = register(client, "o2@example.com")
    assert client.get(f"/api/v1/share/{sid}", headers=auth(other)).status_code == 404
    assert client.get("/api/v1/share/ghost", headers=auth(token)).status_code == 404


def test_cancel_and_double_cancel(client):
    token = register(client)
    fid = _upload(client, token)
    sid = _share(client, token, fid).json()["id"]
    assert client.delete(f"/api/v1/share/{sid}", headers=auth(token)).status_code == 204
    assert client.delete(f"/api/v1/share/{sid}", headers=auth(token)).status_code == 404  # 已删
    other = register(client, "o3@example.com")
    assert client.delete(f"/api/v1/share/{sid}", headers=auth(other)).status_code == 404  # 非 owner


# ---------------- 被分享者旁路访问 ----------------
def test_public_access_download(client):
    token = register(client)
    fid = _upload(client, token)
    stoken = _share(client, token, fid, allow_download=True).json()["token"]
    assert client.get(f"/api/v1/share/token/{stoken}").status_code == 200


def test_public_access_metadata_only(client):
    token = register(client)
    fid = _upload(client, token)
    stoken = _share(client, token, fid, allow_download=False).json()["token"]
    meta = client.get(f"/api/v1/share/token/{stoken}")
    assert meta.status_code == 200
    assert meta.json()["id"] == fid and "size" in meta.json()


def test_access_code_enforced(client):
    token = register(client)
    fid = _upload(client, token)
    stoken = _share(client, token, fid, access_code="1234", allow_download=False).json()["token"]
    assert client.get(f"/api/v1/share/token/{stoken}").status_code == 404            # 缺码
    assert client.get(f"/api/v1/share/token/{stoken}?code=0000").status_code == 404  # 错码
    ok = client.get(f"/api/v1/share/token/{stoken}?code=1234")
    assert ok.status_code == 200 and ok.json()["id"] == fid                         # 对码仅元数据


def test_token_unknown(client):
    assert client.get("/api/v1/share/token/does-not-exist").status_code == 404


def test_token_expired(client, env):
    from backend.models import ShareLink
    _, app, _ = env
    token = register(client)
    fid = _upload(client, token)
    with app.state.sessions() as s:
        link = ShareLink(file_id=fid, owner_id="x", token="expiredtok",
                        expires_at=datetime.now() - timedelta(days=1), allow_download=False)
        s.add(link)
        s.commit()
    assert client.get("/api/v1/share/token/expiredtok").status_code == 404


def test_token_after_file_deleted(client, env):
    from backend.models import File
    _, app, _ = env
    token = register(client)
    fid = _upload(client, token)
    stoken = _share(client, token, fid, allow_download=True).json()["token"]
    with app.state.sessions() as s:
        s.delete(s.get(File, fid))
        s.commit()
    # 被分享文件已删 -> 统一 404
    assert client.get(f"/api/v1/share/token/{stoken}").status_code == 404


# ---------------- 访问统计 ----------------
def test_stats_increments_on_access(client):
    token = register(client)
    fid = _upload(client, token)
    created = _share(client, token, fid, allow_download=True)
    sid = created.json()["id"]
    stoken = created.json()["token"]
    assert client.get(f"/api/v1/share/token/{stoken}").status_code == 200
    stats = client.get(f"/api/v1/share/{sid}/stats", headers=auth(token))
    assert stats.status_code == 200 and stats.json()["visit_count"] == 1
    # 越权查看统计 -> 404
    other = register(client, "o4@example.com")
    assert client.get(f"/api/v1/share/{sid}/stats", headers=auth(other)).status_code == 404
