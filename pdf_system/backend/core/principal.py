"""登录主体与权限依赖（负责人：甲）。

主系统与 OCR 模块共用同一份解析逻辑：OCR 侧通过
app.dependency_overrides[ocr_current_user] 复用下面的 resolve_principal，
从而保证"用户被禁用"在主系统和 OCR 接口上同时生效。
"""
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from ..models import ShareLink, User, now
from .config import Settings
from .errors import not_found
from .security import decode_token

ROLES = {"user", "viewer", "admin"}

bearer = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    user_id: str
    role: str = "user"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def resolve_principal(request: Request, credentials: HTTPAuthorizationCredentials | None) -> Principal:
    if credentials is None:
        raise HTTPException(401, "缺少 Bearer 令牌", headers={"WWW-Authenticate": "Bearer"})
    settings: Settings = request.app.state.settings
    try:
        claims = decode_token(credentials.credentials, secret=settings.jwt_secret,
                              issuer=settings.jwt_issuer, audience=settings.jwt_audience)
        sub, role = claims["sub"], claims.get("role", "user")
        if not isinstance(sub, str) or not 1 <= len(sub) <= 128 or role not in ROLES:
            raise ValueError("invalid principal")
    except Exception:
        raise HTTPException(401, "令牌无效或已过期", headers={"WWW-Authenticate": "Bearer"})

    with request.app.state.sessions() as session:
        user = session.get(User, sub)
        if user is None or user.disabled:
            raise HTTPException(401, "账号不存在或已停用")
        # 角色以库内为准，避免令牌里的旧角色继续生效
        return Principal(user_id=user.id, role=user.role)


def current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal:
    return resolve_principal(request, credentials)


def require_editor(user: Principal = Depends(current_user)) -> Principal:
    """viewer 只读。"""
    if user.role == "viewer":
        raise HTTPException(403, "只读角色，无权执行写操作")
    return user


def require_admin(user: Principal = Depends(current_user)) -> Principal:
    if user.role != "admin":
        raise HTTPException(403, "需要管理员角色")
    return user


def owned_file(session, file_id: str, user: Principal):
    """非本人资源统一 404，避免资源 ID 枚举。"""
    from ..models import File
    from .errors import not_found

    file = session.get(File, file_id)
    if file is None or file.deleted_at is not None:
        raise not_found()
    if file.owner_id != user.user_id and not user.is_admin:
        raise not_found()
    return file


def visible_files(statement, user: Principal):
    from ..models import File

    statement = statement.where(File.deleted_at.is_(None))
    if not user.is_admin:
        statement = statement.where(File.owner_id == user.user_id)
    return statement


def share_access(token: str, session, code: str | None = None) -> ShareLink:
    """分享旁路解析：凭 token（非 JWT）校验分享链接，供被分享者只读访问。

    严格不改动 resolve_principal 主路径；错误 token / 过期 / 提取码不符统一 404，
    避免泄露分享是否存在。返回前递增访问计数（visit_count）。
    """
    link = session.scalar(select(ShareLink).where(ShareLink.token == token))
    if link is None:
        raise not_found()
    if link.expires_at is not None and link.expires_at < now():
        raise not_found()
    if link.access_code is not None and link.access_code != (code or ""):
        raise not_found()
    link.visit_count += 1
    return link
