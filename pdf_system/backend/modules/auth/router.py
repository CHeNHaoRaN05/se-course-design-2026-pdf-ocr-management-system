"""认证端点：注册、登录、当前用户（负责人：甲）。

说明：系统不提供"修改角色"的公开端点，角色调整由管理员直接改库或在 W7 补管理端。
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ...core.database import get_session
from ...core.principal import Principal, current_user, require_admin
from ...models import User
from .schemas import LoginIn, RegisterIn, TokenOut, UserOut
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
