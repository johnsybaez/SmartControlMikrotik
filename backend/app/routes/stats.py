"""Rutas para estadísticas del sistema"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.database import get_db
from app.db.models import Device, Plan, PlanAssignment, Router, AddressListEntry
from app.core.security import require_admin_or_operator
from app.core.logging import get_logger
from app.mikrotik.client import MikroTikClient
from typing import Dict, Any, List

logger = get_logger(__name__)
router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("/summary")
async def get_stats_summary(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)
) -> Dict[str, Any]:
    """
    Get summary statistics for dashboard.
    Returns total devices, active devices, blocked devices, total routers, and active plans.
    """
    try:
        # Count total devices
        total_devices = db.query(Device).count()
        
        # Count devices in permitted/blocked lists from MikroTik (fallback to DB)
        active_devices = 0
        blocked_devices = 0
        routers = db.query(Router).all()
        if routers:
            for router_obj in routers:
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

                    active_devices += len([e for e in permitted_entries if e.get("address")])
                    active_devices += len([e for e in limited_entries if e.get("address")])
                    blocked_devices += len([e for e in blocked_entries if e.get("address")])
                except Exception as e:
                    logger.warning("stats_live_address_list_failed", router_id=router_obj.id, error=str(e))
        else:
            # Fallback to DB if no routers configured
            active_devices = db.query(AddressListEntry).filter(
                AddressListEntry.list_name.in_(["INET_PERMITIDO", "INET_LIMITADO"])
            ).count()
            blocked_devices = db.query(AddressListEntry).filter(
                AddressListEntry.list_name == "INET_BLOQUEADO"
            ).count()
        
        # Count total routers
        total_routers = db.query(Router).count()
        
        # Count active routers
        active_routers = db.query(Router).filter(Router.status == "active").count()
        
        # Count active service plans
        active_plans = db.query(Plan).filter(Plan.is_active == True).count()
        
        # Count plan assignments
        total_assignments = db.query(PlanAssignment).count()
        
        return {
            "total_devices": total_devices,
            "active_devices": active_devices,
            "blocked_devices": blocked_devices,
            "total_routers": total_routers,
            "active_routers": active_routers,
            "active_plans": active_plans,
            "total_assignments": total_assignments
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")


@router.get("/devices-by-plan")
async def get_devices_by_plan(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)
):
    """
    Get count of devices grouped by service plan.
    """
    try:
        # Query devices by plan
        results = db.query(
            Plan.name,
            func.count(PlanAssignment.device_id).label('count')
        ).join(
            PlanAssignment, Plan.id == PlanAssignment.plan_id
        ).group_by(
            Plan.id, Plan.name
        ).all()
        
        # Count unassigned devices
        unassigned = db.query(Device).filter(
            ~Device.id.in_(
                db.query(PlanAssignment.device_id)
            )
        ).count()
        
        data = [{"name": name, "count": count} for name, count in results]
        if unassigned > 0:
            data.append({"name": "Sin plan", "count": unassigned})
        
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching devices by plan: {str(e)}")


@router.get("/revenue")
async def get_revenue_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)
):
    """
    Get revenue statistics based on plan assignments.
    """
    try:
        # Calculate total monthly revenue from active plan assignments
        result = db.query(
            func.sum(Plan.price).label('total_revenue'),
            func.count(PlanAssignment.id).label('total_subscriptions')
        ).join(
            PlanAssignment, Plan.id == PlanAssignment.plan_id
        ).first()
        
        total_revenue = float(result.total_revenue) if result.total_revenue else 0.0
        total_subscriptions = result.total_subscriptions if result.total_subscriptions else 0
        
        # Get revenue by plan
        plans_revenue = db.query(
            Plan.name,
            Plan.price,
            func.count(PlanAssignment.id).label('subscriptions'),
            (Plan.price * func.count(PlanAssignment.id)).label('plan_revenue')
        ).join(
            PlanAssignment, Plan.id == PlanAssignment.plan_id
        ).group_by(
            Plan.id, Plan.name, Plan.price
        ).all()
        
        plans_data = [
            {
                "plan_name": name,
                "price": float(price),
                "subscriptions": subs,
                "revenue": float(revenue)
            }
            for name, price, subs, revenue in plans_revenue
        ]
        
        return {
            "total_monthly_revenue": total_revenue,
            "total_subscriptions": total_subscriptions,
            "average_revenue_per_user": total_revenue / total_subscriptions if total_subscriptions > 0 else 0,
            "plans": plans_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching revenue stats: {str(e)}")


@router.get("/recent-activity")
async def get_recent_activity(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)
):
    """
    Get recent activity (new devices, plan assignments, etc.)
    """
    try:
        # Get recently created devices
        recent_devices = db.query(Device).order_by(
            Device.created_at.desc()
        ).limit(limit).all()
        
        # Get recent plan assignments
        recent_assignments = db.query(PlanAssignment).order_by(
            PlanAssignment.assigned_at.desc()
        ).limit(limit).all()
        
        activities = []
        
        for device in recent_devices:
            device_label = device.hostname or device.mac or "Dispositivo"
            activities.append({
                "type": "device_created",
                "timestamp": device.created_at.isoformat(),
                "description": f"Nuevo dispositivo: {device_label}",
                "details": {
                    "device_id": device.id,
                    "device_name": device.hostname,
                    "ip_address": device.ip
                }
            })
        
        for assignment in recent_assignments:
            device = db.query(Device).filter(Device.id == assignment.device_id).first()
            plan = db.query(Plan).filter(Plan.id == assignment.plan_id).first()
            if device and plan:
                device_label = device.hostname or device.mac or "Dispositivo"
                activities.append({
                    "type": "plan_assigned",
                    "timestamp": assignment.assigned_at.isoformat(),
                    "description": f"Plan '{plan.name}' asignado a {device_label}",
                    "details": {
                        "device_id": device.id,
                        "device_name": device.hostname,
                        "plan_id": plan.id,
                        "plan_name": plan.name
                    }
                })
        
        # Sort by timestamp descending
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return activities[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recent activity: {str(e)}")
