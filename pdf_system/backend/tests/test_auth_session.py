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


def test_disable_requires_admin(env):
    from backend.models import User
    from backend.core.security import hash_password

    settings, app, client = env
    with app.state.sessions() as s:
        u1 = User(email="dis1@example.com", password_hash=hash_password("secret12345"), role="user")
        u2 = User(email="dis2@example.com", password_hash=hash_password("secret12345"), role="user")
        s.add_all([u1, u2])
        s.commit()
        s.refresh(u1)
        s.refresh(u2)
        u1id, u2id = u1.id, u2.id
    t1 = client.post("/api/v1/auth/login",
                     json={"email": "dis1@example.com", "password": "secret12345"}).json()["access_token"]
    # 普通用户不能禁用他人
    resp = client.patch(f"/api/v1/auth/users/{u2id}/disabled", json={"disabled": True},
                        headers={"Authorization": f"Bearer {t1}"})
    assert resp.status_code == 403


def test_admin_disable_invalidates_tokens(env):
    from backend.models import User
    from backend.core.security import hash_password

    settings, app, client = env
    with app.state.sessions() as s:
        admin = User(email="dadm@example.com", password_hash=hash_password("secret12345"), role="admin")
        victim = User(email="dvictim@example.com", password_hash=hash_password("secret12345"), role="user")
        s.add_all([admin, victim])
        s.commit()
        s.refresh(admin)
        s.refresh(victim)
        aid, vid = admin.id, victim.id
    atoken = client.post("/api/v1/auth/login",
                         json={"email": "dadm@example.com", "password": "secret12345"}).json()["access_token"]
    aauth = {"Authorization": f"Bearer {atoken}"}
    # 受害者先拿到令牌
    vtoken = client.post("/api/v1/auth/login",
                         json={"email": "dvictim@example.com", "password": "secret12345"}).json()["access_token"]
    # 管理员禁用
    resp = client.patch(f"/api/v1/auth/users/{vid}/disabled", json={"disabled": True}, headers=aauth)
    assert resp.status_code == 200, resp.text
    assert resp.json()["disabled"] is True
    # 受害者现有令牌立即失效
    assert client.get("/api/v1/auth/me",
                      headers={"Authorization": f"Bearer {vtoken}"}).status_code == 401
    # 管理员不能禁用自己
    resp_self = client.patch(f"/api/v1/auth/users/{aid}/disabled", json={"disabled": True}, headers=aauth)
    assert resp_self.status_code == 400
    # 解禁后受害者可重新登录
    client.patch(f"/api/v1/auth/users/{vid}/disabled", json={"disabled": False}, headers=aauth)
    assert client.post("/api/v1/auth/login",
                      json={"email": "dvictim@example.com", "password": "secret12345"}).status_code == 200
