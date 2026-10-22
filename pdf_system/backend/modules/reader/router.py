"""阅读器端点：书签、批注（负责人：乙）。

pdf.js 的渲染本身在前端完成，后端只负责页面尺寸（见 files 路由）与个人标注数据。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...core.database import get_session
from ...core.principal import Principal, current_user, require_editor
from .schemas import AnnotationIn, AnnotationOut, BookmarkIn, BookmarkOut
from .service import (add_annotation, add_bookmark, list_annotations, list_bookmarks,
                      remove_annotation, remove_bookmark)

router = APIRouter(prefix="/files/{file_id}/reader", tags=["02 文件管理与阅读器·乙"])


@router.get("/bookmarks", response_model=list[BookmarkOut])
def get_bookmarks(file_id: str, session: Session = Depends(get_session), user: Principal = Depends(current_user)):
    return list_bookmarks(session, file_id, user)


@router.post("/bookmarks", status_code=201, response_model=BookmarkOut)
def post_bookmark(file_id: str, body: BookmarkIn, session: Session = Depends(get_session),
                  user: Principal = Depends(require_editor)):
    record = add_bookmark(session, file_id, user, page_no=body.page_no, title=body.title)
    session.commit()
    return record


@router.delete("/bookmarks/{bookmark_id}", status_code=204)
def delete_bookmark(file_id: str, bookmark_id: str, session: Session = Depends(get_session),
                    user: Principal = Depends(require_editor)):
    remove_bookmark(session, file_id, user, bookmark_id)
    session.commit()


@router.get("/annotations", response_model=list[AnnotationOut])
def get_annotations(file_id: str, page_no: int | None = Query(default=None, ge=1),
                    session: Session = Depends(get_session), user: Principal = Depends(current_user)):
    return list_annotations(session, file_id, user, page_no)


@router.post("/annotations", status_code=201, response_model=AnnotationOut)
def post_annotation(file_id: str, body: AnnotationIn, session: Session = Depends(get_session),
                    user: Principal = Depends(require_editor)):
    record = add_annotation(session, file_id, user, page_no=body.page_no, kind=body.kind,
                            text=body.text, bbox=body.bbox)
    session.commit()
    return record


@router.delete("/annotations/{annotation_id}", status_code=204)
def delete_annotation(file_id: str, annotation_id: str, session: Session = Depends(get_session),
                      user: Principal = Depends(require_editor)):
    remove_annotation(session, file_id, user, annotation_id)
    session.commit()
