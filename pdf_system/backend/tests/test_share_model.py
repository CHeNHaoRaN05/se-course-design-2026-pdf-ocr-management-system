"""ShareLink 模型测试（甲，阶段 0 schema 验收）。

只用 SQLAlchemy，不依赖 FastAPI / Paddle，可在任意装了 SQLAlchemy 的环境跑。
验收点：建表列齐全、字段默认值、默认令牌生成、FK 级联删除。
"""
import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import Session

from backend.models import Base, File, ShareLink


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    # SQLite 默认不强制外键，开启才能验证 ondelete=CASCADE
    @event.listens_for(eng, "connect")
    def _fk(dbapi_con, con_record):
        dbapi_con.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    return eng


def _make_file(session: Session, owner_id: str = "u1") -> File:
    f = File(owner_id=owner_id, name="a.pdf", folder="/", storage_key="k",
             media_type="application/pdf", sha256="x", size=10)
    session.add(f)
    session.flush()
    return f


def test_share_links_table_exists(engine):
    cols = {c["name"] for c in inspect(engine).get_columns("share_links")}
    assert {"id", "file_id", "owner_id", "token", "expires_at",
            "access_code", "allow_download", "visit_count", "created_at"} <= cols


def test_share_link_defaults_and_token(engine):
    with Session(engine) as s:
        f = _make_file(s)
        link = ShareLink(file_id=f.id, owner_id="u1")
        s.add(link)
        s.commit()
        assert link.allow_download is True
        assert link.visit_count == 0
        assert link.token  # 默认 uid() 生成，非空
        got = s.get(ShareLink, link.id)
        assert got is not None


def test_file_cascade_deletes_share_links(engine):
    with Session(engine) as s:
        f = _make_file(s)
        s.add(ShareLink(file_id=f.id, owner_id="u1"))
        s.commit()
        s.delete(f)
        s.commit()
    with Session(engine) as s:
        assert s.query(ShareLink).count() == 0
