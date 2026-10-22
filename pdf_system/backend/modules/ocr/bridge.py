"""OCR 适配层：把主系统 files 行镜像为 ocr_files 行（负责人：丙，契约 C2）。

设计前提（W4 已定）：
  1. 主系统 files 是文件事实来源，ocr_files 只是镜像；
  2. 两边共用同一个存储目录，因此 storage_key 直接复用；
  3. 镜像行使用**与主文件相同的 id**，OCR 建任务时 file_id 无需转换。
"""
from sqlalchemy import select

from ...models import File

_ready = False


def set_ready(value: bool) -> None:
    """由 mount_ocr 在挂载成功/失败时设置；决定适配层是否可用。"""
    global _ready
    _ready = value


def is_ready() -> bool:
    return _ready


def ensure_ocr_file(session, file: File):
    """幂等写入/更新镜像行。OCR 未挂载（或表未建立）时静默跳过。"""
    if not _ready:
        return None
    from ocr_service.db import File as OcrFile

    row = session.get(OcrFile, file.id)
    if row is None:
        row = OcrFile(id=file.id, owner_id=file.owner_id, name=file.name, storage_key=file.storage_key,
                      media_type=file.media_type, sha256=file.sha256, size=file.size, page_count=file.page_count)
        session.add(row)
        session.flush()
        return row
    row.owner_id = file.owner_id
    row.name = file.name
    row.storage_key = file.storage_key
    row.media_type = file.media_type
    row.sha256 = file.sha256
    row.size = file.size
    row.page_count = file.page_count
    return row


def ocr_file_missing(session, file_id: str) -> bool:
    from ocr_service.db import File as OcrFile
    return session.get(OcrFile, file_id) is None


def active_job_id(session, file_id: str) -> str | None:
    from ocr_service.db import File as OcrFile
    row = session.get(OcrFile, file_id)
    return row.active_job_id if row else None


def latest_job(session, file_id: str):
    from ocr_service.db import Job
    return session.scalar(select(Job).where(Job.file_id == file_id).order_by(Job.created_at.desc(), Job.id))
