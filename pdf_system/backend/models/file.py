"""文件、标签（负责人：乙）。

本表是文件事实来源；OCR 模块的 ocr_files 只是适配层镜像（契约 C2）。
"""
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, now, uid

# 多对多关联表属于 Core 层，只能用 Column，不能用 mapped_column
file_tags = Table(
    "file_tags",
    Base.metadata,
    Column("file_id", String(32), ForeignKey("files.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", String(32), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class File(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(255))
    folder: Mapped[str] = mapped_column(String(255), default="/")  # 分类：目录路径
    storage_key: Mapped[str] = mapped_column(String(100))
    media_type: Mapped[str] = mapped_column(String(40))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    size: Mapped[int] = mapped_column(Integer)
    page_count: Mapped[int] = mapped_column(Integer, default=1)
    version: Mapped[int] = mapped_column(Integer, default=1)  # 合并/拆分/替换产生新版本
    replaced_from: Mapped[str | None] = mapped_column(String(32), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # 软删除=回收站
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    tags: Mapped[list["Tag"]] = relationship(secondary=file_tags, lazy="selectin")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(64))
