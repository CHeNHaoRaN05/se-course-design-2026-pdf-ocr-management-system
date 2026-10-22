"""所有模型的公共定义（负责人：甲）。"""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import DeclarativeBase


def now() -> datetime:
    """统一存 UTC 且不带时区，MySQL DATETIME 与 SQLite 语义一致。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def uid() -> str:
    return uuid4().hex


class Base(DeclarativeBase):
    pass
