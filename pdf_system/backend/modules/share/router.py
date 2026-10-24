"""分享与协作端点（负责人：甲，FR-SHR-01/02/03）。

owner 侧（需 JWT）：创建 / 列表 / 详情 / 取消 / 统计。
被分享者侧（旁路 token，无需 JWT）：GET /share/token/{token} 只读访问。
"""
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ...core.database import get_session
from ...core.errors import bad_request
from ...core.media import MediaError, safe_path
from ...core.principal import Principal, current_user, share_access
from ...models import ShareLink
from . import service
from .schemas import ShareCreate, ShareOut, ShareStats

router = APIRouter(prefix="/share", tags=["01 分享与协作·甲"])


def _out(link: ShareLink, base_url: str) -> ShareOut:
    return ShareOut(id=link.id, file_id=link.file_id, token=link.token,
                    share_url=f"{base_url}api/v1/share/token/{link.token}",
                    expires_at=link.expires_at, access_code=link.access_code,
                    allow_download=link.allow_download, visit_count=link.visit_count,
                    created_at=link.created_at)


# ---- owner 侧（需 JWT）----


@router.post("", status_code=201, response_model=ShareOut)
@router.post("/", status_code=201, response_model=ShareOut, include_in_schema=False)
def create(body: ShareCreate, request: Request, session: Session = Depends(get_session),
          user: Principal = Depends(current_user)):
    link = service.create_share(session, user, file_id=body.file_id, expires_at=body.expires_at,
                                access_code=body.access_code, allow_download=body.allow_download)
    session.commit()
    return _out(link, str(request.base_url))


@router.get("", response_model=list[ShareOut])
@router.get("/", response_model=list[ShareOut])
def list_shares(request: Request, session: Session = Depends(get_session),
                user: Principal = Depends(current_user)):
    return [_out(link, str(request.base_url)) for link in service.list_shares(session, user)]


@router.get("/{share_id}", response_model=ShareOut)
def detail(share_id: str, request: Request, session: Session = Depends(get_session),
           user: Principal = Depends(current_user)):
    return _out(service.get_share(session, user, share_id), str(request.base_url))


@router.delete("/{share_id}", status_code=204)
def cancel(share_id: str, session: Session = Depends(get_session),
           user: Principal = Depends(current_user)):
    service.cancel_share(session, user, share_id)
    session.commit()


@router.get("/{share_id}/stats", response_model=ShareStats)
def stats(share_id: str, session: Session = Depends(get_session),
          user: Principal = Depends(current_user)):
    link = service.share_stats(session, user, share_id)
    return ShareStats(id=link.id, file_id=link.file_id, visit_count=link.visit_count,
                      allow_download=link.allow_download, expires_at=link.expires_at,
                      created_at=link.created_at)


# ---- 被分享者侧（旁路 token，无需 JWT）----


@router.get("/token/{token}")
def view_token(token: str, request: Request, code: str | None = Query(default=None),
               session: Session = Depends(get_session)):
    """FR-SHR：被分享者凭 token 只读访问；错误/过期/提取码不符统一 404。"""
    link = share_access(token, session, code)
    record = service.shared_file(session, link)
    session.commit()  # 递增访问计数
    if link.allow_download:
        try:
            path = safe_path(request.app.state.settings.storage_dir, record.storage_key)
        except MediaError:
            raise bad_request("invalid_storage_key")
        return FileResponse(path, media_type=record.media_type, filename=record.name,
                            content_disposition_type="inline",
                            headers={"X-Content-Type-Options": "nosniff",
                                     "Cache-Control": "private, no-store"})
    # 不允许下载：仅返回元数据，供前端只读预览
    return {"id": record.id, "name": record.name, "media_type": record.media_type,
            "page_count": record.page_count, "size": record.size}
