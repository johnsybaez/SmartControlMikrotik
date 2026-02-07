"""Rutas para auditoría"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.db.database import get_db
from app.db.models import AuditEvent
from app.core.security import require_admin

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
    payload: dict = Depends(require_admin)
):
    events = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(limit).all()
    return events