"""中文全文检索（负责人：丙）。

数据来自 OCR 模块回写的 pdf_text_index；主系统只读该表并 join 自己的 files，
不改动 OCR 模块的表结构（避免两套 DeclarativeBase 争用同一张表）。
"""
from datetime import date, datetime, time, timedelta

from sqlalchemy import DateTime, bindparam, select, text

from ...core.principal import Principal
from ...models import File


def _mysql_match() -> str:
    return "MATCH(t.content) AGAINST (:q IN NATURAL LANGUAGE MODE) > 0"


def search(session, user: Principal, q: str, *, limit: int, offset: int,
           file_id: str | None = None, tag: str | None = None,
           date_from: date | None = None, date_to: date | None = None) -> tuple[str, list[dict]]:
    from ..ocr.bridge import is_ready
    if not is_ready():
        # 索引由 OCR 模块回写，未挂载时没有可检索数据，返回空集而不是 500
        return "ocr_not_ready", []

    dialect = session.bind.dialect.name
    use_fulltext = dialect == "mysql" and len(q) >= 2  # ngram 分词器默认 token_size=2
    backend = "mysql_ngram" if use_fulltext else "substring"

    base = """
        SELECT t.file_id AS file_id, f.name AS file_name, t.page_no AS page_no,
               t.job_id AS job_id, t.revision AS revision, t.content AS content
        FROM pdf_text_index AS t JOIN files AS f ON f.id = t.file_id
        WHERE f.deleted_at IS NULL
    """
    params: dict = {"q": q, "limit": limit, "offset": offset}
    if not user.is_admin:
        base += " AND f.owner_id = :owner"
        params["owner"] = user.user_id
    if file_id:
        base += " AND f.id = :file_id"
        params["file_id"] = file_id
    if tag:
        # EXISTS avoids duplicate hits when a file has several tags.
        base += """ AND EXISTS (
            SELECT 1 FROM file_tags AS ft JOIN tags AS g ON g.id = ft.tag_id
            WHERE ft.file_id = f.id AND g.name = :tag
        )"""
        params["tag"] = tag
    if date_from:
        base += " AND f.created_at >= :date_from"
        params["date_from"] = datetime.combine(date_from, time.min)
    if date_to:
        base += " AND f.created_at < :date_before"
        params["date_before"] = datetime.combine(date_to + timedelta(days=1), time.min)
    base += f" AND ({_mysql_match() if use_fulltext else 't.content LIKE :like ESCAPE :esc'})"
    if not use_fulltext:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        params["like"] = f"%{escaped}%"
        params["esc"] = "\\"
    base += " ORDER BY t.updated_at DESC, t.id LIMIT :limit OFFSET :offset"

    statement = text(base)
    # Bind datetimes explicitly: SQLite stores SQLAlchemy DATETIME with microseconds.
    for name in ("date_from", "date_before"):
        if name in params:
            statement = statement.bindparams(bindparam(name, type_=DateTime()))
    rows = session.execute(statement, params).all()
    items = []
    for row in rows:
        content = row.content or ""
        position = content.find(q)
        start = max(0, position - 40) if position >= 0 else 0
        items.append(dict(file_id=row.file_id, file_name=row.file_name, page_no=row.page_no,
                          job_id=row.job_id, revision=row.revision,
                          snippet=content[start:start + 200]))
    return backend, items


def suggest_files(session, user: Principal, q: str, limit: int = 10) -> list[dict]:
    """文件名补全，与全文检索互补。"""
    statement = select(File.id, File.name).where(File.deleted_at.is_(None),
                                                 File.name.contains(q, autoescape=True))
    if not user.is_admin:
        statement = statement.where(File.owner_id == user.user_id)
    rows = session.execute(statement.order_by(File.created_at.desc()).limit(limit)).all()
    return [dict(file_id=row[0], file_name=row[1]) for row in rows]
