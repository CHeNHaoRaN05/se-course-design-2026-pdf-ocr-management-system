"""认证端点：注册、登录、当前用户、管理员改角色（负责人：甲）。

说明：修改角色由管理员经 PATCH /auth/users/{user_id}/role 完成（FR-USER-06）。
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ...core.audit import audit
from ...core.database import get_session
from ...core.errors import not_found
from ...core.principal import Principal, current_user, require_admin
from ...models import User
from .schemas import LoginIn, RegisterIn, RoleUpdate, TokenOut, UserOut
from .service import login, register

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
