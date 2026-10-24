"""吊销的 JWT（负责人：甲，支撑 FR-USER-03/04/05 登出 / 刷新 / 改密码）。

黑名单只记 jti 与过期时间；resolve_principal 在每个请求里用 session.get 判断存在性。
过期行可由定时任务清理（本系统规模小，暂不强制）。
"""
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, now


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime] = mapped_column(DateTime, default=now)
