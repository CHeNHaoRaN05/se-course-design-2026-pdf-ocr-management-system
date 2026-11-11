"""文件落盘、列表、标签与删除（负责人：乙）。

与丙的耦合点（契约 C2/C5）：
  · 上传成功后调用 ocr.bridge.ensure_ocr_file 写 ocr_files 镜像；
  · 软删除调用 ocr.lifecycle.cancel_tasks（保留数据，可还原）；
  · 彻底删除调用 ocr.lifecycle.purge_file（清理任务、页 PNG、全文索引）。
OCR 模块未挂载时这些调用自动降级为 no-op，乙的代码不依赖 Paddle 环境。
"""
from pathlib import Path
import errno
import unicodedata

from fastapi import UploadFile, HTTPException
from sqlalchemy import select

from ...core.audit import audit
from ...core.errors import bad_request, not_found
from ...core.media import MediaError, inspect_media, save_upload
from ...core.principal import Principal, owned_file, visible_files
from ...models import File, Tag, User, now, uid


def normalize_folder(value: str) -> str:
    parts = [part.strip() for part in value.replace("\\", "/").split("/") if part.strip()]
    if len(parts) > 5 or any(p in {".", ".."} for p in parts):
        raise bad_request("分类最多5级，且不能包含 . 或 ..")
    result = "/" + "/".join(parts)
    if len(result) > 255:
        raise bad_request("分类路径过长")
    return result


def normalize_tags(values: list[str]) -> list[str]:
    result = list(dict.fromkeys(v.strip() for v in values if v.strip()))
    if len(result) > 20 or any(len(v) > 64 for v in result):
        raise bad_request("最多20个标签，每个不超过64字符")
    return result


def safe_name(value: str) -> str:
    name = value.replace("\\", "/").split("/")[-1].strip()
    name = "".join(c for c in name if not unicodedata.category(c).startswith("C"))
    if not name or name in {".", ".."}:
        raise bad_request("文件名不能为空")
    suffix = Path(name).suffix[:20]
    stem = name[:-len(suffix)] if suffix else name
    return stem[:255-len(suffix)] + suffix


def pdf_name(value: str) -> str:
    return safe_name(value if value.lower().endswith(".pdf") else value + ".pdf")


def available_name(session, owner_id: str, value: str) -> str:
    name = safe_name(value)
    names = set(session.scalars(select(File.name).where(File.owner_id == owner_id)))
    suffix = Path(name).suffix
    stem = name[:-len(suffix)] if suffix else name
    index = 1
    while name in names:
        tail = f"({index}){suffix}"
        name = stem[:255-len(tail)] + tail
        index += 1
    return name


def _tags_of(session, owner_id: str, names: list[str]) -> list[Tag]:
    result = []
    for raw in normalize_tags(names):
        name = raw.strip()
        if not name or len(name) > 64:
            continue
        tag = session.scalar(select(Tag).where(Tag.owner_id == owner_id, Tag.name == name))
        if tag is None:
            tag = Tag(owner_id=owner_id, name=name)
            session.add(tag)
            session.flush()
        result.append(tag)
    return result


def upload(session, settings, user: Principal, upload_file: UploadFile) -> File:
    session.execute(select(User.id).where(User.id == user.user_id).with_for_update()).all()
    raw_name = available_name(session, user.user_id, upload_file.filename or "document")
    ident = uid()
    key = f"uploads/{ident}.bin"
    try:
        size, digest = save_upload(storage=settings.storage_dir, key=key, stream=upload_file.file,
                                   max_upload_bytes=settings.max_upload_bytes)
        media_type, page_count = inspect_media(settings.storage_dir / key,
                                               max_pages=settings.max_pages, max_pixels=settings.max_pixels)
    except (MediaError, OSError) as exc:
        (settings.storage_dir / key).unlink(missing_ok=True)
        if isinstance(exc, OSError):
            if exc.errno == errno.ENOSPC:
                raise HTTPException(507, "存储空间不足") from exc
            raise
        raise bad_request(str(exc))
    record = File(id=ident, owner_id=user.user_id, name=raw_name, storage_key=key, media_type=media_type,
                  sha256=digest, size=size, page_count=page_count)
    try:
        session.add(record)
        session.flush()
        audit(session, user.user_id, "file_uploaded", ident, bytes=size, pages=page_count)
        _sync_ocr_file(session, record)
    except Exception:
        (settings.storage_dir / key).unlink(missing_ok=True)
        raise
    return record


def _sync_ocr_file(session, record: File) -> None:
    """写 OCR 适配层镜像（契约 C2）。OCR 未挂载时静默跳过。"""
    try:
        from ..ocr.bridge import ensure_ocr_file, is_ready
    except ImportError:
        return
    if not is_ready():
        return
    ensure_ocr_file(session, record)


def get(session, file_id: str, user: Principal) -> File:
    return owned_file(session, file_id, user)


def listing(session, user: Principal, *, folder: str | None, tag: str | None, q: str | None,
            limit: int, offset: int) -> list[File]:
    statement = visible_files(select(File), user)
    if folder:
        statement = statement.where(File.folder == folder)
    if tag:
        statement = statement.where(File.tags.any(Tag.name == tag))
    if q:
        statement = statement.where(File.name.contains(q, autoescape=True))
    statement = statement.order_by(File.created_at.desc(), File.id).limit(limit).offset(offset)
    return list(session.scalars(statement).unique().all())


def update(session, file_id: str, user: Principal, *, name=None, folder=None, tags=None) -> File:
    record = owned_file(session, file_id, user)
    if name is not None:
        record.name = safe_name(name)
    if folder is not None:
        record.folder = normalize_folder(folder)
    if tags is not None:
        record.tags = _tags_of(session, record.owner_id, tags)
    audit(session, user.user_id, "file_updated", file_id)
    _sync_ocr_file(session, record)
    return record


def soft_delete(session, file_id: str, user: Principal) -> File:
    """移入回收站：先取消未完成的 OCR 任务，数据与结果保留。"""
    record = owned_file(session, file_id, user)
    record.deleted_at = now()
    _cancel_ocr(session, file_id)
    audit(session, user.user_id, "file_trashed", file_id)
    return record


def restore(session, file_id: str, user: Principal) -> File:
    statement = select(File).where(File.id == file_id, File.deleted_at.is_not(None))
    record = session.scalar(statement)
    if record is None or (record.owner_id != user.user_id and not user.is_admin):
        raise not_found()
    record.deleted_at = None
    audit(session, user.user_id, "file_restored", file_id)
    return record


def purge(session, settings, file_id: str, user: Principal) -> None:
    """彻底删除：OCR 侧任务/页图/索引一并清理（契约 C5）。"""
    statement = select(File).where(File.id == file_id)
    record = session.scalar(statement)
    if record is None or (record.owner_id != user.user_id and not user.is_admin):
        raise not_found()
    _purge_ocr(session, settings, file_id)
    Path(settings.storage_dir / record.storage_key).unlink(missing_ok=True)
    session.delete(record)
    audit(session, user.user_id, "file_purged", file_id)


def _cancel_ocr(session, file_id: str) -> None:
    try:
        from ..ocr.bridge import is_ready
        from ..ocr.lifecycle import cancel_tasks
    except ImportError:
        return
    if not is_ready():
        return
    cancel_tasks(session, file_id)


def _purge_ocr(session, settings, file_id: str) -> None:
    try:
        from ..ocr.bridge import is_ready
        from ..ocr.lifecycle import purge_file
    except ImportError:
        return
    if not is_ready():
        return
    purge_file(session, settings, file_id)


def folders(session, user: Principal) -> list[str]:
    statement = select(File.folder).where(File.deleted_at.is_(None))
    if not user.is_admin:
        statement = statement.where(File.owner_id == user.user_id)
    return sorted({row for row in session.scalars(statement.distinct()) if row})


def tags(session, user: Principal) -> list[str]:
    statement = select(Tag.name).where(Tag.owner_id == user.user_id)
    return sorted(session.scalars(statement))


def page_sizes(session, settings, file_id: str, user: Principal) -> list[dict]:
    """阅读器契约 C4：返回每页点阵尺寸与内置旋转，供覆盖层换算。"""
    import pypdfium2 as pdfium
    record = owned_file(session, file_id, user)
    if record.media_type != "application/pdf":
        raise bad_request("仅 PDF 支持分页尺寸")
    from ...core.media import PDFIUM_LOCK
    with PDFIUM_LOCK, pdfium.PdfDocument(str(settings.storage_dir / record.storage_key)) as pdf:
        # pypdfium2 >= 4 起 PdfPage 只有 get_rotation()，没有 .rotation 属性
        return [{"page_no": i + 1, "width_pt": float(pdf[i].get_size()[0]), "height_pt": float(pdf[i].get_size()[1]),
                 "rotation": int(pdf[i].get_rotation())} for i in range(len(pdf))]
