"""配额与使用统计（负责人：甲）。"""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.database import get_session
from ...core.principal import Principal, current_user
from ...models import File
from .service import usage

router = APIRouter(prefix="/quota", tags=["01 用户与权限·甲"])


@router.get("", response_model=dict)
@router.get("/", response_model=dict)
def my_quota(session: Session = Depends(get_session), user: Principal = Depends(current_user)):
    """始终返回调用者自己的配额；管理员也不例外。"""
    settings_limit = usage(session, user.user_id)
    return settings_limit


@router.get("/overview", response_model=dict)
def overview(session: Session = Depends(get_session), user: Principal = Depends(current_user)):
    """文件量、存储量与配额。OCR 侧的任务统计由丙的 /ocr-host/usage 提供。"""
    statement = select(func.count(File.id), func.coalesce(func.sum(File.size), 0)).where(
        File.owner_id == user.user_id, File.deleted_at.is_(None))
    count, size = session.execute(statement).one()
    return {"files": count, "storage_bytes": int(size), "quota": usage(session, user.user_id)}
