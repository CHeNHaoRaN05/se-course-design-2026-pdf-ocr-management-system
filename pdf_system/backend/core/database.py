"""数据库引擎与会话（负责人：甲）。

主系统与 OCR 模块共用同一个 engine；OCR 模块自带 sessionmaker，
两条线在同一个库、不同的 DeclarativeBase 上工作，互不干扰。
"""
from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings


def build_engine(settings: Settings):
    kwargs = {"future": True, "echo": settings.database_echo}
    if settings.database_url.startswith("sqlite:"):
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
    else:
        kwargs["pool_pre_ping"] = True
        kwargs["pool_recycle"] = 1800
    return create_engine(settings.database_url, **kwargs)


def build_session_factory(engine):
    return sessionmaker(engine, expire_on_commit=False, class_=Session)


def get_session(request: Request) -> Iterator[Session]:
    """FastAPI 依赖：每请求一个会话，提交由各 service 自行控制。"""
    with request.app.state.sessions() as session:
        yield session
