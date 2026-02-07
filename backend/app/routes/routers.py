"""Rutas para gestión de routers MikroTik"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.db.database import get_db
from app.db.models import Router
from app.core.security import require_admin, require_admin_or_operator, get_current_user_payload
from app.mikrotik.client import MikroTikClient
from app.core.logging import get_logger
from datetime import datetime

logger = get_logger(__name__)
router = APIRouter(prefix="/routers", tags=["Routers"])


class RouterResponse(BaseModel):
    id: int
    name: str
    host: str
    api_port: int
    ssh_port: int
    username: str
    use_ssl: bool
    ssl_verify: bool
    timeout: int
    status: str
    description: Optional[str] = None
    last_seen: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RouterCreate(BaseModel):
    name: str
    host: str
    api_port: int = 8728
    ssh_port: int = 22
    username: str
    password: str
    use_ssl: bool = False
    ssl_verify: bool = False
    timeout: int = 10
    description: Optional[str] = None
    status: str = "active"


class TestConnectionResponse(BaseModel):
    success: bool
    method_used: str
    data: dict
    message: str


@router.get("", response_model=list[RouterResponse])
async def list_routers(
    db: Session = Depends(get_db),
    payload: dict = Depends(require_admin_or_operator)
):
    """Lista todos los routers configurados"""
    routers = db.query(Router).all()
    return routers


@router.post("", response_model=RouterResponse, status_code=status.HTTP_201_CREATED)
async def create_router(
    router_data: RouterCreate,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_admin)
):
    """Crea un nuevo router MikroTik"""
    existing_name = db.query(Router).filter(Router.name == router_data.name).first()
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un router con ese nombre"
        )

    existing_host = db.query(Router).filter(Router.host == router_data.host).first()
    if existing_host:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un router con ese host"
        )

    router_obj = Router(
        name=router_data.name,
        host=router_data.host,
        api_port=router_data.api_port,
        ssh_port=router_data.ssh_port,
        username=router_data.username,
        password=router_data.password,
        use_ssl=router_data.use_ssl,
        ssl_verify=router_data.ssl_verify,
        timeout=router_data.timeout,
        description=router_data.description,
        status=router_data.status
    )

    db.add(router_obj)
    db.commit()
    db.refresh(router_obj)

    logger.info("router_created", router_id=router_obj.id, user=payload.get("sub"))
    return router_obj


@router.get("/{router_id}", response_model=RouterResponse)
async def get_router(
    router_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_admin_or_operator)
):
    """Obtiene detalles de un router específico"""
    router_obj = db.query(Router).filter(Router.id == router_id).first()
    
    if not router_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Router no encontrado"
        )
    
    return router_obj


@router.post("/{router_id}/test", response_model=TestConnectionResponse)
async def test_router_connection(
    router_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_admin)
):
    """Prueba conexión con el router MikroTik"""
    
    # Obtener router de DB
    router_obj = db.query(Router).filter(Router.id == router_id).first()
    
    if not router_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Router no encontrado"
        )
    
    try:
        # Crear cliente MikroTik
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
            # Obtener información del sistema
            system_info = client.get_system_resource()
            
            # Actualizar last_seen en DB
            router_obj.last_seen = datetime.utcnow()
            router_obj.status = "active"
            db.commit()
            
            logger.info("router_test_success", 
                       router_id=router_id, 
                       method=client.method_used)
            
            return TestConnectionResponse(
                success=True,
                method_used=client.method_used,
                data={
                    "version": system_info.get("version", "unknown"),
                    "board_name": system_info.get("board-name", "unknown"),
                    "uptime": system_info.get("uptime", "unknown"),
                    "cpu_load": system_info.get("cpu-load", "unknown"),
                    "free_memory": system_info.get("free-memory", "unknown"),
                    "total_memory": system_info.get("total-memory", "unknown"),
                },
                message=f"Conexión exitosa vía {client.method_used}"
            )
    
    except Exception as e:
        logger.error("router_test_failed", router_id=router_id, error=str(e))
        
        # Actualizar status a error
        router_obj.status = "error"
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error conectando al router: {str(e)}"
        )


@router.get("/{router_id}/address-lists")
async def get_router_address_lists(
    router_id: int,
    list_name: Optional[str] = None,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_admin)
):
    """Obtiene address-lists del router"""
    
    router_obj = db.query(Router).filter(Router.id == router_id).first()
    
    if not router_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Router no encontrado"
        )
    
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
            entries = client.get_address_list(list_name)
            
            return {
                "success": True,
                "method_used": client.method_used,
                "total": len(entries),
                "entries": entries
            }
    
    except Exception as e:
        logger.error("get_address_lists_failed", router_id=router_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error obteniendo address-lists: {str(e)}"
        )


@router.get("/{router_id}/dhcp-leases")
async def get_router_dhcp_leases(
    router_id: int,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_admin)
):
    """Obtiene leases DHCP del router"""
    
    router_obj = db.query(Router).filter(Router.id == router_id).first()
    
    if not router_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Router no encontrado"
        )
    
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
            leases = client.get_dhcp_leases(status_filter)
            
            return {
                "success": True,
                "method_used": client.method_used,
                "total": len(leases),
                "leases": leases
            }
    
    except Exception as e:
        logger.error("get_dhcp_leases_failed", router_id=router_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error obteniendo leases DHCP: {str(e)}"
        )


@router.post("/{router_id}/sync-dhcp-leases")
async def sync_dhcp_leases(
    router_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_admin)
):
    """Sincroniza leases DHCP del router a la tabla devices"""
    from app.db.models import Device
    from datetime import datetime
    
    router_obj = db.query(Router).filter(Router.id == router_id).first()
    
    if not router_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Router no encontrado"
        )
    
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
            leases = client.get_dhcp_leases()
            
            devices_created = 0
            devices_updated = 0
            
            for lease in leases:
                mac = lease.get('mac-address', lease.get('active-mac-address'))
                ip = lease.get('active-address', lease.get('address'))
                hostname = lease.get('host-name', '')
                state = lease.get('status', 'unknown')
                server = lease.get('server', '')
                
                if not mac:
                    continue
                
                # Buscar dispositivo existente
                device = db.query(Device).filter(
                    Device.router_id == router_id,
                    Device.mac == mac
                ).first()
                
                if device:
                    # Actualizar
                    device.ip = ip
                    device.hostname = hostname or device.hostname
                    device.state = state
                    device.server = server
                    device.last_seen = datetime.utcnow()
                    devices_updated += 1
                else:
                    # Crear nuevo
                    device = Device(
                        router_id=router_id,
                        mac=mac,
                        ip=ip,
                        hostname=hostname,
                        state=state,
                        server=server,
                        last_seen=datetime.utcnow()
                    )
                    db.add(device)
                    devices_created += 1
            
            db.commit()
            
            logger.info(
                "dhcp_sync_completed",
                router_id=router_id,
                created=devices_created,
                updated=devices_updated,
                user=payload.get("sub", "unknown")
            )
            
            return {
                "success": True,
                "devices_created": devices_created,
                "devices_updated": devices_updated,
                "total_leases": len(leases)
            }
    
    except Exception as e:
        logger.error("dhcp_sync_failed", router_id=router_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error sincronizando DHCP: {str(e)}"
        )


class AddressListEntry(BaseModel):
    address: str
    comment: Optional[str] = None


@router.post("/{router_id}/address-lists/{list_name}")
async def add_to_address_list(
    router_id: int,
    list_name: str,
    entry: AddressListEntry,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_admin)
):
    """Agrega una dirección a una address-list"""
    
    router_obj = db.query(Router).filter(Router.id == router_id).first()
    
    if not router_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Router no encontrado"
        )
    
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
            result = client.add_to_address_list(list_name, entry.address, entry.comment)
            
            logger.info("address_added", 
                       router_id=router_id, 
                       list_name=list_name, 
                       address=entry.address)
            
            return {
                "success": True,
                "method_used": client.method_used,
                "message": f"Dirección {entry.address} agregada a {list_name}",
                "data": result
            }
    
    except Exception as e:
        logger.error("add_to_address_list_failed", 
                    router_id=router_id, 
                    list_name=list_name,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error agregando dirección: {str(e)}"
        )


@router.delete("/{router_id}/address-lists/{list_name}/{address}")
async def remove_from_address_list(
    router_id: int,
    list_name: str,
    address: str,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_admin)
):
    """Elimina una dirección de una address-list"""
    
    router_obj = db.query(Router).filter(Router.id == router_id).first()
    
    if not router_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Router no encontrado"
        )
    
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
            result = client.remove_from_address_list(list_name, address)
            
            logger.info("address_removed", 
                       router_id=router_id, 
                       list_name=list_name, 
                       address=address)
            
            return {
                "success": True,
                "method_used": client.method_used,
                "message": f"Dirección {address} eliminada de {list_name}",
                "data": result
            }
    
    except Exception as e:
        logger.error("remove_from_address_list_failed", 
                    router_id=router_id, 
                    list_name=list_name,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error eliminando dirección: {str(e)}"
        )


class ToggleInternetRequest(BaseModel):
    ip_address: str
    enable: bool
    comment: Optional[str] = None
    list_type: Optional[str] = "permitted"  # permitted | limited


@router.post("/{router_id}/toggle-internet")
async def toggle_device_internet(
    router_id: int,
    request: ToggleInternetRequest,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_admin_or_operator)
):
    """Habilita o deshabilita el internet de un dispositivo"""
    from app.db.models import AddressListEntry as AddressListModel
    
    router_obj = db.query(Router).filter(Router.id == router_id).first()
    
    if not router_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Router no encontrado"
        )
    
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
            comment = request.comment or f"SmartBJ Portal - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
            list_type = (request.list_type or "permitted").lower()
            target_list = "INET_LIMITADO" if list_type == "limited" else "INET_PERMITIDO"
            
            if request.enable:
                # PERMITIR/LIMITAR: Eliminar de TODAS las listas y agregar solo a la objetivo
                removed_from = []
                removed_counts = {}
                
                logger.info("allowing_device", ip=request.ip_address, target_list=target_list)
                
                # PASO 1: Eliminar COMPLETAMENTE de INET_BLOQUEADO y la otra lista permitida
                lists_to_clean = ["INET_BLOQUEADO"]
                # Si vamos a INET_PERMITIDO, limpiar INET_LIMITADO y viceversa
                if target_list == "INET_PERMITIDO":
                    lists_to_clean.append("INET_LIMITADO")
                else:
                    lists_to_clean.append("INET_PERMITIDO")
                
                for list_to_clean in lists_to_clean:
                    try:
                        count = client.remove_from_address_list(list_to_clean, request.ip_address)
                        if count > 0:
                            removed_from.append(list_to_clean)
                            removed_counts[list_to_clean] = count
                            logger.info(f"ELIMINADAS {count} entradas de {list_to_clean} para {request.ip_address}")
                    except Exception as e:
                        logger.warning(f"Error al eliminar de {list_to_clean}: {e}")
                
                # PASO 2: Verificar que NO esté en las listas bloqueadas/opuestas
                try:
                    verificacion_bloqueado = client.get_address_list("INET_BLOQUEADO")
                    still_in_bloqueado = any(e.get("address") == request.ip_address for e in verificacion_bloqueado)
                    
                    if still_in_bloqueado:
                        logger.error(f"ADVERTENCIA: {request.ip_address} AUN esta en INET_BLOQUEADO despues de eliminar!")
                except Exception as e:
                    logger.warning(f"Error verificando limpieza: {e}")
                
                # PASO 3: Eliminar duplicados de la lista objetivo si existen
                try:
                    count_target = client.remove_from_address_list(target_list, request.ip_address)
                    if count_target > 0:
                        logger.info(f"Limpiados {count_target} duplicados de {target_list}")
                except Exception as e:
                    logger.warning(f"Error limpiando duplicados de {target_list}: {e}")
                
                # PASO 4: Eliminar de DB
                deleted_count = db.query(AddressListModel).filter(
                    AddressListModel.router_id == router_id,
                    AddressListModel.list_name.in_(["INET_BLOQUEADO", "INET_PERMITIDO", "INET_LIMITADO"]),
                    AddressListModel.address == request.ip_address
                ).delete()
                
                logger.info(
                    "cleanup_complete",
                    ip=request.ip_address,
                    removed_from=removed_from,
                    removed_counts=removed_counts,
                    db_deleted=deleted_count
                )
                
                # PASO 5: Agregar SOLO a lista objetivo
                logger.info(f"Agregando {request.ip_address} a {target_list}")
                result = client.add_to_address_list(target_list, request.ip_address, comment)
                
                # PASO 6: Guardar en DB
                entry = AddressListModel(
                    router_id=router_id,
                    list_name=target_list,
                    address=request.ip_address,
                    comment=comment,
                    synced_at=datetime.utcnow()
                )
                db.add(entry)
                action = "permitido" if target_list == "INET_PERMITIDO" else "limitado"
                
                logger.info("device_allowed_successfully", ip=request.ip_address, list=target_list)
            else:
                # BLOQUEAR: Eliminar de TODAS las listas y agregar solo a bloqueados
                removed_from = []
                removed_counts = {}
                
                logger.info("blocking_device", ip=request.ip_address)
                
                # PASO 1: Eliminar COMPLETAMENTE de INET_PERMITIDO e INET_LIMITADO
                for list_to_clean in ["INET_PERMITIDO", "INET_LIMITADO"]:
                    try:
                        count = client.remove_from_address_list(list_to_clean, request.ip_address)
                        if count > 0:
                            removed_from.append(list_to_clean)
                            removed_counts[list_to_clean] = count
                            logger.info(f"ELIMINADAS {count} entradas de {list_to_clean} para {request.ip_address}")
                    except Exception as e:
                        logger.warning(f"Error al eliminar de {list_to_clean}: {e}")
                
                # PASO 2: Verificar que NO esté en INET_PERMITIDO ni INET_LIMITADO
                try:
                    verificacion_permitido = client.get_address_list("INET_PERMITIDO")
                    verificacion_limitado = client.get_address_list("INET_LIMITADO")
                    
                    still_in_permitido = any(e.get("address") == request.ip_address for e in verificacion_permitido)
                    still_in_limitado = any(e.get("address") == request.ip_address for e in verificacion_limitado)
                    
                    if still_in_permitido or still_in_limitado:
                        logger.error(f"ADVERTENCIA: {request.ip_address} AUN esta en listas permitidas despues de eliminar!")
                        if still_in_permitido:
                            logger.error(f"  - Aun en INET_PERMITIDO")
                        if still_in_limitado:
                            logger.error(f"  - Aun en INET_LIMITADO")
                except Exception as e:
                    logger.warning(f"Error verificando limpieza: {e}")
                
                # PASO 3: Eliminar duplicados de INET_BLOQUEADO si existen
                try:
                    count_bloqueado = client.remove_from_address_list("INET_BLOQUEADO", request.ip_address)
                    if count_bloqueado > 0:
                        logger.info(f"Limpiados {count_bloqueado} duplicados de INET_BLOQUEADO")
                except Exception as e:
                    logger.warning(f"Error limpiando duplicados de INET_BLOQUEADO: {e}")
                
                # PASO 4: Eliminar de DB
                deleted_count = db.query(AddressListModel).filter(
                    AddressListModel.router_id == router_id,
                    AddressListModel.list_name.in_(["INET_PERMITIDO", "INET_LIMITADO", "INET_BLOQUEADO"]),
                    AddressListModel.address == request.ip_address
                ).delete()
                
                logger.info(
                    "cleanup_complete",
                    ip=request.ip_address,
                    removed_from=removed_from,
                    removed_counts=removed_counts,
                    db_deleted=deleted_count
                )
                
                # PASO 5: Agregar SOLO a bloqueados
                logger.info(f"Agregando {request.ip_address} a INET_BLOQUEADO")
                result = client.add_to_address_list("INET_BLOQUEADO", request.ip_address, comment)
                
                # PASO 6: Guardar en DB
                entry = AddressListModel(
                    router_id=router_id,
                    list_name="INET_BLOQUEADO",
                    address=request.ip_address,
                    comment=comment,
                    synced_at=datetime.utcnow()
                )
                db.add(entry)
                action = "bloqueado"
                
                logger.info("device_blocked_successfully", ip=request.ip_address)
            
            db.commit()
            
            logger.info(
                "internet_toggled",
                router_id=router_id,
                ip=request.ip_address,
                action=action,
                user=payload.get("sub", "unknown")
            )
            
            return {
                "success": True,
                "method_used": client.method_used,
                "action": action,
                "ip_address": request.ip_address,
                "message": f"Internet {action} para {request.ip_address}"
            }
    
    except Exception as e:
        logger.error("toggle_internet_failed", 
                    router_id=router_id,
                    ip=request.ip_address,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error cambiando estado de internet: {str(e)}"
        )


@router.delete("/{router_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_router(
    router_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_admin)
):
    """Elimina un router y todos sus dispositivos asociados"""
    from app.db.models import Device, AddressListEntry, PlanAssignment, StatsSnapshot
    
    # Obtener router
    router_obj = db.query(Router).filter(Router.id == router_id).first()
    
    if not router_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Router no encontrado"
        )
    
    try:
        # Eliminar dispositivos asociados (esto también eliminará plan_assignments y traffic_stats por CASCADE)
        db.query(Device).filter(Device.router_id == router_id).delete()
        
        # Eliminar address list entries
        db.query(AddressListEntry).filter(AddressListEntry.router_id == router_id).delete()
        
        # Eliminar snapshots de estadísticas
        db.query(StatsSnapshot).filter(StatsSnapshot.router_id == router_id).delete()
        
        # Eliminar el router
        db.delete(router_obj)
        db.commit()
        
        logger.info("router_deleted", 
                   router_id=router_id, 
                   router_name=router_obj.name,
                   user=payload.get("sub"))
        
        return None
    
    except Exception as e:
        db.rollback()
        logger.error("router_delete_failed", router_id=router_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error eliminando router: {str(e)}"
        )
