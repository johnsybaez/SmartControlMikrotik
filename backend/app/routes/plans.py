"""Rutas para gestión de planes de servicio"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.db.database import get_db
from app.db.models import Plan
from app.core.security import require_admin
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/plans", tags=["Plans"])


class PlanCreate(BaseModel):
    name: str
    description: Optional[str] = None
    download_limit: str
    upload_limit: str
    burst_download: Optional[str] = None
    burst_upload: Optional[str] = None
    burst_threshold: Optional[str] = None
    burst_time: Optional[str] = None
    priority: Optional[int] = 8
    is_active: Optional[bool] = True


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    download_limit: Optional[str] = None
    upload_limit: Optional[str] = None
    burst_download: Optional[str] = None
    burst_upload: Optional[str] = None
    burst_threshold: Optional[str] = None
    burst_time: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class PlanResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    download_limit: str
    upload_limit: str
    burst_download: Optional[str]
    burst_upload: Optional[str]
    burst_threshold: Optional[str]
    burst_time: Optional[str]
    priority: int
    is_active: bool
    
    class Config:
        from_attributes = True


@router.get("", response_model=List[PlanResponse])
async def list_plans(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Listar planes de servicio"""
    query = db.query(Plan)
    if active_only:
        query = query.filter(Plan.is_active == True)
    plans = query.all()
    logger.info("plans_listed", count=len(plans), user=current_user.get("sub", "unknown"))
    return plans


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Obtener un plan específico"""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    return plan


@router.post("", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    plan_data: PlanCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Crear un nuevo plan de servicio"""
    existing = db.query(Plan).filter(Plan.name == plan_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un plan con ese nombre")
    
    plan = Plan(
        name=plan_data.name,
        description=plan_data.description,
        download_limit=plan_data.download_limit,
        upload_limit=plan_data.upload_limit,
        burst_download=plan_data.burst_download,
        burst_upload=plan_data.burst_upload,
        burst_threshold=plan_data.burst_threshold,
        burst_time=plan_data.burst_time,
        priority=plan_data.priority or 8,
        is_active=plan_data.is_active
    )
    
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    logger.info("plan_created", plan_id=plan.id, name=plan.name, user=current_user.get("sub", "unknown"))
    return plan


@router.put("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: int,
    plan_data: PlanUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Actualizar un plan existente"""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    
    if plan_data.name is not None:
        plan.name = plan_data.name
    if plan_data.description is not None:
        plan.description = plan_data.description
    if plan_data.download_limit is not None:
        plan.download_limit = plan_data.download_limit
    if plan_data.upload_limit is not None:
        plan.upload_limit = plan_data.upload_limit
    if plan_data.burst_download is not None:
        plan.burst_download = plan_data.burst_download
    if plan_data.burst_upload is not None:
        plan.burst_upload = plan_data.burst_upload
    if plan_data.burst_threshold is not None:
        plan.burst_threshold = plan_data.burst_threshold
    if plan_data.burst_time is not None:
        plan.burst_time = plan_data.burst_time
    if plan_data.priority is not None:
        plan.priority = plan_data.priority
    if plan_data.is_active is not None:
        plan.is_active = plan_data.is_active
    
    db.commit()
    db.refresh(plan)
    
    logger.info("plan_updated", plan_id=plan.id, user=current_user.get("sub", "unknown"))
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Eliminar un plan de servicio"""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    
    db.delete(plan)
    db.commit()
    
    logger.info("plan_deleted", plan_id=plan_id, user=current_user.get("sub", "unknown"))
    return None
