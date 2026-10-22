"""月度识别配额（负责人：甲的表，丙的 OCR 钩子写入）。

reserve：任务入队时预留（在 OCR 入队的同一事务内锁定行）
settle ：任务终态时把 reserved 转为 used；取消/失败时退回 reserved
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, now, uid


def current_month(at=None) -> str:
    return (at or now()).strftime("%Y-%m")


class QuotaAccount(Base):
    __tablename__ = "quota_accounts"

    user_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    month: Mapped[str] = mapped_column(String(7), primary_key=True)
    pages_reserved: Mapped[int] = mapped_column(Integer, default=0)
    pages_used: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class QuotaLedger(Base):
    """配额流水：便于对账与"取消退款"审计。"""
    __tablename__ = "quota_ledger"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    month: Mapped[str] = mapped_column(String(7))
    pages: Mapped[int] = mapped_column(Integer)  # 正数=占用，负数=退还
    reason: Mapped[str] = mapped_column(String(40))
    ref_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
