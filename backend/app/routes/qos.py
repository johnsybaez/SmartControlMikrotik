"""Rutas para gestiÃ³n de QoS (Simple Queues)"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.db.database import get_db
from app.db.models import Device, Router, Plan, PlanAssignment
from app.core.security import require_admin
from app.core.logging import get_logger
from app.mikrotik.client import MikroTikClient

logger = get_logger(__name__)
router = APIRouter(prefix="/qos", tags=["QoS"])


class QueueCreate(BaseModel):
    router_id: int
    name: str
    target: str  # IP address
    max_limit_download: int  # bps
    max_limit_upload: int  # bps
    comment: Optional[str] = None


class QueueResponse(BaseModel):
    id: str
    name: str
    target: str
    max_limit: str
    comment: Optional[str]


class AssignPlanRequest(BaseModel):
    device_id: int
    plan_id: int


@router.get("/queues/{router_id}", response_model=List[QueueResponse])
async def list_queues(
    router_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Listar todas las simple queues de un router"""
    router_obj = db.query(Router).filter(Router.id == router_id).first()
    if not router_obj:
        raise HTTPException(status_code=404, detail="Router no encontrado")
    
    try:
        client = MikroTikClient(
            host=router_obj.host,
            username=router_obj.username,
            password=router_obj.password,
            api_port=router_obj.api_port,
            ssh_port=router_obj.ssh_port,
            use_ssl=router_obj.use_ssl
        )
        
        queues = await client.get_simple_queues()
        
        result = []
        for queue in queues:
            result.append({
                "id": queue.get(".id", ""),
                "name": queue.get("name", ""),
                "target": queue.get("target", ""),
                "max_limit": queue.get("max-limit", ""),
                "comment": queue.get("comment", "")
            })
        
        return result
        
    except Exception as e:
        logger.error("list_queues_failed", router_id=router_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener queues: {str(e)}"
        )


@router.post("/queues", response_model=dict)
async def create_queue(
    queue_data: QueueCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Crear una simple queue en MikroTik"""
    router_obj = db.query(Router).filter(Router.id == queue_data.router_id).first()
    if not router_obj:
        raise HTTPException(status_code=404, detail="Router no encontrado")
    
    try:
        client = MikroTikClient(
            host=router_obj.host,
            username=router_obj.username,
            password=router_obj.password,
            api_port=router_obj.api_port,
            ssh_port=router_obj.ssh_port,
            use_ssl=router_obj.use_ssl
        )
        
        # Formato: upload/download
        max_limit = f"{queue_data.max_limit_upload}/{queue_data.max_limit_download}"
        
        queue_id = await client.add_simple_queue(
            name=queue_data.name,
            target=queue_data.target,
            max_limit=max_limit,
            comment=queue_data.comment
        )
        
        logger.info(
            "queue_created",
            router_id=queue_data.router_id,
            queue_name=queue_data.name,
            user=current_user["username"]
        )
        
        return {
            "message": "Queue creada exitosamente",
            "queue_id": queue_id,
            "name": queue_data.name
        }
        
    except Exception as e:
        logger.error("create_queue_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear queue: {str(e)}"
        )


@router.delete("/queues/{router_id}/{queue_id}")
async def delete_queue(
    router_id: int,
    queue_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Eliminar una simple queue de MikroTik"""
    router_obj = db.query(Router).filter(Router.id == router_id).first()
    if not router_obj:
        raise HTTPException(status_code=404, detail="Router no encontrado")
    
    try:
        client = MikroTikClient(
            host=router_obj.host,
            username=router_obj.username,
            password=router_obj.password,
            api_port=router_obj.api_port,
            ssh_port=router_obj.ssh_port,
            use_ssl=router_obj.use_ssl
        )
        
        await client.remove_simple_queue(queue_id)
        
        logger.info(
            "queue_deleted",
            router_id=router_id,
            queue_id=queue_id,
            user=current_user["username"]
        )
        
        return {"message": "Queue eliminada exitosamente"}
        
    except Exception as e:
        logger.error("delete_queue_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar queue: {str(e)}"
        )


@router.post("/assign-plan", response_model=dict)
async def assign_plan_to_device(
    assignment: AssignPlanRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Asignar un plan de servicio a un dispositivo y crear/actualizar queue"""
    device = db.query(Device).filter(Device.id == assignment.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    plan = db.query(Plan).filter(Plan.id == assignment.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    
    router_obj = db.query(Router).filter(Router.id == device.router_id).first()
    if not router_obj:
        raise HTTPException(status_code=404, detail="Router no encontrado")
    
    try:
        client = MikroTikClient(
            host=router_obj.host,
            username=router_obj.username,
            password=router_obj.password,
            api_port=router_obj.api_port,
            ssh_port=router_obj.ssh_port,
            use_ssl=router_obj.use_ssl
        )
        
        # Nombre de la queue
        queue_name = f"QoS-{device.hostname or device.mac}"
        comment = f"SmartBJPortal - Plan: {plan.name}"
        
        # Verificar si ya existe una queue para este dispositivo
        existing_queues = await client.get_simple_queues()
        existing_queue = None
        for q in existing_queues:
            if device.ip in q.get("target", ""):
                existing_queue = q
                break
        
        # Formato: upload/download
        max_limit = f"{plan.upload_limit}/{plan.download_limit}"
        
        if existing_queue:
            # Actualizar queue existente
            await client.update_simple_queue(
                queue_id=existing_queue[".id"],
                max_limit=max_limit,
                comment=comment
            )
            action = "actualizada"
        else:
            # Crear nueva queue
            await client.add_simple_queue(
                name=queue_name,
                target=f"{device.ip}/32",
                max_limit=max_limit,
                comment=comment
            )
            action = "creada"
        
        # Registrar asignaciÃ³n en BD
        existing_assignment = db.query(PlanAssignment).filter(
            PlanAssignment.device_id == device.id
        ).first()
        
        if existing_assignment:
            existing_assignment.plan_id = plan.id
        else:
            assignment_record = PlanAssignment(
                device_id=device.id,
                plan_id=plan.id
            )
            db.add(assignment_record)
        
        device.current_plan_id = plan.id
        db.commit()
        
        logger.info(
            "plan_assigned",
            device_id=device.id,
            plan_id=plan.id,
            action=action,
            user=current_user["username"]
        )
        
        return {
            "message": f"Plan asignado y queue {action} exitosamente",
            "device": device.hostname or device.mac,
            "plan": plan.name,
            "download_limit": plan.download_limit,
            "upload_limit": plan.upload_limit
        }
        
    except Exception as e:
        logger.error("assign_plan_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Error al asignar plan: {str(e)}"
        )


@router.delete("/unassign-plan/{device_id}")
async def unassign_plan_from_device(
    device_id: int,
    remove_queue: bool = True,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Desasignar plan de un dispositivo y opcionalmente eliminar queue"""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    if remove_queue:
        router_obj = db.query(Router).filter(Router.id == device.router_id).first()
        if router_obj:
            try:
                client = MikroTikClient(
                    host=router_obj.host,
                    username=router_obj.username,
                    password=router_obj.password,
                    api_port=router_obj.api_port,
                    ssh_port=router_obj.ssh_port,
                    use_ssl=router_obj.use_ssl
                )
                
                # Buscar y eliminar queue
                queues = await client.get_simple_queues()
                for q in queues:
                    if device.ip in q.get("target", ""):
                        await client.remove_simple_queue(q[".id"])
                        break
            except Exception as e:
                logger.warning("queue_removal_failed", device_id=device_id, error=str(e))
    
    # Eliminar asignaciÃ³n de BD
    assignment = db.query(PlanAssignment).filter(
        PlanAssignment.device_id == device_id
    ).first()
    if assignment:
        db.delete(assignment)
    
    device.current_plan_id = None
    db.commit()
    
    logger.info("plan_unassigned", device_id=device_id, user=current_user["username"])
    
    return {"message": "Plan desasignado exitosamente"}
