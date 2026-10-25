"""分享与协作服务（负责人：甲，FR-SHR-01/02/03）。

设计要点：
· 分享不复制文件实体，被分享者只读；owner 用 JWT 管理，被分享者凭 token 旁路访问。
· 旁路访问走 core.principal.share_access，不改 resolve_principal 主路径。
"""
from datetime import datetime

from sqlalchemy import select

from ...core.audit import audit
from ...core.errors import bad_request, not_found
from ...core.principal import owned_file
from ...models import File, ShareLink, now


def create_share(session, user, *, file_id: str, expires_at: datetime | None,
                 access_code: str | None, allow_download: bool) -> ShareLink:
    # 只有文件所有者（或管理员）能为文件创建分享
    owned_file(session, file_id, user)
    if expires_at is not None and expires_at <= now():
        raise bad_request("expires_at_must_be_future")
    link = ShareLink(file_id=file_id, owner_id=user.user_id, expires_at=expires_at,
                     access_code=access_code, allow_download=allow_download)
    session.add(link)
    session.flush()
    audit(session, user.user_id, "share_created", link.id, file_id=file_id)
    return link


def _owner_link(session, user, share_id: str) -> ShareLink:
    link = session.get(ShareLink, share_id)
    if link is None or (link.owner_id != user.user_id and not user.is_admin):
        raise not_found()
    return link


def list_shares(session, user) -> list[ShareLink]:
    statement = (select(ShareLink).where(ShareLink.owner_id == user.user_id)
                 .order_by(ShareLink.created_at.desc()))
    return list(session.scalars(statement).all())


def get_share(session, user, share_id: str) -> ShareLink:
    return _owner_link(session, user, share_id)


def cancel_share(session, user, share_id: str) -> None:
    """FR-SHR-02：取消分享 = 删除分享链接行。"""
    link = _owner_link(session, user, share_id)
    session.delete(link)
    audit(session, user.user_id, "share_revoked", share_id)


def share_stats(session, user, share_id: str) -> ShareLink:
    """FR-SHR-03：访问统计数据源（visit_count 等）。"""
    return _owner_link(session, user, share_id)


def shared_file(session, link: ShareLink) -> File:
    """被分享文件必须存在且未被删除（回收站）。"""
    record = session.get(File, link.file_id)
    if record is None or record.deleted_at is not None:
        raise not_found()
    return record
