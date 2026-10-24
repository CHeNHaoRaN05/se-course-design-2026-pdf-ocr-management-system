"""注册登录业务逻辑（负责人：甲）。"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select

from ...core.audit import audit
from ...core.errors import bad_request, conflict
from ...models import RevokedToken, User, now
from ...core.security import (create_access_token, decode_token, hash_password,
                              verify_password)
from .schemas import ChangePasswordIn, LoginIn, RegisterIn, TokenOut


def register(session, body: RegisterIn) -> User:
    email = body.email.strip().lower()
    if session.scalar(select(User).where(func.lower(User.email) == email)):
        raise conflict("该邮箱已注册")
    user = User(email=email, display_name=body.display_name.strip() or email.split("@")[0],
                password_hash=hash_password(body.password))
    session.add(user)
    session.flush()
    audit(session, user.id, "user_registered", user.id)
    return user


def _issue(settings, *, user_id: str, role: str, token_version: int) -> TokenOut:
    token = create_access_token(user_id=user_id, role=role, secret=settings.jwt_secret,
                                issuer=settings.jwt_issuer, audience=settings.jwt_audience,
                                expire_minutes=settings.jwt_expire_minutes,
                                jti=uuid.uuid4().hex, token_version=token_version)
    return TokenOut(access_token=token, expires_in=settings.jwt_expire_minutes * 60, role=role)


def login(session, settings, body: LoginIn) -> TokenOut:
    email = body.email.strip().lower()
    user = session.scalar(select(User).where(func.lower(User.email) == email))
    # 不区分"邮箱不存在"与"密码错误"，避免账号枚举
    if user is None or user.disabled or not verify_password(body.password, user.password_hash):
        raise bad_request("邮箱或密码不正确")
    user.login_count += 1
    user.last_login_at = now()
    audit(session, user.id, "user_logged_in", user.id)
    return _issue(settings, user_id=user.id, role=user.role, token_version=user.token_version)


def logout(session, settings, token: str) -> None:
    """FR-USER-03：吊销当前令牌（单点登出）。"""
    try:
        claims = decode_token(token, secret=settings.jwt_secret, issuer=settings.jwt_issuer,
                              audience=settings.jwt_audience)
    except Exception:
        return
    jti = claims.get("jti")
    if not jti or session.get(RevokedToken, jti) is not None:
        return
    exp = claims.get("exp")
    if isinstance(exp, (int, float)):
        exp = datetime.fromtimestamp(exp, tz=timezone.utc).replace(tzinfo=None)
    session.add(RevokedToken(jti=jti, user_id=str(claims.get("sub", "")),
                             expires_at=exp, revoked_at=now()))
    audit(session, str(claims.get("sub", "")), "user_logged_out", str(claims.get("sub", "")))


def refresh(session, settings, token: str) -> TokenOut:
    """FR-USER-04：用当前有效令牌换新令牌，并吊销旧 jti。"""
    claims = decode_token(token, secret=settings.jwt_secret, issuer=settings.jwt_issuer,
                          audience=settings.jwt_audience)
    sub = claims["sub"]
    role = claims.get("role", "user")
    tv = claims.get("tv", 0)
    old_jti = claims.get("jti")
    result = _issue(settings, user_id=sub, role=role, token_version=tv)
    if old_jti:
        exp = claims.get("exp")
        if isinstance(exp, (int, float)):
            exp = datetime.fromtimestamp(exp, tz=timezone.utc).replace(tzinfo=None)
        session.add(RevokedToken(jti=old_jti, user_id=sub, expires_at=exp, revoked_at=now()))
        audit(session, sub, "token_refreshed", sub)
    return result


def change_password(session, settings, user_id: str, body: ChangePasswordIn) -> TokenOut:
    """FR-USER-02：校验原密码 → 改密 → token_version 自增（全部旧令牌失效）→ 发新令牌。"""
    record = session.get(User, user_id)
    if record is None or not verify_password(body.old_password, record.password_hash):
        raise bad_request("原密码不正确")
    record.password_hash = hash_password(body.new_password)
    record.token_version = (record.token_version or 0) + 1
    audit(session, user_id, "user_password_changed", user_id)
    return _issue(settings, user_id=record.id, role=record.role, token_version=record.token_version)


def set_disabled(session, target: User, disabled: bool, *, actor_id: str) -> User:
    """FR-USER-04：管理员禁用/解禁账号；禁用后其所有令牌立即失效（resolve_principal 拦截 disabled）。"""
    target.disabled = bool(disabled)
    audit(session, actor_id, "user_disabled" if disabled else "user_enabled", target.id)
    return target
