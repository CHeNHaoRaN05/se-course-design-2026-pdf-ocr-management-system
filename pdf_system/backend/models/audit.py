"""全系统操作日志（负责人：甲；OCR 模块自身的 ocr_audit_log 由丙汇总到统计接口）。"""
from datetime import datetime
from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, now, uid


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    actor_id: Mapped[str] = mapped_column(String(128), index=True)
    action: Mapped[str] = mapped_column(String(40), index=True)
    resource_id: Mapped[str] = mapped_column(String(32))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
