"""会话端点测试（甲，FR-USER-03/04/05）。

覆盖：单点登出吊销、刷新轮换、改密码使旧令牌整体失效。
依赖 conftest.make_env（独立 SQLite + 真实 app）。
"""
from .conftest import auth, register


def test_logout_revokes_current_token(client):
    token = register(client, "lo@example.com")
    assert client.post("/api/v1/auth/logout", headers=auth(token)).status_code == 204
    # 旧令牌立即失效
    assert client.get("/api/v1/auth/me", headers=auth(token)).status_code == 401


def test_refresh_rotates_and_revokes_old(client):
    token = register(client, "rf@example.com")
    resp = client.post("/api/v1/auth/refresh", headers=auth(token))
    assert resp.status_code == 200, resp.text
    new_token = resp.json()["access_token"]
    assert client.get("/api/v1/auth/me", headers=auth(new_token)).status_code == 200
    # 旧 jti 被回收
    assert client.get("/api/v1/auth/me", headers=auth(token)).status_code == 401


def test_change_password_invalid_old(client):
    token = register(client, "cp@example.com")
    resp = client.post("/api/v1/auth/change-password", headers=auth(token),
                       json={"old_password": "wrong", "new_password": "newsecret12345"})
    assert resp.status_code == 400


def test_change_password_invalidates_old_and_login(client):
    token = register(client, "cp2@example.com")
    resp = client.post("/api/v1/auth/change-password", headers=auth(token),
                       json={"old_password": "secret12345", "new_password": "newsecret12345"})
    assert resp.status_code == 200, resp.text
    new_token = resp.json()["access_token"]
    # 新令牌可用，旧令牌失效
    assert client.get("/api/v1/auth/me", headers=auth(new_token)).status_code == 200
    assert client.get("/api/v1/auth/me", headers=auth(token)).status_code == 401
    # 用新密码能登录
    login = client.post("/api/v1/auth/login",
                        json={"email": "cp2@example.com", "password": "newsecret12345"})
    assert login.status_code == 200
    assert client.post("/api/v1/auth/login",
                       json={"email": "cp2@example.com", "password": "secret12345"}).status_code == 400
