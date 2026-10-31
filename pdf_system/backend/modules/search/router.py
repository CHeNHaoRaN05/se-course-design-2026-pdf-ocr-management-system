"""检索端点（负责人：丙）。

与 OCR 模块自带的 /api/v1/ocr/search 的区别：
  · 这里 join 主系统 files，支持回收站过滤、文件名补全与统一响应结构；
  · 前端统一走本接口，避免维护两套权限口径。
"""
from datetime import date

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
              offset: int = Query(0, ge=0),
              file_id: str | None = Query(None, pattern=r"^[0-9a-f]{32}$"),
              tag: str | None = Query(None, min_length=1, max_length=64),
              date_from: date | None = None, date_to: date | None = None,
              session: Session = Depends(get_session),
              user: Principal = Depends(current_user)):
    keyword = q.strip()
    if not keyword:
        raise bad_request("检索词不能为空")
    if tag is not None and not tag.strip():
        raise bad_request("标签不能为空")
    if date_from and date_to and date_from > date_to:
        raise bad_request("开始日期不能晚于结束日期")
    if date_to == date.max:
        raise bad_request("结束日期必须早于 9999-12-31")
    backend, items = search(session, user, keyword, limit=limit, offset=offset,
                           file_id=file_id, tag=tag.strip() if tag else None,
                           date_from=date_from, date_to=date_to)
    return {"backend": backend, "items": items}


@router.get("/suggest", response_model=dict)
def suggest(q: str = Query(min_length=1, max_length=100), session: Session = Depends(get_session),
            user: Principal = Depends(current_user)):
    return {"items": suggest_files(session, user, q.strip())}
