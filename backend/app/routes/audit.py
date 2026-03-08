"""Audit routes."""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.db.database import get_db
from app.db.models import AuditEvent

router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditResponse(BaseModel):
    id: int
    timestamp: datetime
    username: Optional[str]
    action: str
    target: Optional[str]
    router_id: Optional[int]
    method_used: Optional[str]
    result: Optional[str]
    error_message: Optional[str]

    class Config:
        from_attributes = True


@router.get("", response_model=List[AuditResponse])
async def list_audit_events(
    limit: int = 100,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_admin),
):
    events = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(limit).all()
    return events
