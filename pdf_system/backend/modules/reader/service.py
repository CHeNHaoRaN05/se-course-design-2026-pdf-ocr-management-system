"""书签与批注的业务逻辑（负责人：乙）。"""
from sqlalchemy import select

from ...core.audit import audit
from ...core.errors import conflict, not_found
from ...models import Annotation, Bookmark, uid
from ...core.principal import Principal, owned_file


def list_bookmarks(session, file_id: str, user: Principal) -> list[Bookmark]:
    owned_file(session, file_id, user)  # 权限预检，非本人一律 404
    return list(session.scalars(select(Bookmark).where(Bookmark.file_id == file_id,
                                                       Bookmark.owner_id == user.user_id)
                                .order_by(Bookmark.page_no)))


def add_bookmark(session, file_id: str, user: Principal, *, page_no: int, title: str) -> Bookmark:
    owned_file(session, file_id, user)
    existing = session.scalar(select(Bookmark).where(Bookmark.file_id == file_id,
                                                     Bookmark.owner_id == user.user_id,
                                                     Bookmark.page_no == page_no))
    if existing:
        raise conflict("该页已有书签")
    record = Bookmark(id=uid(), file_id=file_id, owner_id=user.user_id, page_no=page_no, title=title.strip())
    session.add(record)
    session.flush()
    audit(session, user.user_id, "bookmark_created", file_id, page_no=page_no)
    return record


def remove_bookmark(session, file_id: str, user: Principal, bookmark_id: str) -> None:
    record = session.get(Bookmark, bookmark_id)
    if record is None or record.file_id != file_id or record.owner_id != user.user_id:
        raise not_found()
    session.delete(record)
    audit(session, user.user_id, "bookmark_deleted", file_id, page_no=record.page_no)


def list_annotations(session, file_id: str, user: Principal, page_no: int | None = None) -> list[Annotation]:
    owned_file(session, file_id, user)
    statement = select(Annotation).where(Annotation.file_id == file_id, Annotation.owner_id == user.user_id)
    if page_no:
        statement = statement.where(Annotation.page_no == page_no)
    return list(session.scalars(statement.order_by(Annotation.page_no, Annotation.created_at)))


def add_annotation(session, file_id: str, user: Principal, *, page_no: int, kind: str,
                   text: str, bbox: list[float] | None) -> Annotation:
    record = owned_file(session, file_id, user)
    if page_no > max(1, record.page_count):
        raise conflict("页码超出文件范围")
    annotation = Annotation(id=uid(), file_id=file_id, owner_id=user.user_id, page_no=page_no, kind=kind,
                            payload={"text": text, "bbox": bbox})
    session.add(annotation)
    session.flush()
    audit(session, user.user_id, "annotation_created", file_id, page_no=page_no, kind=kind)
    return annotation


def remove_annotation(session, file_id: str, user: Principal, annotation_id: str) -> None:
    record = session.get(Annotation, annotation_id)
    if record is None or record.file_id != file_id or record.owner_id != user.user_id:
        raise not_found()
    session.delete(record)
    audit(session, user.user_id, "annotation_deleted", file_id, page_no=record.page_no)
