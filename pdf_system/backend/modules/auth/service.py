"""注册登录业务逻辑（负责人：甲）。"""
from sqlalchemy import func, select

from ...core.audit import audit
from ...core.errors import bad_request, conflict
from ...models import User, now
from ...core.security import create_access_token, hash_password, verify_password
from .schemas import LoginIn, RegisterIn, TokenOut


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


def login(session, settings, body: LoginIn) -> TokenOut:
    email = body.email.strip().lower()
    user = session.scalar(select(User).where(func.lower(User.email) == email))
    # 不区分"邮箱不存在"与"密码错误"，避免账号枚举
    if user is None or user.disabled or not verify_password(body.password, user.password_hash):
        raise bad_request("邮箱或密码不正确")
    user.login_count += 1
    user.last_login_at = now()
    audit(session, user.id, "user_logged_in", user.id)
    token = create_access_token(user_id=user.id, role=user.role, secret=settings.jwt_secret,
                                issuer=settings.jwt_issuer, audience=settings.jwt_audience,
                                expire_minutes=settings.jwt_expire_minutes)
    return TokenOut(access_token=token, expires_in=settings.jwt_expire_minutes * 60, role=user.role)
