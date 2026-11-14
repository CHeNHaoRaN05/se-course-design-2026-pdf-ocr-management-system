"""Read-only administrative audit history (01 line review required)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...core.database import get_session
from ...core.principal import Principal, require_admin
from ...models import AuditLog

router = APIRouter(prefix="/audit", tags=["01 审计"])


@router.get("")
def audit_history(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=10000),
                  session: Session = Depends(get_session), admin: Principal = Depends(require_admin)):
    query = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id).limit(limit).offset(offset)
    return [{k: getattr(row, k) for k in ("id", "actor_id", "action", "resource_id", "detail", "created_at")}
            for row in session.scalars(query)]
