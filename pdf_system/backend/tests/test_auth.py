"""认证与权限接口详尽测试（甲，FR-USER 全系列 + 异常分支）。

依赖 conftest.make_env（独立 SQLite + 真实 app）。
状态码约定（来自 core/errors 与本仓库 FastAPI 配置）：
  - 缺令牌 / 令牌无效或过期 / 被禁用 / 被吊销 / 改密后旧令牌  -> 401
  - bad_request（含原密码错误、自禁防护）                    -> 422
  - pydantic 校验失败（邮箱格式、密码长度、多余字段、枚举）  -> 422
  - 非管理员访问管理员接口                                  -> 403
  - not_found（越权/不存在）                                -> 404
  - conflict（重复邮箱）                                    -> 409
HTTPBearer 使用 auto_error=False，因此"缺 Authorization"走 401 而非 403。
"""
from .conftest import auth, register


def _seed(env, email, role="user", password="secret12345"):
    from backend.models import User
    from backend.core.security import hash_password
    _, app, _ = env
    with app.state.sessions() as s:
        u = User(email=email, display_name=email.split("@")[0],
                 password_hash=hash_password(password), role=role)
        s.add(u)
        s.commit()
        s.refresh(u)
        return u.id


def _login(client, email, password="secret12345"):
    return client.post("/api/v1/auth/login",
                      json={"email": email, "password": password}).json()["access_token"]


# ---------------- 注册 ----------------
def test_register_success(client):
    token = register(client, "reg1@example.com")
    me = client.get("/api/v1/auth/me", headers=auth(token))
    assert me.status_code == 200 and me.json()["email"] == "reg1@example.com"


def test_register_duplicate_email(client):
    register(client, "dup@example.com")
    r = client.post("/api/v1/auth/register",
                    json={"email": "dup@example.com", "password": "secret12345"})
    assert r.status_code == 409


def test_register_invalid_email(client):
    r = client.post("/api/v1/auth/register",
                    json={"email": "not-an-email", "password": "secret12345"})
    assert r.status_code == 422


def test_register_short_password(client):
    r = client.post("/api/v1/auth/register",
                    json={"email": "short@example.com", "password": "123"})
    assert r.status_code == 422


def test_register_extra_field_forbidden(client):
    r = client.post("/api/v1/auth/register",
                    json={"email": "extra@example.com", "password": "secret12345", "foo": 1})
    assert r.status_code == 422


# ---------------- 登录 ----------------
def test_login_success(client):
    register(client, "login1@example.com")
    r = client.post("/api/v1/auth/login",
                    json={"email": "login1@example.com", "password": "secret12345"})
    assert r.status_code == 200 and "access_token" in r.json()


def test_login_wrong_password(client):
    register(client, "login2@example.com")
    r = client.post("/api/v1/auth/login",
                    json={"email": "login2@example.com", "password": "wrongpass1"})
    assert r.status_code == 422


def test_login_nonexistent(client):
    r = client.post("/api/v1/auth/login",
                    json={"email": "nobody@example.com", "password": "secret12345"})
    assert r.status_code == 422


# ---------------- /me ----------------
def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_invalid_token(client):
    assert client.get("/api/v1/auth/me",
                     headers={"Authorization": "Bearer not.a.jwt"}).status_code == 401


def test_me_disabled_user(client, env):
    vid = _seed(env, "disuser@example.com", role="user")
    token = _login(client, "disuser@example.com")
    _seed(env, "adminx@example.com", role="admin")
    atoken = _login(client, "adminx@example.com")
    client.patch(f"/api/v1/auth/users/{vid}/disabled",
                 json={"disabled": True}, headers=auth(atoken))
    assert client.get("/api/v1/auth/me", headers=auth(token)).status_code == 401


# ---------------- 管理员自检 ----------------
def test_admin_check_requires_admin(client):
    token = register(client, "plain@example.com")
    assert client.get("/api/v1/auth/_admin/check", headers=auth(token)).status_code == 403


def test_admin_check_ok(client, env):
    _seed(env, "ac@example.com", role="admin")
    atoken = _login(client, "ac@example.com")
    r = client.get("/api/v1/auth/_admin/check", headers=auth(atoken))
    assert r.status_code == 200 and r.json()["role"] == "admin"


# ---------------- 改角色 ----------------
def test_role_requires_admin(client):
    token = register(client, "r1@example.com")
    me = client.get("/api/v1/auth/me", headers=auth(token)).json()
    r = client.patch(f"/api/v1/auth/users/{me['id']}/role",
                    headers=auth(token), json={"role": "admin"})
    assert r.status_code == 403


def test_role_success(client, env):
    _seed(env, "adminr@example.com", role="admin")
    atoken = _login(client, "adminr@example.com")
    victim = register(client, "victr@example.com")
    vid = client.get("/api/v1/auth/me", headers=auth(victim)).json()["id"]
    r = client.patch(f"/api/v1/auth/users/{vid}/role",
                    headers=auth(atoken), json={"role": "viewer"})
    assert r.status_code == 200 and r.json()["role"] == "viewer"
    # 角色以库内为准：/me 反映新角色
    assert client.get("/api/v1/auth/me", headers=auth(victim)).json()["role"] == "viewer"


def test_role_unknown_user(client, env):
    _seed(env, "admr2@example.com", role="admin")
    atoken = _login(client, "admr2@example.com")
    r = client.patch("/api/v1/auth/users/nonexistent/id/role",
                    headers=auth(atoken), json={"role": "admin"})
    assert r.status_code == 404


def test_role_invalid_enum(client, env):
    _seed(env, "admr3@example.com", role="admin")
    atoken = _login(client, "admr3@example.com")
    victim = register(client, "victr3@example.com")
    vid = client.get("/api/v1/auth/me", headers=auth(victim)).json()["id"]
    r = client.patch(f"/api/v1/auth/users/{vid}/role",
                    headers=auth(atoken), json={"role": "superuser"})
    assert r.status_code == 422


# ---------------- 禁用账号 ----------------
def test_disable_requires_admin(client):
    token = register(client, "d1@example.com")
    me = client.get("/api/v1/auth/me", headers=auth(token)).json()
    r = client.patch(f"/api/v1/auth/users/{me['id']}/disabled",
                    headers=auth(token), json={"disabled": True})
    assert r.status_code == 403


def test_disable_unknown_user(client, env):
    _seed(env, "admd@example.com", role="admin")
    atoken = _login(client, "admd@example.com")
    r = client.patch("/api/v1/auth/users/ghost/id/disabled",
                    headers=auth(atoken), json={"disabled": True})
    assert r.status_code == 404


def test_disable_self(client, env):
    _seed(env, "admself@example.com", role="admin")
    atoken = _login(client, "admself@example.com")
    aid = client.get("/api/v1/auth/me", headers=auth(atoken)).json()["id"]
    r = client.patch(f"/api/v1/auth/users/{aid}/disabled",
                    headers=auth(atoken), json={"disabled": True})
    assert r.status_code == 422  # 禁止管理员禁用自己


def test_disable_and_reenable(client, env):
    _seed(env, "adme@example.com", role="admin")
    atoken = _login(client, "adme@example.com")
    vid = _seed(env, "victimd@example.com", role="user")
    vtoken = _login(client, "victimd@example.com")
    r = client.patch(f"/api/v1/auth/users/{vid}/disabled",
                    headers=auth(atoken), json={"disabled": True})
    assert r.status_code == 200 and r.json()["disabled"] is True
    # 禁用后其所有令牌立即失效
    assert client.get("/api/v1/auth/me", headers=auth(vtoken)).status_code == 401
    # 解禁后可重新登录
    client.patch(f"/api/v1/auth/users/{vid}/disabled",
                 headers=auth(atoken), json={"disabled": False})
    assert _login(client, "victimd@example.com")


# ---------------- 登出 ----------------
def test_logout_requires_token(client):
    assert client.post("/api/v1/auth/logout").status_code == 401


def test_logout_revokes(client):
    token = register(client, "lo@example.com")
    assert client.post("/api/v1/auth/logout", headers=auth(token)).status_code == 204
    assert client.get("/api/v1/auth/me", headers=auth(token)).status_code == 401


def test_logout_invalid_token(client):
    assert client.post("/api/v1/auth/logout",
                      headers={"Authorization": "Bearer bad.token"}).status_code == 401


# ---------------- 刷新 ----------------
def test_refresh_requires_token(client):
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_refresh_rotates(client):
    token = register(client, "rf@example.com")
    r = client.post("/api/v1/auth/refresh", headers=auth(token))
    assert r.status_code == 200, r.text
    new_token = r.json()["access_token"]
    assert client.get("/api/v1/auth/me", headers=auth(new_token)).status_code == 200
    # 旧 jti 被回收
    assert client.get("/api/v1/auth/me", headers=auth(token)).status_code == 401


def test_refresh_invalid_token(client):
    assert client.post("/api/v1/auth/refresh",
                      headers={"Authorization": "Bearer tampered.token"}).status_code == 401


def test_refresh_tampered_signature(client):
    token = register(client, "rft@example.com")
    header, payload, signature = token.split(".")
    # 修改首字符，确保签名字节改变；末字符可能只改变 Base64URL 的填充位。
    tampered_signature = ("A" if signature[0] != "A" else "B") + signature[1:]
    tampered = ".".join((header, payload, tampered_signature))
    assert client.post("/api/v1/auth/refresh",
                      headers={"Authorization": f"Bearer {tampered}"}).status_code == 401


# ---------------- 改密码 ----------------
def test_change_password_requires_token(client):
    assert client.post("/api/v1/auth/change-password",
                      json={"old_password": "x", "new_password": "newsecret12345"}).status_code == 401


def test_change_password_wrong_old(client):
    token = register(client, "cp@example.com")
    r = client.post("/api/v1/auth/change-password", headers=auth(token),
                    json={"old_password": "wrongpass1", "new_password": "newsecret12345"})
    assert r.status_code == 422  # bad_request：原密码不正确


def test_change_password_short_new(client):
    token = register(client, "cps@example.com")
    r = client.post("/api/v1/auth/change-password", headers=auth(token),
                    json={"old_password": "secret12345", "new_password": "short"})
    assert r.status_code == 422  # pydantic：new_password 至少 8 位


def test_change_password_success_invalidates_old(client):
    token = register(client, "cpm@example.com")
    r = client.post("/api/v1/auth/change-password", headers=auth(token),
                    json={"old_password": "secret12345", "new_password": "newsecret12345"})
    assert r.status_code == 200, r.text
    new_token = r.json()["access_token"]
    assert client.get("/api/v1/auth/me", headers=auth(new_token)).status_code == 200
    # 旧令牌整体失效（token_version 不匹配）
    assert client.get("/api/v1/auth/me", headers=auth(token)).status_code == 401
    # 新密码可登录，旧密码不可
    assert _login(client, "cpm@example.com", "newsecret12345")
    assert client.post("/api/v1/auth/login",
                      json={"email": "cpm@example.com", "password": "secret12345"}).status_code == 422
