from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def now():
    # Store UTC without tzinfo for consistent MySQL DATETIME / SQLite semantics.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def uid():
    return uuid4().hex


class Base(DeclarativeBase):
    pass


class File(Base):
    __tablename__ = "ocr_files"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(100))
    media_type: Mapped[str] = mapped_column(String(40))
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    page_count: Mapped[int] = mapped_column(Integer)
    active_job_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    generation: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Job(Base):
    __tablename__ = "ocr_jobs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    file_id: Mapped[str] = mapped_column(ForeignKey("ocr_files.id"), index=True)
    generation: Mapped[int] = mapped_column(Integer)
    owner_id: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(24), default="queued")
    options: Mapped[dict] = mapped_column(JSON)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_token: Mapped[str | None] = mapped_column(String(32), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    available_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    __table_args__ = (Index("ix_ocr_queue", "status", "available_at", "lease_until"),)


class Page(Base):
    __tablename__ = "ocr_pages"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    job_id: Mapped[str] = mapped_column(ForeignKey("ocr_jobs.id"), index=True)
    page_no: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    revision: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(String(80), nullable=True)
    __table_args__ = (UniqueConstraint("job_id", "page_no"),)


class TextIndex(Base):
    __tablename__ = "pdf_text_index"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    file_id: Mapped[str] = mapped_column(ForeignKey("ocr_files.id"), index=True)
    page_no: Mapped[int] = mapped_column(Integer)
    job_id: Mapped[str] = mapped_column(ForeignKey("ocr_jobs.id"))
    revision: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text().with_variant(LONGTEXT, "mysql"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    __table_args__ = (UniqueConstraint("file_id", "page_no"),)


# Only MySQL gets the ngram index; SQLite deliberately uses substring search.
Index("ft_pdf_text_content", TextIndex.content, mysql_prefix="FULLTEXT", mysql_with_parser="ngram").ddl_if(dialect="mysql")


class Audit(Base):
    __tablename__ = "ocr_audit_log"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    actor_id: Mapped[str] = mapped_column(String(128), index=True)
    action: Mapped[str] = mapped_column(String(40))
    resource_id: Mapped[str] = mapped_column(String(32))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


def database(settings):
    settings.storage.mkdir(parents=True, exist_ok=True)
    # Default URL is resolved against module workspace rather than caller cwd.
    url = settings.database_url
    if url == "sqlite:///./ocr_data/dev.sqlite3":
        url = "sqlite:///" + (settings.storage / "dev.sqlite3").as_posix()
    kwargs = {"connect_args": {"check_same_thread": False, "timeout": 30}} if url.startswith("sqlite:") else {"pool_pre_ping": True}
    engine = create_engine(url, **kwargs)
    return engine, sessionmaker(engine, expire_on_commit=False)


def audit(session, actor, action, resource, **detail):
    session.add(Audit(actor_id=actor, action=action, resource_id=resource, detail=detail))

