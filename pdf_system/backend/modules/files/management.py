"""02 线管理能力；复用现有上传、归属、镜像和删除契约。"""
import errno
import io
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Literal, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.database import get_session
from ...core.errors import bad_request
from ...core.media import PDFIUM_LOCK, MediaError, inspect_media, safe_path
from ...core.principal import Principal, current_user, owned_file, require_editor
from ...models import File, User
from . import service
from .schemas import FileOut, FileQueryOut, TrashOut
from ...core.pagination import PageResult
from ...core.audit import audit

router = APIRouter(prefix="/files", tags=["02 文件管理"])
MAX_OFFSET = 1_000_000
MediaType = Literal["application/pdf", "image/png", "image/jpeg"]
Status = Literal["none", "queued", "running", "retry_wait", "succeeded", "partial_success", "failed", "cancelled"]


def view(record, **extra):
    return dict(id=record.id, name=record.name, folder=record.folder, media_type=record.media_type,
                size=record.size, page_count=record.page_count, version=record.version,
                tags=[t.name for t in record.tags], created_at=record.created_at, replaced_from=record.replaced_from, **extra)


def date_filter(statement, column, date_from, date_to):
    if date_from and date_to and date_from > date_to:
        raise bad_request("开始日期不能晚于结束日期")
    if date_to == date.max:
        raise bad_request("结束日期必须早于 9999-12-31")
    if date_from:
        statement = statement.where(column >= datetime.combine(date_from, time.min))
    if date_to:
        statement = statement.where(column < datetime.combine(date_to + timedelta(days=1), time.min))
    return statement


@router.get("/query", response_model=FileQueryOut)
def query(request: Request, q: str = Query("", max_length=255), folder: str | None = Query(None, max_length=255),
          tag: str | None = Query(None, max_length=64), media_type: MediaType | None = None,
          date_from: date | None = None, date_to: date | None = None,
          status: Status | None = None, sort: Literal["newest", "name", "size", "pages", "status"] = "newest",
          limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=MAX_OFFSET),
          session: Session = Depends(get_session), user: Principal = Depends(current_user)):
    available = bool(request.app.state.ocr_mounted)
    state = None
    generation = None
    if available:
        from ocr_service.db import Job
        state = select(Job.status).where(Job.file_id == File.id).order_by(
            Job.created_at.desc(), Job.id.desc()).limit(1).correlate(File).scalar_subquery()
        generation = select(Job.generation).where(Job.file_id == File.id).order_by(
            Job.created_at.desc(), Job.id.desc()).limit(1).correlate(File).scalar_subquery()
    statement = select(File).where(File.deleted_at.is_(None))
    if not user.is_admin:
        statement = statement.where(File.owner_id == user.user_id)
    if q.strip():
        statement = statement.where(File.name.contains(q.strip(), autoescape=True))
    if folder:
        statement = statement.where((File.folder == folder) | File.folder.startswith(folder.rstrip("/") + "/", autoescape=True))
    if tag:
        statement = statement.where(File.tags.any(name=tag))
    if media_type:
        statement = statement.where(File.media_type == media_type)
    statement = date_filter(statement, File.created_at, date_from, date_to)
    if status and available:
        statement = statement.where(func.coalesce(state, "none") == status)
    total = session.scalar(select(func.count()).select_from(statement.subquery()))
    ordering = {"newest": File.created_at.desc(), "name": File.name.asc(), "size": File.size.desc(),
                "pages": File.page_count.desc(), "status": func.coalesce(state, "none") if available else File.created_at.desc()}
    statement = statement.order_by(ordering[sort], File.id.asc()).limit(limit).offset(offset)
    if available:
        rows = session.execute(statement.add_columns(state, generation)).all()
        items = [view(record, status=job_status or "none", generation=job_generation or 0) for record, job_status, job_generation in rows]
    else:
        items = [view(record, status="unknown", generation=None) for record in session.scalars(statement)]
    return {"items": items, "total": total, "status_available": available, "effective_sort": "newest" if sort == "status" and not available else sort}


@router.get("/trash", response_model=PageResult[TrashOut] | list[TrashOut])
def trash(q: str = Query("", max_length=255), envelope: bool = False, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=MAX_OFFSET),
          session: Session = Depends(get_session), user: Principal = Depends(current_user)):
    statement = select(File).where(File.deleted_at.is_not(None))
    if not user.is_admin:
        statement = statement.where(File.owner_id == user.user_id)
    if q.strip():
        statement = statement.where(File.name.contains(q.strip(), autoescape=True))
    total = session.scalar(select(func.count()).select_from(statement.subquery()))
    rows = session.scalars(statement.order_by(File.deleted_at.desc(), File.id).limit(limit).offset(offset))
    items = [view(record, deleted_at=record.deleted_at) for record in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset} if envelope else items


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FileIds(Strict):
    file_ids: list[str] = Field(min_length=1, max_length=100, json_schema_extra={"uniqueItems": True})

    @model_validator(mode="after")
    def unique(self):
        if len(self.file_ids) != len(set(self.file_ids)):
            raise ValueError("文件 ID 不得重复")
        return self


class Bulk(FileIds):
    action: Literal["move", "tag", "delete"]
    folder: str | None = Field(None, max_length=255)
    tags: list[str] | None = Field(None, max_length=20)
    append_tags: bool = True


class BulkItem(BaseModel):
    id: str
    name: str
    ok: bool
    message: str | None = None


class BulkResult(BaseModel):
    items: list[BulkItem]
    succeeded: int
    failed: int


@router.post("/bulk", response_model=BulkResult, responses={207: {"model": BulkResult}, 409: {"model": BulkResult}})
def bulk(body: Bulk, session: Session = Depends(get_session), user: Principal = Depends(require_editor)):
    # 全批归属检查在任何修改前进行，越权不暴露名称，且不产生前序写入。
    records = []
    for ident in body.file_ids:
        record = session.get(File, ident)
        if record is None or (record.owner_id != user.user_id and not user.is_admin):
            from ...core.errors import not_found
            raise not_found()
        records.append(record)
    if body.action == "move" and (body.folder is None or not body.folder.strip()):
        raise bad_request("移动操作需要非空分类；根目录请填写 /")
    folder = service.normalize_folder(body.folder) if body.action == "move" and body.folder is not None else None
    if body.action == "move" and folder is None:
        raise bad_request("移动操作需要目标分类")
    tags = service.normalize_tags(body.tags) if body.action == "tag" and body.tags is not None else None
    if body.action == "tag" and tags is None:
        raise bad_request("打标操作需要标签")
    entries = [(record.id, record.name) for record in records]
    items = []
    session.rollback()  # 结束只读事务；每个操作独立提交并准确报告部分失败。
    for ident, name in entries:
        try:
            if body.action == "delete":
                service.soft_delete(session, ident, user)
            else:
                labels = tags
                if body.action == "tag" and body.append_tags:
                    record = owned_file(session, ident, user)
                    labels = service.normalize_tags([t.name for t in record.tags] + tags)
                service.update(session, ident, user, folder=folder, tags=labels)
            session.commit()
            items.append({"id": ident, "name": name, "ok": True})
        except HTTPException as exc:
            session.rollback()
            items.append({"id": ident, "name": name, "ok": False, "message": str(exc.detail)})
        except Exception:
            session.rollback()
            items.append({"id": ident, "name": name, "ok": False, "message": "操作失败，请刷新后重试"})
    succeeded = sum(item["ok"] for item in items)
    result = {"items": items, "succeeded": succeeded, "failed": len(items) - succeeded}
    return JSONResponse(result, status_code=200 if succeeded == len(items) else 207 if succeeded else 409)


class Merge(FileIds):
    file_ids: list[str] = Field(min_length=2, max_length=100, json_schema_extra={"uniqueItems": True})
    name: str = Field(min_length=1, max_length=255)


class Split(Strict):
    name: str = Field(min_length=1, max_length=200)
    groups: list[Annotated[list[Annotated[int, Field(ge=1, le=100, strict=True)]], Field(min_length=1, max_length=100, json_schema_extra={"uniqueItems": True})]] | None = Field(None, min_length=1, max_length=100)
    every: int | None = Field(None, ge=1, le=100)

    @model_validator(mode="after")
    def exclusive(self):
        if (self.groups is None) == (self.every is None):
            raise ValueError("groups 和 every 必须且只能提供一个")
        if self.groups is not None:
            flat = [page for group in self.groups for page in group]
            if any(not group or len(group) > 100 for group in self.groups) or len(flat) > 100 or len(set(flat)) != len(flat) or any(p < 1 for p in flat):
                raise ValueError("页段不能为空、重复、重叠或超过100页")
        return self


def sources(session, settings, user, ids):
    result = []
    for ident in ids:
        record = owned_file(session, ident, user)
        if record.media_type != "application/pdf":
            raise bad_request("仅支持 PDF 文件")
        try:
            import pypdfium2 as pdfium
            import pypdfium2.raw as raw
            path = safe_path(settings.storage_dir, record.storage_key)
            kind, count = inspect_media(path, max_pages=settings.max_pages, max_pixels=settings.max_pixels)
            with PDFIUM_LOCK, pdfium.PdfDocument(str(path)) as document:
                if raw.FPDF_GetSecurityHandlerRevision(document) >= 0:
                    raise MediaError("invalid_or_encrypted_pdf")
                for page_no in range(count):
                    page = document[page_no]
                    try:
                        width, height = page.get_size()
                        if width * height * 4 > settings.max_pixels:
                            raise MediaError("render_pixel_limit")
                    finally:
                        page.close()
        except MediaError as exc:
            raise bad_request(str(exc)) from exc
        except (OSError, pdfium.PdfiumError) as exc:
            raise bad_request("invalid_or_encrypted_pdf") from exc
        if kind != "application/pdf":
            raise bad_request("invalid_or_encrypted_pdf")
        result.append((path, count))
    return result


def generate(session, settings, user, plans, source_ids):
    """PDFium calls alone hold its lock; filesystem/SQL do not. Output batch is atomic."""
    import pypdfium2 as pdfium
    created = []
    try:
        originals = [owned_file(session, ident, user) for ident in source_ids]
        version = max(record.version for record in originals) + 1
        for name, parts in plans:
            with PDFIUM_LOCK:
                with pdfium.PdfDocument.new() as output:
                    for path, pages in parts:
                        with pdfium.PdfDocument(str(path)) as source:
                            output.import_pages(source, pages=pages)
                    data = io.BytesIO()
                    output.save(data)
            if data.tell() > settings.max_upload_bytes:
                raise bad_request("upload_size_limit")
            data.seek(0)
            uploaded = service.upload(session, settings, user, UploadFile(data, filename=service.pdf_name(name)))
            created.append(uploaded)
            uploaded.version = version
            uploaded.replaced_from = source_ids[0]
            audit(session, user.user_id, "file_derived", uploaded.id, source_file_ids=source_ids, version=version)
        result = [view(record) for record in created]
        session.commit()
        return result
    except Exception as exc:
        paths = [settings.storage_dir / record.storage_key for record in created]
        session.rollback()
        for path in paths:
            path.unlink(missing_ok=True)
        if isinstance(exc, HTTPException):
            raise
        if isinstance(exc, OSError) and exc.errno == errno.ENOSPC:
            raise HTTPException(507, "存储空间不足") from exc
        if isinstance(exc, (MediaError, pdfium.PdfiumError)):
            raise bad_request(str(exc) if isinstance(exc, MediaError) else "invalid_or_encrypted_pdf") from exc
        raise


@router.post("/merge", status_code=201, response_model=FileOut)
def merge(body: Merge, request: Request, session: Session = Depends(get_session), user: Principal = Depends(require_editor)):
    settings = request.app.state.settings
    files = sources(session, settings, user, body.file_ids)
    if sum(count for _, count in files) > settings.max_pages:
        raise bad_request("pdf_page_limit")
    return generate(session, settings, user, [(body.name, [(path, list(range(count))) for path, count in files])], body.file_ids)[0]


@router.post("/{file_id}/split", status_code=201, response_model=list[FileOut])
def split(file_id: str, body: Split, request: Request, session: Session = Depends(get_session), user: Principal = Depends(require_editor)):
    settings = request.app.state.settings
    path, count = sources(session, settings, user, [file_id])[0]
    groups = body.groups if body.groups is not None else [list(range(start, min(start + body.every, count + 1))) for start in range(1, count + 1, body.every)]
    if any(page > count for group in groups for page in group):
        raise bad_request("拆分页码超出文件实际范围")
    return generate(session, settings, user, [(f"{body.name}-{i + 1}.pdf", [(path, [page - 1 for page in group])]) for i, group in enumerate(groups)], [file_id])
