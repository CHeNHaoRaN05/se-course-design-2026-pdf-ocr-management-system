"""操作日志（负责人：甲；各线调用）。"""
from ..models import AuditLog, now


def audit(session, actor_id: str, action: str, resource_id: str, **detail) -> None:
    session.add(AuditLog(actor_id=actor_id, action=action, resource_id=resource_id, detail=detail))
