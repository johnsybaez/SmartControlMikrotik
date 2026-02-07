"""SQLAlchemy Models según especificación del plan"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey, BigInteger, Date, JSON
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class User(Base):
    """Usuarios del sistema"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    email = Column(String(100))
    role = Column(String(20), nullable=False, default="readonly")  # admin, operator, readonly
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    audit_events = relationship("AuditEvent", back_populates="user")


class Router(Base):
    """Routers MikroTik configurados"""
    __tablename__ = "routers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    host = Column(String(100), nullable=False)
    api_port = Column(Integer, default=8728)
    ssh_port = Column(Integer, default=22)
    username = Column(String(50), nullable=False)
    password = Column(String(255), nullable=False)  # Encriptado
    use_ssl = Column(Boolean, default=False)
    ssl_verify = Column(Boolean, default=False)
    timeout = Column(Integer, default=10)
    description = Column(Text)
    status = Column(String(20), default="active")  # active, inactive, error
    last_seen = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    devices = relationship("Device", back_populates="router")
    address_list_entries = relationship("AddressListEntry", back_populates="router")
    plan_assignments = relationship("PlanAssignment", back_populates="router")
    audit_events = relationship("AuditEvent", back_populates="router")
    stats_snapshots = relationship("StatsSnapshot", back_populates="router")


class Device(Base):
    """Dispositivos (leases DHCP + estado)"""
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    router_id = Column(Integer, ForeignKey("routers.id", ondelete="CASCADE"), nullable=False)
    mac = Column(String(17), nullable=False)  # AA:BB:CC:DD:EE:FF
    ip = Column(String(45))  # IPv4 o IPv6
    hostname = Column(String(100))
    comment = Column(Text)
    state = Column(String(20), default="unknown")  # bound, waiting, offered, expired, unknown
    server = Column(String(50))  # DHCP server name
    last_seen = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    router = relationship("Router", back_populates="devices")
    plan_assignments = relationship("PlanAssignment", back_populates="device")
    traffic_stats = relationship("DeviceTrafficStats", back_populates="device")


class AddressListEntry(Base):
    """Entradas en address-lists de MikroTik"""
    __tablename__ = "address_list_entries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    router_id = Column(Integer, ForeignKey("routers.id", ondelete="CASCADE"), nullable=False)
    list_name = Column(String(50), nullable=False)  # INET_PERMITIDO, INET_BLOQUEADO
    address = Column(String(45), nullable=False)  # IP o MAC
    mikrotik_id = Column(String(20))  # *ID del item en MikroTik
    comment = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    synced_at = Column(DateTime(timezone=True))
    
    # Relationships
    router = relationship("Router", back_populates="address_list_entries")


class Plan(Base):
    """Planes de servicio QoS"""
    __tablename__ = "plans"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    upload_limit = Column(String(20), nullable=False)  # 10M, 50M, unlimited
    download_limit = Column(String(20), nullable=False)
    burst_upload = Column(String(20))
    burst_download = Column(String(20))
    burst_threshold = Column(String(50))
    burst_time = Column(String(20))
    priority = Column(Integer, default=8)  # 1-8 MikroTik priority
    price = Column(Integer, default=0)  # Precio mensual del plan
    type = Column(String(20), default="simple_queue")
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    plan_assignments = relationship("PlanAssignment", back_populates="plan")


class PlanAssignment(Base):
    """Asignaciones de planes a dispositivos"""
    __tablename__ = "plan_assignments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    router_id = Column(Integer, ForeignKey("routers.id", ondelete="CASCADE"), nullable=False)
    queue_mikrotik_id = Column(String(20))  # *ID de la queue en MikroTik
    target = Column(String(50))  # 192.168.1.100/32 o MAC
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    removed_at = Column(DateTime(timezone=True))
    assigned_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    
    # Relationships
    device = relationship("Device", back_populates="plan_assignments")
    plan = relationship("Plan", back_populates="plan_assignments")
    router = relationship("Router", back_populates="plan_assignments")


class AuditEvent(Base):
    """Eventos de auditoría"""
    __tablename__ = "audit_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    correlation_id = Column(String(50))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    username = Column(String(50))
    action = Column(String(100), nullable=False, index=True)
    target = Column(String(200))
    router_id = Column(Integer, ForeignKey("routers.id", ondelete="SET NULL"))
    method_used = Column(String(10))  # API, SSH
    result = Column(String(20))  # success, error
    error_message = Column(Text)
    extra_data = Column(JSON)
    
    # Relationships
    user = relationship("User", back_populates="audit_events")
    router = relationship("Router", back_populates="audit_events")


class StatsSnapshot(Base):
    """Snapshots de estadísticas agregadas"""
    __tablename__ = "stats_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    router_id = Column(Integer, ForeignKey("routers.id", ondelete="CASCADE"), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    total_traffic_up_bytes = Column(BigInteger, default=0)
    total_traffic_down_bytes = Column(BigInteger, default=0)
    allowed_devices_count = Column(Integer, default=0)
    denied_devices_count = Column(Integer, default=0)
    bound_leases_count = Column(Integer, default=0)
    active_queues_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    router = relationship("Router", back_populates="stats_snapshots")


class DeviceTrafficStats(Base):
    """Estadísticas de tráfico por dispositivo"""
    __tablename__ = "device_traffic_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    router_id = Column(Integer, ForeignKey("routers.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    traffic_up_bytes = Column(BigInteger, default=0)
    traffic_down_bytes = Column(BigInteger, default=0)
    packets_up = Column(BigInteger, default=0)
    packets_down = Column(BigInteger, default=0)
    source = Column(String(20))  # queue, interface_monitor, traffic_flow
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    device = relationship("Device", back_populates="traffic_stats")
