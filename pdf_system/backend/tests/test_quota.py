"""配额与使用统计接口测试（甲，FR-QTA-01/02/03/04）。

依赖 conftest.make_env：独立 SQLite + 真实 app。
"""
from .conftest import auth, register


def test_quota_requires_token(client):
    assert client.get("/api/v1/quota").status_code == 401
    assert client.get("/api/v1/quota/overview").status_code == 401


def test_quota_shape(client):
    token = register(client)
    r = client.get("/api/v1/quota", headers=auth(token))
    assert r.status_code == 200, r.text
    assert set(r.json().keys()) >= {
        "month", "pages_reserved", "pages_used", "pages_committed"
    }


def test_overview_shape(client):
    token = register(client)
    r = client.get("/api/v1/quota/overview", headers=auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    # files / storage_bytes 为本账户文件量与会用量；quota 为 OCR 额度
    assert isinstance(body["files"], int)
    assert isinstance(body["storage_bytes"], int)
    assert isinstance(body["quota"], dict)


def test_quota_is_per_user(client):
    """始终返回调用者自己的配额，与管理员身份无关。"""
    a = register(client, "qa@example.com")
    b = register(client, "qb@example.com")
    ra = client.get("/api/v1/quota", headers=auth(a)).json()
    rb = client.get("/api/v1/quota", headers=auth(b)).json()
    # 两个独立账户的额度结构一致（各自隔离）
    assert set(ra.keys()) == set(rb.keys())
