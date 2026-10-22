"""书签与批注（负责人：乙）。"""
from datetime import datetime
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, now, uid


class Bookmark(Base):
    __tablename__ = "bookmarks"
    __table_args__ = (UniqueConstraint("file_id", "owner_id", "page_no"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    file_id: Mapped[str] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), index=True)
    owner_id: Mapped[str] = mapped_column(String(32), index=True)
    page_no: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Annotation(Base):
    """kind: highlight / note / ink；payload 存归一化矩形与文本，坐标口径与 OCR bbox 一致。"""
    __tablename__ = "annotations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    file_id: Mapped[str] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), index=True)
    owner_id: Mapped[str] = mapped_column(String(32), index=True)
    page_no: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16), default="note")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
