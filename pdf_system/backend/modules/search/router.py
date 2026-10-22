"""检索端点（负责人：丙）。

与 OCR 模块自带的 /api/v1/ocr/search 的区别：
  · 这里 join 主系统 files，支持回收站过滤、文件名补全与统一响应结构；
  · 前端统一走本接口，避免维护两套权限口径。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...core.database import get_session
from ...core.errors import bad_request
from ...core.principal import Principal, current_user
from .service import search, suggest_files

router = APIRouter(prefix="/search", tags=["03 OCR 与检索·丙"])


@router.get("", response_model=dict)
@router.get("/", response_model=dict, include_in_schema=False)
def full_text(q: str = Query(min_length=1, max_length=100), limit: int = Query(20, ge=1, le=100),
              offset: int = Query(0, ge=0), session: Session = Depends(get_session),
              user: Principal = Depends(current_user)):
    keyword = q.strip()
    if not keyword:
        raise bad_request("检索词不能为空")
    backend, items = search(session, user, keyword, limit=limit, offset=offset)
    return {"backend": backend, "items": items}


@router.get("/suggest", response_model=dict)
def suggest(q: str = Query(min_length=1, max_length=100), session: Session = Depends(get_session),
            user: Principal = Depends(current_user)):
    return {"items": suggest_files(session, user, q.strip())}
