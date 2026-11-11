from datetime import date, datetime, time, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...core.database import get_session
from ...core.principal import Principal, require_admin
from ...models.audit import AuditLog
from ...core.errors import bad_request

router = APIRouter(prefix="/audit", tags=["01 审计查询"])


@router.get("")
def listing(actor_id: str | None = Query(None, max_length=128), action: str | None = Query(None, max_length=40),
            date_from: date | None = None, date_to: date | None = None,
            limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=1_000_000),
            session: Session = Depends(get_session), admin: Principal = Depends(require_admin)):
    statement = select(AuditLog)
    if actor_id:
        statement = statement.where(AuditLog.actor_id == actor_id)
    if action:
        statement = statement.where(AuditLog.action == action)
    if date_from and date_to and date_from > date_to:
        raise bad_request("开始日期不能晚于结束日期")
    if date_to == date.max:
        raise bad_request("结束日期必须早于 9999-12-31")
    if date_from:
        statement = statement.where(AuditLog.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        statement = statement.where(AuditLog.created_at < datetime.combine(date_to + timedelta(days=1), time.min))
    rows = session.scalars(statement.order_by(AuditLog.created_at.desc(), AuditLog.id).limit(limit).offset(offset))
    return [dict(id=row.id, actor_id=row.actor_id, action=row.action, resource_id=row.resource_id,
                 created_at=row.created_at) for row in rows]
