"""文件管理端点（负责人：乙）。

W7 待补（小组成员自行认领）：合并 / 拆分 / 批量操作，见 README 的迭代清单。
"""
from fastapi import APIRouter, Depends, File as UploadField, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ...core.database import get_session
from ...core.media import MediaError, safe_path
from ...core.principal import Principal, current_user, require_editor
from .schemas import FileOut, FileUpdate, PageOut
from .service import (folders, get, listing, page_sizes, purge, restore, soft_delete, tags, update, upload)

router = APIRouter(prefix="/files", tags=["02 文件管理与阅读器·乙"])


def view(record) -> dict:
    return dict(id=record.id, name=record.name, folder=record.folder, media_type=record.media_type,
                size=record.size, page_count=record.page_count, version=record.version,
                tags=[t.name for t in record.tags], created_at=record.created_at)


@router.post("", status_code=201, response_model=FileOut)
@router.post("/", status_code=201, response_model=FileOut, include_in_schema=False)
def upload_endpoint(request: Request, file: UploadFile = UploadField(...),
                    session: Session = Depends(get_session), user: Principal = Depends(require_editor)):
    record = upload(session, request.app.state.settings, user, file)
    session.commit()
    return view(record)


@router.get("", response_model=list[FileOut])
def list_endpoint(folder: str | None = None, tag: str | None = None, q: str | None = None,
                  limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                  session: Session = Depends(get_session), user: Principal = Depends(current_user)):
    return [view(r) for r in listing(session, user, folder=folder, tag=tag, q=q, limit=limit, offset=offset)]


@router.get("/folders", response_model=list[str])
def list_folders(session: Session = Depends(get_session), user: Principal = Depends(current_user)):
    return folders(session, user)


@router.get("/tags", response_model=list[str])
def list_tags(session: Session = Depends(get_session), user: Principal = Depends(current_user)):
    return tags(session, user)


@router.get("/{file_id}", response_model=FileOut)
def get_endpoint(file_id: str, session: Session = Depends(get_session), user: Principal = Depends(current_user)):
    return view(get(session, file_id, user))


@router.get("/{file_id}/content")
def content_endpoint(file_id: str, request: Request, session: Session = Depends(get_session),
                     user: Principal = Depends(current_user)):
    """原文件（支持 Range，pdf.js 用 httpHeaders 携带 JWT 直接请求）。"""
    record = get(session, file_id, user)
    try:
        path = safe_path(request.app.state.settings.storage_dir, record.storage_key)
    except MediaError:
        from ...core.errors import bad_request
        raise bad_request("invalid_storage_key")
    return FileResponse(path, media_type=record.media_type, filename=record.name,
                        content_disposition_type="inline",
                        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})


@router.get("/{file_id}/pages", response_model=list[PageOut])
def pages_endpoint(file_id: str, request: Request, session: Session = Depends(get_session),
                   user: Principal = Depends(current_user)):
    return page_sizes(session, request.app.state.settings, file_id, user)


@router.patch("/{file_id}", response_model=FileOut)
def update_endpoint(file_id: str, body: FileUpdate, session: Session = Depends(get_session),
                    user: Principal = Depends(require_editor)):
    record = update(session, file_id, user, name=body.name, folder=body.folder, tags=body.tags)
    session.commit()
    return view(record)


@router.delete("/{file_id}", response_model=FileOut)
def trash_endpoint(file_id: str, session: Session = Depends(get_session), user: Principal = Depends(require_editor)):
    record = soft_delete(session, file_id, user)
    session.commit()
    return view(record)


@router.post("/{file_id}/restore", response_model=FileOut)
def restore_endpoint(file_id: str, session: Session = Depends(get_session), user: Principal = Depends(require_editor)):
    record = restore(session, file_id, user)
    session.commit()
    return view(record)


@router.delete("/{file_id}/purge", status_code=204)
def purge_endpoint(file_id: str, request: Request, session: Session = Depends(get_session),
                   user: Principal = Depends(require_editor)):
    purge(session, request.app.state.settings, file_id, user)
    session.commit()
