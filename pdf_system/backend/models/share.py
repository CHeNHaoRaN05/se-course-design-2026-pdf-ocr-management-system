"""分享链接（负责人：甲）。

支撑 FR-SHR-01/02/03：生成分享链接（有效期、提取码、是否允许下载）、
取消分享、访问统计。分享不复制文件实体，被分享者只读；文件被彻底删除时
级联清理其分享链接（ondelete=CASCADE）。
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, now, uid


class ShareLink(Base):
    __tablename__ = "share_links"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    file_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("files.id", ondelete="CASCADE"), index=True
    )
    owner_id: Mapped[str] = mapped_column(String(32), index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, default=uid)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # null=永不过期
    access_code: Mapped[str | None] = mapped_column(String(32), nullable=True)  # null=无需提取码
    allow_download: Mapped[bool] = mapped_column(Boolean, default=True)
    visit_count: Mapped[int] = mapped_column(Integer, default=0)  # 访问统计计数器
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
