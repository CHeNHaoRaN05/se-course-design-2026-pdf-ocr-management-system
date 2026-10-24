"""认证端点：注册、登录、当前用户、管理员改角色（负责人：甲）。

说明：修改角色由管理员经 PATCH /auth/users/{user_id}/role 完成（FR-USER-06）。
"""
from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ...core.audit import audit
from ...core.database import get_session
from ...core.errors import not_found
from ...core.principal import Principal, bearer, current_user, require_admin
from ...models import User
from .schemas import ChangePasswordIn, LoginIn, RegisterIn, RoleUpdate, TokenOut, UserOut
from .service import change_password, login, logout, refresh, register

router = APIRouter(prefix="/auth", tags=["01 用户与权限·甲"])


@router.post("/register", status_code=201, response_model=TokenOut)
def register_endpoint(body: RegisterIn, request: Request, session: Session = Depends(get_session)):
    user = register(session, body)
    session.commit()
    settings = request.app.state.settings
    return login(session, settings, LoginIn(email=user.email, password=body.password))


@router.post("/login", response_model=TokenOut)
def login_endpoint(body: LoginIn, request: Request, session: Session = Depends(get_session)):
    result = login(session, request.app.state.settings, body)
    session.commit()
    return result


@router.get("/me", response_model=UserOut)
def me(session: Session = Depends(get_session), user: Principal = Depends(current_user)):
    record = session.get(User, user.user_id)
    return UserOut(id=record.id, email=record.email, display_name=record.display_name,
                   role=record.role, created_at=record.created_at)


@router.get("/_admin/check", response_model=dict)
def admin_check(user: Principal = Depends(require_admin)):
    return {"ok": True, "role": user.role}


@router.patch("/users/{user_id}/role", response_model=UserOut)
def set_role(user_id: str, body: RoleUpdate, session: Session = Depends(get_session),
             admin: Principal = Depends(require_admin)):
    """FR-USER-06：管理员修改指定用户角色（user / viewer / admin）。"""
    target = session.get(User, user_id)
    if target is None:
        raise not_found()
    target.role = body.role
    audit(session, admin.user_id, "user_role_changed", user_id, role=body.role)
    session.commit()
    return UserOut(id=target.id, email=target.email, display_name=target.display_name,
                   role=target.role, created_at=target.created_at)


@router.post("/logout", status_code=204)
def logout_endpoint(request: Request, credentials: HTTPAuthorizationCredentials = Depends(bearer),
                   session: Session = Depends(get_session), user: Principal = Depends(current_user)):
    """FR-USER-03：单点登出，吊销当前令牌（其余会话不受影响）。"""
    logout(session, request.app.state.settings, credentials.credentials)
    session.commit()


@router.post("/refresh", response_model=TokenOut)
def refresh_endpoint(request: Request, credentials: HTTPAuthorizationCredentials = Depends(bearer),
                    session: Session = Depends(get_session), user: Principal = Depends(current_user)):
    """FR-USER-04：用当前有效令牌换新令牌，旧令牌立即失效。"""
    result = refresh(session, request.app.state.settings, credentials.credentials)
    session.commit()
    return result


@router.post("/change-password", response_model=TokenOut)
def change_password_endpoint(body: ChangePasswordIn, request: Request,
                            session: Session = Depends(get_session),
                            user: Principal = Depends(current_user)):
    """FR-USER-05：修改密码；成功后所有旧令牌失效并返回新令牌。"""
    result = change_password(session, request.app.state.settings, user.user_id, body)
    session.commit()
    return result
