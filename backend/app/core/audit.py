"""Audit logging utilities"""
from typing import Optional, Dict, Any
from app.db.models import AuditEvent


def record_audit_event(
    db,
    user_id: Optional[int],
    username: Optional[str],
    action: str,
    target: Optional[str] = None,
    router_id: Optional[int] = None,
    method_used: Optional[str] = None,
    result: Optional[str] = "success",
    error_message: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None
):
    event = AuditEvent(
        user_id=user_id,
        username=username,
        action=action,
        target=target,
        router_id=router_id,
        method_used=method_used,
        result=result,
        error_message=error_message,
        extra_data=extra_data
    )
    db.add(event)
    db.commit()
    return event