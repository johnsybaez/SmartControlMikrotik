"""Rutas para gestión de dispositivos"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.db.database import get_db
from app.db.models import Device, Router, AddressListEntry
from app.mikrotik.client import MikroTikClient
from app.core.security import require_admin_or_operator
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/devices", tags=["Devices"])


class DeviceResponse(BaseModel):
    id: int
    router_id: int
    mac: str
    ip: Optional[str]
    hostname: Optional[str]
    comment: Optional[str]
    state: str
    server: Optional[str]
    last_seen: Optional[datetime]
    internet_status: Optional[str] = None  # "permitted", "blocked", "unknown"

    class Config:
        from_attributes = True


@router.get("", response_model=List[DeviceResponse])
async def list_devices(
    router_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)
):
    """Listar todos los dispositivos con su estado de internet"""
    query = db.query(Device)
    if router_id:
        query = query.filter(Device.router_id == router_id)

    permitted_set = None
    limited_set = None
    blocked_set = None
    if router_id:
        router_obj = db.query(Router).filter(Router.id == router_id).first()
        if not router_obj:
            raise HTTPException(status_code=404, detail="Router no encontrado")

        try:
            with MikroTikClient(
                host=router_obj.host,
                username=router_obj.username,
                password=router_obj.password,
                api_port=router_obj.api_port,
                ssh_port=router_obj.ssh_port,
                use_ssl=router_obj.use_ssl,
                ssl_verify=router_obj.ssl_verify,
                timeout=router_obj.timeout
            ) as client:
                permitted_entries = client.get_address_list("INET_PERMITIDO")
                limited_entries = client.get_address_list("INET_LIMITADO")
                blocked_entries = client.get_address_list("INET_BLOQUEADO")

            permitted_set = {
                entry.get("address")
                for entry in permitted_entries
                if entry.get("address")
            }
            limited_set = {
                entry.get("address")
                for entry in limited_entries
                if entry.get("address")
            }
            blocked_set = {
                entry.get("address")
                for entry in blocked_entries
                if entry.get("address")
            }
        except Exception as e:
            logger.warning("address_list_live_failed", router_id=router_id, error=str(e))
    
    devices = query.all()
    
    # Obtener estados de internet desde address-lists
    result = []
    removed_count = 0
    for device in devices:
        device_dict = {
            "id": device.id,
            "router_id": device.router_id,
            "mac": device.mac,
            "ip": device.ip,
            "hostname": device.hostname,
            "comment": device.comment,
            "state": device.state,
            "server": device.server,
            "last_seen": device.last_seen,
            "internet_status": "unknown"
        }
        
        if device.ip:
            if permitted_set is not None and limited_set is not None and blocked_set is not None:
                if device.ip in permitted_set:
                    device_dict["internet_status"] = "permitted"
                elif device.ip in limited_set:
                    device_dict["internet_status"] = "limited"
                elif device.ip in blocked_set:
                    device_dict["internet_status"] = "blocked"
                elif device.state == "bound":
                    device_dict["internet_status"] = "pending"
                else:
                    db.delete(device)
                    removed_count += 1
                    continue
            else:
                # Check address lists from DB as fallback
                permitted = db.query(AddressListEntry).filter(
                    AddressListEntry.router_id == device.router_id,
                    AddressListEntry.list_name == "INET_PERMITIDO",
                    AddressListEntry.address == device.ip
                ).first()

                limited = db.query(AddressListEntry).filter(
                    AddressListEntry.router_id == device.router_id,
                    AddressListEntry.list_name == "INET_LIMITADO",
                    AddressListEntry.address == device.ip
                ).first()

                blocked = db.query(AddressListEntry).filter(
                    AddressListEntry.router_id == device.router_id,
                    AddressListEntry.list_name == "INET_BLOQUEADO",
                    AddressListEntry.address == device.ip
                ).first()

                if permitted:
                    device_dict["internet_status"] = "permitted"
                elif limited:
                    device_dict["internet_status"] = "limited"
                elif blocked:
                    device_dict["internet_status"] = "blocked"
                elif device.state == "bound":
                    device_dict["internet_status"] = "pending"
                else:
                    db.delete(device)
                    removed_count += 1
                    continue
        else:
            if device.state != "bound":
                db.delete(device)
                removed_count += 1
                continue
        
        result.append(device_dict)
    
    if removed_count:
        db.commit()
        logger.info("devices_removed", count=removed_count, user=current_user.get("sub", "unknown"))
    logger.info("devices_listed", count=len(result), user=current_user.get("sub", "unknown"))
    return result


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)
):
    """Obtener un dispositivo por ID"""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    # Determinar estado de internet
    internet_status = "unknown"
    if device.ip:
        permitted = db.query(AddressListEntry).filter(
            AddressListEntry.router_id == device.router_id,
            AddressListEntry.list_name == "INET_PERMITIDO",
            AddressListEntry.address == device.ip
        ).first()

        limited = db.query(AddressListEntry).filter(
            AddressListEntry.router_id == device.router_id,
            AddressListEntry.list_name == "INET_LIMITADO",
            AddressListEntry.address == device.ip
        ).first()
        
        blocked = db.query(AddressListEntry).filter(
            AddressListEntry.router_id == device.router_id,
            AddressListEntry.list_name == "INET_BLOQUEADO",
            AddressListEntry.address == device.ip
        ).first()
        
        if permitted:
            internet_status = "permitted"
        elif limited:
            internet_status = "limited"
        elif blocked:
            internet_status = "blocked"
        elif device.state == "bound":
            internet_status = "pending"
    
    return {
        "id": device.id,
        "router_id": device.router_id,
        "mac": device.mac,
        "ip": device.ip,
        "hostname": device.hostname,
        "comment": device.comment,
        "state": device.state,
        "server": device.server,
        "last_seen": device.last_seen,
        "internet_status": internet_status
    }
