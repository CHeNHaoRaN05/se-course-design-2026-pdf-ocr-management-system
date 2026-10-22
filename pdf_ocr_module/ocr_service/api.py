import hashlib
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, File as UploadField, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, select, text, update

from .auth import current_user, editor, owned
from .config import Settings
from .db import Audit, Base, File, Job, Page, TextIndex, audit, database, now, uid
from .exports import export_pages
from .media import MediaError, inspect_media, safe_path
from .queue import TERMINAL, release_file, write_index
from .schemas import Correction, FileOut, JobCreate, JobOut, PageOut, SearchOut
from .tables import assign_cells

router = APIRouter(prefix="/api/v1/ocr", tags=["OCR"])


def db(request: Request):
    with request.app.state.ocr_sessions() as session:
        yield session


def file_view(file):
    return {key: getattr(file, key) for key in ("id", "name", "media_type", "size", "page_count", "created_at")}


def page_view(page):
    return {key: getattr(page, key) for key in ("page_no", "status", "revision", "error", "result")}


def job_view(session, job):
    pages = session.scalars(select(Page).where(Page.job_id == job.id).order_by(Page.page_no)).all()
    success = sum(p.status == "succeeded" for p in pages)
    return dict(id=job.id, file_id=job.file_id, status=job.status, options=job.options, attempts=job.attempts,
                progress=dict(total=len(pages), succeeded=success, failed=sum(p.status == "failed" for p in pages),
                              percent=round(100 * success / len(pages), 1)),
                pages=[dict(page_no=p.page_no, status=p.status, error=p.error) for p in pages],
                created_at=job.created_at, finished_at=job.finished_at)


@router.get("/capabilities")
def capabilities(request: Request, user=Depends(current_user)):
    cfg = request.app.state.ocr_settings
    return dict(modes=["general"] + (["handwriting"] if cfg.handwriting_detector and cfg.handwriting_detector.is_file() else []),
                models=["official"] + (["custom"] if cfg.custom_recognizer and cfg.custom_recognizer.is_file() else []),
                formats=["txt", "json", "csv", "html", "xlsx"], table_strategy="ruled_grid",
                limitations=["No borderless/merged-cell table reconstruction", "No searchable-PDF/DOCX export"])


@router.post("/files", status_code=201, response_model=FileOut)
def upload(request: Request, file: UploadFile = UploadField(...), session=Depends(db), user=Depends(editor)):
    cfg = request.app.state.ocr_settings
    ident = uid()
    key = f"uploads/{ident}.bin"
    path = safe_path(cfg.storage, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    size, digest = 0, hashlib.sha256()
    try:
        with path.open("xb") as target:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > cfg.max_upload_bytes:
                    raise HTTPException(413, "File exceeds upload limit")
                digest.update(chunk)
                target.write(chunk)
        media_type, page_count = inspect_media(path, cfg)
        name = (file.filename or "document").replace("\\", "/").split("/")[-1][:255]
        record = File(id=ident, owner_id=user.user_id, name=name, storage_key=key,
                      media_type=media_type, page_count=page_count, size=size, sha256=digest.hexdigest())
        session.add(record)
        audit(session, user.user_id, "file_uploaded", ident, bytes=size)
        session.commit()
        return file_view(record)
    except MediaError as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(422, str(exc))
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        file.file.close()


@router.get("/files/{file_id}", response_model=FileOut)
def get_file(file_id: str, session=Depends(db), user=Depends(current_user)):
    return file_view(owned(session.get(File, file_id), user))


@router.get("/files/{file_id}/content")
def file_content(file_id: str, request: Request, session=Depends(db), user=Depends(current_user)):
    file = owned(session.get(File, file_id), user)
    return FileResponse(safe_path(request.app.state.ocr_settings.storage, file.storage_key),
                        media_type=file.media_type, filename=file.name, content_disposition_type="inline",
                        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})


@router.post("/jobs", status_code=202, response_model=JobOut)
def create_job(body: JobCreate, request: Request, session=Depends(db), user=Depends(editor)):
    file = owned(session.get(File, body.file_id), user)
    cfg = request.app.state.ocr_settings
    if body.mode == "handwriting" and not (cfg.handwriting_detector and cfg.handwriting_detector.is_file()):
        raise HTTPException(422, "Handwriting detector is not configured")
    if body.recognition_model == "custom" and not (cfg.custom_recognizer and cfg.custom_recognizer.is_file()):
        raise HTTPException(422, "Custom recognition model is not configured")
    pages = sorted(set(body.pages or range(1, file.page_count + 1)))
    if any(n < 1 or n > file.page_count for n in pages):
        raise HTTPException(422, "Page number out of range (1-based)")
    job_id = uid()
    changed = session.execute(update(File).where(File.id == file.id, File.active_job_id.is_(None)).values(
        active_job_id=job_id, generation=File.generation + 1))
    if not changed.rowcount:
        raise HTTPException(409, "File already has an active OCR job")
    session.refresh(file)
    # Host can enforce monthly page quota in this SAME transaction.
    request.app.state.ocr_before_enqueue(session, user, file, pages)
    options = body.model_dump(exclude={"file_id"})
    options["pages"] = pages
    job = Job(id=job_id, file_id=file.id, owner_id=file.owner_id, options=options, generation=file.generation)
    session.add(job)
    session.flush()
    session.add_all([Page(job_id=job_id, page_no=n) for n in pages])
    audit(session, user.user_id, "job_created", job_id, pages=pages)
    session.commit()
    return job_view(session, job)


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), session=Depends(db), user=Depends(current_user)):
    query = select(Job)
    if user.role != "admin":
        query = query.where(Job.owner_id == user.user_id)
    return [job_view(session, j) for j in session.scalars(query.order_by(Job.created_at.desc(), Job.id).limit(limit).offset(offset))]


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, session=Depends(db), user=Depends(current_user)):
    return job_view(session, owned(session.get(Job, job_id), user))


@router.post("/jobs/{job_id}/cancel", response_model=JobOut)
def cancel(job_id: str, session=Depends(db), user=Depends(editor)):
    job = owned(session.get(Job, job_id), user)
    changed = session.execute(update(Job).where(Job.id == job_id, Job.status.not_in(TERMINAL)).values(
        status="cancelled", lease_token=None, lease_until=None, finished_at=now()))
    if not changed.rowcount:
        raise HTTPException(409, "Job is already terminal")
    release_file(session, job)
    audit(session, user.user_id, "job_cancelled", job_id)
    session.commit()
    return job_view(session, job)


@router.post("/jobs/{job_id}/retry", status_code=202, response_model=JobOut)
def retry(job_id: str, request: Request, session=Depends(db), user=Depends(editor)):
    job = owned(session.get(Job, job_id), user)
    changed = session.execute(update(Job).where(Job.id == job_id, Job.status.in_(["failed", "partial_success"])).values(
        status="queued", attempts=0, available_at=now(), finished_at=None))
    if not changed.rowcount:
        raise HTTPException(409, "Only failed or partially successful jobs may be retried")
    file = session.get(File, job.file_id)
    changed = session.execute(update(File).where(File.id == file.id, File.active_job_id.is_(None),
        File.generation == job.generation).values(active_job_id=job_id))
    if not changed.rowcount:
        raise HTTPException(409, "File has an active or newer job; create a new job for failed pages")
    # Old successful pages may have been superseded by a newer job. Do not overwrite them on retry.
    failed = session.scalars(select(Page).where(Page.job_id == job_id, Page.status != "succeeded")).all()
    request.app.state.ocr_before_enqueue(session, user, file, [p.page_no for p in failed])
    for page in failed:
        page.status, page.error = "pending", None
    audit(session, user.user_id, "job_retried", job_id)
    session.commit()
    return job_view(session, job)


@router.get("/jobs/{job_id}/pages", response_model=list[PageOut])
def results(job_id: str, session=Depends(db), user=Depends(current_user)):
    owned(session.get(Job, job_id), user)
    return [page_view(p) for p in session.scalars(select(Page).where(Page.job_id == job_id).order_by(Page.page_no))]


@router.get("/jobs/{job_id}/pages/{page_no}", response_model=PageOut)
def get_page(job_id: str, page_no: int, session=Depends(db), user=Depends(current_user)):
    owned(session.get(Job, job_id), user)
    page = session.scalar(select(Page).where(Page.job_id == job_id, Page.page_no == page_no))
    if page is None:
        raise HTTPException(404, "Page result not found")
    return page_view(page)


@router.get("/jobs/{job_id}/pages/{page_no}/image")
def page_image(job_id: str, page_no: int, request: Request, session=Depends(db), user=Depends(current_user)):
    owned(session.get(Job, job_id), user)
    page = session.scalar(select(Page).where(Page.job_id == job_id, Page.page_no == page_no))
    if not page or page.status != "succeeded":
        raise HTTPException(404, "Page image is not available")
    return FileResponse(safe_path(request.app.state.ocr_settings.storage, page.result["image_key"]),
                        media_type="image/png", headers={"Cache-Control": "private, no-store"})


@router.patch("/jobs/{job_id}/pages/{page_no}", response_model=PageOut)
def correct(job_id: str, page_no: int, body: Correction, session=Depends(db), user=Depends(editor)):
    job = owned(session.get(Job, job_id), user)
    # Hold file row through correction + index update, so enqueue cannot race the edit.
    gate = session.execute(update(File).where(File.id == job.file_id, File.active_job_id.is_(None)).values(active_job_id=None))
    if not gate.rowcount:
        raise HTTPException(409, "Wait for active OCR job to finish before editing")
    page = session.scalar(select(Page).where(Page.job_id == job_id, Page.page_no == page_no))
    if not page or page.status != "succeeded":
        raise HTTPException(404, "Successful page result not found")
    index = session.scalar(select(TextIndex).where(TextIndex.file_id == job.file_id, TextIndex.page_no == page_no))
    if not index or index.job_id != job_id:
        raise HTTPException(409, "Page has been superseded by a newer result")
    data = dict(page.result)
    data["blocks"] = [b.model_dump() for b in body.blocks]
    data["text"] = "\n".join(b.text for b in body.blocks)
    data["corrected"] = True
    for table in data.get("tables", []):
        table["cells"] = assign_cells(table, data["blocks"], data["width"], data["height"])
    changed = session.execute(update(Page).where(Page.id == page.id, Page.revision == body.expected_revision).values(
        result=data, revision=body.expected_revision + 1))
    if not changed.rowcount:
        raise HTTPException(409, "Revision conflict; reload the page")
    session.refresh(page)
    write_index(session, job, page)
    audit(session, user.user_id, "page_corrected", job_id, page_no=page_no, revision=page.revision)
    session.commit()
    return page_view(page)


@router.get("/jobs/{job_id}/export")
def export(job_id: str, format: Literal["txt", "json", "csv", "html", "xlsx"] = "json",
           allow_partial: bool = False, session=Depends(db), user=Depends(current_user)):
    job = owned(session.get(Job, job_id), user)
    pages = session.scalars(select(Page).where(Page.job_id == job_id).order_by(Page.page_no)).all()
    good = [page_view(p) for p in pages if p.status == "succeeded"]
    if not good or (not allow_partial and (job.status != "succeeded" or len(good) != len(pages))):
        raise HTTPException(409, "Result incomplete; use allow_partial=true to export successful pages")
    data, media = export_pages(good, format)
    audit(session, user.user_id, "result_exported", job_id, format=format, pages=len(good))
    session.commit()
    return Response(data, media_type=media, headers={"Content-Disposition": f'attachment; filename="ocr-{job_id}.{format}"',
        "X-OCR-Exported-Pages": str(len(good)), "X-OCR-Total-Pages": str(len(pages)),
        "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})


@router.get("/search", response_model=SearchOut)
def search(q: str = Query(min_length=1, max_length=100), limit: int = Query(20, ge=1, le=100),
           offset: int = Query(0, ge=0), session=Depends(db), user=Depends(current_user)):
    q = q.strip()
    if not q:
        raise HTTPException(422, "Empty search query")
    query = select(TextIndex, File.name).join(File, TextIndex.file_id == File.id)
    if user.role != "admin":
        query = query.where(File.owner_id == user.user_id)
    if session.bind.dialect.name == "mysql" and len(q) >= 2:
        query = query.where(text("MATCH(pdf_text_index.content) AGAINST (:q IN NATURAL LANGUAGE MODE) > 0")).params(q=q)
        backend = "mysql_ngram"
    else:
        query = query.where(TextIndex.content.contains(q, autoescape=True))
        backend = "substring"
    rows = session.execute(query.order_by(TextIndex.updated_at.desc(), TextIndex.id).limit(limit).offset(offset)).all()
    return dict(backend=backend, items=[dict(file_id=i.file_id, file_name=name, page_no=i.page_no,
        job_id=i.job_id, revision=i.revision, snippet=i.content[max(0, i.content.find(q)-40):max(0, i.content.find(q)-40)+200]) for i, name in rows])


@router.get("/usage")
def usage(session=Depends(db), user=Depends(current_user)):
    # Always the caller's own usage, including for administrators.
    statuses = session.execute(select(Job.status, func.count()).where(Job.owner_id == user.user_id).group_by(Job.status)).all()
    count, size = session.execute(select(func.count(File.id), func.coalesce(func.sum(File.size), 0)).where(File.owner_id == user.user_id)).one()
    recognized = session.scalar(select(func.count(Page.id)).join(Job).where(Job.owner_id == user.user_id, Page.status == "succeeded"))
    return dict(files=count, storage_bytes=size, recognized_page_results=recognized, jobs_by_status=dict(statuses))


@router.get("/audit")
def audit_log(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), session=Depends(db), user=Depends(current_user)):
    query = select(Audit).where(Audit.actor_id == user.user_id).order_by(Audit.created_at.desc(), Audit.id).limit(limit).offset(offset)
    return [{k: getattr(row, k) for k in ("action", "resource_id", "detail", "created_at")} for row in session.scalars(query)]


def install(app: FastAPI, settings: Settings, before_enqueue=None):
    if len(settings.jwt_secret) < 32:
        raise ValueError("Set OCR_JWT_SECRET to a private random value of at least 32 characters")
    engine, sessions = database(settings)
    app.state.ocr_settings, app.state.ocr_engine, app.state.ocr_sessions = settings, engine, sessions
    app.state.ocr_before_enqueue = before_enqueue or (lambda session, user, file, pages: None)
    app.include_router(router)


def create_app(settings: Settings | None = None):
    @asynccontextmanager
    async def lifespan(app):
        yield
        app.state.ocr_engine.dispose()
    app = FastAPI(title="PDF 系统 OCR 独立模块", version="1.0.0", lifespan=lifespan)
    install(app, settings or Settings())
    return app
