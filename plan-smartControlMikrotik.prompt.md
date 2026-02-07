# PLANIFICACIÓN COMPLETA: Sistema SmartControl para Gestión de Red MikroTik

---

## 1. ARQUITECTURA DEL SISTEMA

### 1.1 Diagrama de Arquitectura (Textual)

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENTE (Browser)                         │
│                     React SPA + TailwindCSS                      │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/HTTPS
                             │ JSON REST API
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND - FastAPI                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ API Layer (routes/)                                       │  │
│  │  - auth, routers, devices, plans, qos, stats, reports... │  │
│  └──────────────────┬───────────────────────────────────────┘  │
│                     │                                            │
│  ┌──────────────────▼───────────────────────────────────────┐  │
│  │ Services Layer                                            │  │
│  │  - access_control, dhcp, qos, stats, router_config       │  │
│  └──────────┬────────────────────────┬──────────────────────┘  │
│             │                        │                           │
│  ┌──────────▼────────┐    ┌─────────▼──────────┐               │
│  │ MikroTik Client   │    │  DB Repository     │               │
│  │ (orquestador)     │    │  (SQLite ORM)      │               │
│  │  - API (primary)  │    └────────────────────┘               │
│  │  - SSH (fallback) │                                          │
│  │  - Circuit Breaker│                                          │
│  └──────────┬────────┘                                          │
└─────────────┼───────────────────────────────────────────────────┘
              │
              │ RouterOS API (port 8728/8729)
              │ SSH (port configurable)
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MikroTik RouterOS 7.x                         │
│  - /ip/dhcp-server/lease                                         │
│  - /ip/firewall/address-list                                     │
│  - /queue/simple                                                 │
│  - /system/resource                                              │
│  - /interface/monitor-traffic                                    │
└─────────────────────────────────────────────────────────────────┘

PERSISTENCIA:
┌─────────────────────────────────────────────────────────────────┐
│                    SQLite (smartbjportal.db)                     │
│  - users, roles, routers, devices, plans, audit_events, stats   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Flujo de Comunicación Principal

**Flujo Típico: Permitir Dispositivo**
```
User (React) 
  → POST /api/devices/permit {mac, router_id}
    → FastAPI Router (auth middleware → RBAC check)
      → AccessControlService.permit_device()
        → MikroTikClient.get_or_create(router_id)
          → API Client: RouterOsApiPool.get_api()
            → /ip/firewall/address-list/add {list=INET_PERMITIDO, address=...}
          ← Success/Fail
        → DB Repository: save device state
        → Audit: log event (user, action, method_used, result)
      ← {success, method_used: "API", data: {...}, correlation_id}
  ← 200 OK JSON
```

**Fallback a SSH (Circuit Breaker)**
```
Si API falla 3 veces consecutivas en router X:
  → Circuit state = OPEN para router X
  → Próximas llamadas en 5 min usan SSH automáticamente
  → SSH Client: paramiko connect → exec command
  → method_used = "SSH"
  → Después de 5 min o éxito manual → circuit = HALF_OPEN → retry API
```

---

## 2. MÓDULOS Y RESPONSABILIDADES

### 2.1 Backend (FastAPI)

| Módulo | Responsabilidad |
|--------|-----------------|
| **app/main.py** | Entry point FastAPI, CORS, middleware, routers mount |
| **app/core/config.py** | Carga config.env, validación, settings singleton |
| **app/core/logging.py** | Configuración logger (console + file), filtro de secretos |
| **app/core/security.py** | JWT encode/decode, password hashing (bcrypt), RBAC decorators |
| **app/mikrotik/api_client.py** | Wrapper routeros-api, pool por router, timeouts, retries |
| **app/mikrotik/ssh_client.py** | Wrapper paramiko, ejecución comandos SSH, manejo errores |
| **app/mikrotik/client.py** | **Orquestador**: decide API vs SSH, circuit breaker, logging method_used |
| **app/services/access_control.py** | Lógica permitir/denegar, sync address-list con DB |
| **app/services/dhcp.py** | Leer leases DHCP, filtrar status=bound, enriquecer con estado DB |
| **app/services/qos.py** | CRUD planes, asignar/quitar colas (simple queues), validar duplicados |
| **app/services/stats.py** | Recolección métricas: queues bytes, device counters, snapshots |
| **app/services/router_config.py** | Test conexión, leer/modificar WAN/DNS/Firewall rules (safe templates) |
| **app/db/models.py** | SQLAlchemy models: User, Role, Router, Device, Plan, AuditEvent, etc. |
| **app/db/repository.py** | CRUD genérico + queries específicas (get_devices_by_state, etc.) |
| **app/routes/auth.py** | POST /login, /logout, GET /me |
| **app/routes/routers.py** | CRUD routers, test conexión |
| **app/routes/devices.py** | GET devices, POST permit/deny, sync |
| **app/routes/plans.py** | CRUD planes, asignación a dispositivos |
| **app/routes/qos.py** | GET queues activas, modificar |
| **app/routes/stats.py** | GET summary, device traffic |
| **app/routes/reports.py** | Export CSV/PDF (CSV MVP) |
| **app/routes/users.py** | CRUD users, asignar roles |
| **app/routes/audit.py** | GET audit log filtrado |
| **tests/** | pytest: unit + integration tests |

### 2.2 Frontend (React)

| Módulo | Responsabilidad |
|--------|-----------------|
| **src/App.tsx** | Router principal, layout con sidebar, auth guard |
| **src/pages/Dashboard.tsx** | Resumen: stats, gráficos (recharts), métricas rápidas |
| **src/pages/Devices.tsx** | Tabla leases DHCP + estados, búsqueda, permitir/denegar toggle |
| **src/pages/AllowedBlocked.tsx** | Vistas filtradas: solo permitidos, solo bloqueados |
| **src/pages/ServicePlans.tsx** | CRUD planes (tabla + modal form) |
| **src/pages/QoS.tsx** | Ver queues activas, asignar/modificar planes por device |
| **src/pages/Reports.tsx** | Filtros rango fechas, export CSV, vista previa tabla |
| **src/pages/Users.tsx** | CRUD usuarios, asignación roles |
| **src/pages/Routers.tsx** | CRUD routers, test conectividad, indicador estado |
| **src/pages/Administration.tsx** | Panel administrativo - CRUD usuarios (roles, passwords), CRUD routers MikroTik (IP, puertos, credenciales), botón limpiar base de datos |
| **src/pages/RouterConfig.tsx** | Tabs: WAN, DNS, Firewall (read-only MVP, edit fase 2) |
| **src/pages/Audit.tsx** | Log eventos, filtros, paginación |
| **src/components/DeviceTable.tsx** | Tabla reutilizable con paginación, columnas configurables |
| **src/components/PlanModal.tsx** | Form crear/editar plan |
| **src/components/Sidebar.tsx** | Navegación lateral colapsable |
| **src/components/Toast.tsx** | Notificaciones (react-hot-toast) |
| **src/services/api.ts** | Axios instance, interceptors auth, error handling |
| **src/store/authStore.ts** | Zustand: estado auth (user, token, login/logout) |
| **src/store/routerStore.ts** | Zustand: routers activos, selección actual |
| **src/hooks/useDevices.ts** | React Query: fetch devices, mutations (permit/deny) |
| **src/hooks/usePlans.ts** | React Query: fetch plans, CRUD |

**Justificación Zustand**: Ligero, sin boilerplate, ideal para auth y selección de router global. React Query para server state (cache, refetch automático).

---

## 3. ENDPOINTS API (Request/Response Ejemplos)

### 3.1 Health & Auth

**GET /health**
```
Response 200:
{
  "status": "ok",
  "version": "1.0.0",
  "db": "connected",
  "timestamp": "2026-01-29T20:15:00Z"
}
```

**POST /api/auth/login**
```
Request:
{
  "username": "admin",
  "password": "securepass"
}

Response 200:
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "username": "admin",
      "role": "admin"
    }
  }
}
```

### 3.2 Routers

**POST /api/routers**
```
Request:
{
  "name": "Router Principal",
  "host": "10.80.0.1",
  "api_port": 8728,
  "ssh_port": 2214,
  "username": "portal",
  "password": "Porta123!!",
  "use_ssl": false
}

Response 201:
{
  "success": true,
  "method_used": "API",
  "data": {
    "id": 1,
    "name": "Router Principal",
    "host": "10.80.0.1",
    "status": "active",
    "created_at": "2026-01-29T20:00:00Z"
  },
  "correlation_id": "abc-123-def"
}
```

**POST /api/routers/{id}/test-connection**
```
Request: {} (empty body)

Response 200:
{
  "success": true,
  "method_used": "API",
  "data": {
    "api_reachable": true,
    "ssh_reachable": true,
    "router_identity": "MikroTik-RB450G",
    "version": "7.12",
    "uptime": "3d2h15m"
  },
  "correlation_id": "xyz-456"
}
```

### 3.3 Devices

**GET /api/devices?router_id=1&status=bound**
```
Response 200:
{
  "success": true,
  "method_used": "API",
  "data": {
    "total": 15,
    "items": [
      {
        "id": 1,
        "mac": "00:11:22:33:44:55",
        "ip": "192.168.1.100",
        "hostname": "laptop-juan",
        "status": "bound",
        "state": "allowed",  // allowed|denied|pending
        "plan_id": 2,
        "plan_name": "10M/5M",
        "last_seen": "2026-01-29T19:55:00Z",
        "router_id": 1
      },
      // ...
    ]
  },
  "correlation_id": "dev-001"
}
```  

**POST /api/devices/permit**
```
Request:
{
  "router_id": 1,
  "mac": "00:11:22:33:44:55",
  "comment": "Cliente premium"
}

Response 200:
{
  "success": true,
  "method_used": "API",
  "data": {
    "device_id": 1,
    "mac": "00:11:22:33:44:55",
    "state": "allowed",
    "address_list_entry_id": "*5",  // MikroTik internal ID
    "action": "added_to_INET_PERMITIDO"
  },
  "correlation_id": "permit-123"
}
```

**POST /api/devices/deny**
```
Request:
{
  "router_id": 1,
  "mac": "00:11:22:33:44:55",
  "reason": "Violación política uso"
}

Response 200:
{
  "success": true,
  "method_used": "API",
  "data": {
    "device_id": 1,
    "mac": "00:11:22:33:44:55",
    "state": "denied",
    "address_list_entry_id": "*8",
    "action": "added_to_INET_BLOQUEADO_and_removed_from_INET_PERMITIDO"
  },
  "correlation_id": "deny-456"
}
```

### 3.4 Address Lists

**GET /api/address-lists/INET_PERMITIDO?router_id=1**
```
Response 200:
{
  "success": true,
  "method_used": "API",
  "data": {
    "list_name": "INET_PERMITIDO",
    "entries": [
      {
        "id": "*5",
        "address": "192.168.1.100",
        "mac-address": "00:11:22:33:44:55",
        "comment": "Cliente premium",
        "creation-time": "jan/29/2026 19:30:00"
      },
      // ...
    ]
  },
  "correlation_id": "addrlist-001"
}
```

### 3.5 Plans

**POST /api/plans**
```
Request:
{
  "name": "Plan Empresarial 50M",
  "upload_limit": "50M",
  "download_limit": "50M",
  "burst_upload": "60M",
  "burst_download": "60M",
  "burst_threshold": "40M/40M",
  "burst_time": "8s/8s",
  "priority": 3,
  "description": "Plan empresas"
}

Response 201:
{
  "success": true,
  "data": {
    "id": 3,
    "name": "Plan Empresarial 50M",
    "upload_limit": "50M",
    "download_limit": "50M",
    "created_at": "2026-01-29T20:10:00Z"
  },
  "correlation_id": "plan-789"
}
```

**POST /api/plans/assign**
```
Request:
{
  "device_id": 1,  // o usar mac: "00:11:22:33:44:55"
  "plan_id": 3,
  "router_id": 1
}

Response 200:
{
  "success": true,
  "method_used": "API",
  "data": {
    "assignment_id": 10,
    "device_id": 1,
    "plan_id": 3,
    "queue_id": "*A",  // MikroTik queue internal ID
    "target": "192.168.1.100/32",
    "max_limit": "50M/50M",
    "applied_at": "2026-01-29T20:12:00Z"
  },
  "correlation_id": "assign-555"
}
```

### 3.6 QoS

**GET /api/qos/queues?router_id=1**
```
Response 200:
{
  "success": true,
  "method_used": "API",
  "data": {
    "total": 5,
    "queues": [
      {
        "id": "*A",
        "name": "queue-192.168.1.100",
        "target": "192.168.1.100/32",
        "max_limit": "50M/50M",
        "burst_limit": "60M/60M",
        "bytes": "1234567890/9876543210",  // up/down
        "packets": "1000000/2000000",
        "disabled": false,
        "comment": "Plan Empresarial 50M - device_id:1"
      },
      // ...
    ]
  },
  "correlation_id": "qos-001"
}
```

### 3.7 Stats

**GET /api/stats/summary?range=7d&router_id=1**
```
Response 200:
{
  "success": true,
  "method_used": "API",
  "data": {
    "range_days": 7,
    "allowed_devices": 25,
    "denied_devices": 3,
    "bound_leases": 28,
    "active_queues": 25,
    "total_traffic_up_gb": 150.5,
    "total_traffic_down_gb": 890.2,
    "top_consumers": [
      {
        "device_id": 5,
        "mac": "AA:BB:CC:DD:EE:FF",
        "hostname": "server-backup",
        "traffic_down_gb": 200.5,
        "traffic_up_gb": 50.2
      },
      // top 10
    ],
    "daily_stats": [
      {
        "date": "2026-01-29",
        "traffic_up_gb": 25.1,
        "traffic_down_gb": 130.5
      },
      // ...
    ]
  },
  "correlation_id": "stats-summary-123"
}
```

### 3.8 Reports

**GET /api/reports/export.csv?range=30d&router_id=1&type=devices**
```
Response 200 (text/csv):
Headers: Content-Disposition: attachment; filename="devices_report_2026-01-29.csv"

CSV Content:
mac,ip,hostname,state,plan,traffic_up_gb,traffic_down_gb,last_seen
00:11:22:33:44:55,192.168.1.100,laptop-juan,allowed,10M/5M,5.2,25.8,2026-01-29T19:55:00Z
...
```

### 3.9 Users

**POST /api/users**
```
Request:
{
  "username": "operador1",
  "password": "pass123",
  "role": "operator",
  "full_name": "Juan Operador"
}

Response 201:
{
  "success": true,
  "data": {
    "id": 5,
    "username": "operador1",
    "role": "operator",
    "created_at": "2026-01-29T20:20:00Z"
  },
  "correlation_id": "user-999"
}
```

### 3.10 Audit

**GET /api/audit?range=7d&action=permit&user_id=1**
```
Response 200:
{
  "success": true,
  "data": {
    "total": 150,
    "page": 1,
    "per_page": 50,
    "events": [
      {
        "id": 1500,
        "timestamp": "2026-01-29T20:00:00Z",
        "user": "admin",
        "action": "permit_device",
        "target": "00:11:22:33:44:55",
        "router_id": 1,
        "router_name": "Router Principal",
        "method_used": "API",
        "result": "success",
        "error": null,
        "correlation_id": "permit-123"
      },
      // ...
    ]
  },
  "correlation_id": "audit-query-001"
}
```

### 3.8 Administración del Sistema (Solo Admin)

#### POST `/api/admin/users`
**Descripción:** Crear nuevo usuario del sistema con rol y contraseña

**Request:**
```json
{
  "username": "operador1",
  "password": "Pass123!!",
  "role": "operator",
  "full_name": "Juan Operador"
}
```

**Response:**
```json
{
  "id": 2,
  "username": "operador1",
  "role": "operator",
  "full_name": "Juan Operador",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### PUT `/api/admin/users/{user_id}`
**Descripción:** Actualizar datos de usuario (incluye cambio de password y rol)

**Request:**
```json
{
  "password": "NewPass456!!",
  "role": "admin",
  "full_name": "Juan Admin"
}
```

#### DELETE `/api/admin/users/{user_id}`
**Descripción:** Eliminar usuario (no permite eliminar último admin)

#### POST `/api/admin/routers`
**Descripción:** Agregar nuevo router MikroTik al sistema

**Request:**
```json
{
  "name": "MikroTik Sucursal Norte",
  "host": "10.80.0.2",
  "api_port": 8728,
  "ssh_port": 22,
  "username": "admin",
  "password": "RouterPass123!!",
  "description": "Router principal sucursal norte"
}
```

**Response:**
```json
{
  "id": 2,
  "name": "MikroTik Sucursal Norte",
  "host": "10.80.0.2",
  "api_port": 8728,
  "ssh_port": 22,
  "status": "active",
  "created_at": "2024-01-15T10:35:00Z"
}
```

#### PUT `/api/admin/routers/{router_id}`
**Descripción:** Actualizar configuración de router existente

#### DELETE `/api/admin/routers/{router_id}`
**Descripción:** Eliminar router del sistema (valida que no tenga dispositivos activos)

#### POST `/api/admin/database/reset`
**Descripción:** Limpiar toda la base de datos excepto usuario admin default

**Request:**
```json
{
  "confirmation": "RESET_DATABASE",
  "preserve_admin": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Base de datos reiniciada. Se preservó usuario admin.",
  "deleted_records": {
    "devices": 45,
    "users": 3,
    "routers": 1,
    "audit_logs": 1523
  },
  "preserved": {
    "admin_username": "admin"
  }
}
```

---

## 4. MODELO DE DATOS SQLite

### 4.1 Esquema de Tablas

```sql
-- Users & Auth
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    email VARCHAR(100),
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL,  -- admin, operator, readonly
    description TEXT
);

CREATE TABLE user_roles (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);

-- Routers
CREATE TABLE routers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    host VARCHAR(100) NOT NULL,
    api_port INTEGER DEFAULT 8728,
    ssh_port INTEGER DEFAULT 22,
    username VARCHAR(50) NOT NULL,
    password_encrypted TEXT NOT NULL,  -- AES encrypted with app key
    use_ssl BOOLEAN DEFAULT 0,
    ssl_verify BOOLEAN DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',  -- active, inactive, error
    circuit_state VARCHAR(20) DEFAULT 'closed',  -- closed, open, half_open
    circuit_failures INTEGER DEFAULT 0,
    circuit_last_failure TIMESTAMP,
    last_connected TIMESTAMP,
    router_identity VARCHAR(100),
    routeros_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Devices
CREATE TABLE devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    router_id INTEGER NOT NULL,
    mac VARCHAR(17) NOT NULL,  -- 00:11:22:33:44:55
    ip VARCHAR(15),  -- 192.168.1.100
    hostname VARCHAR(100),
    state VARCHAR(20) DEFAULT 'pending',  -- allowed, denied, pending
    plan_id INTEGER,
    dhcp_status VARCHAR(20),  -- bound, waiting, searching
    last_seen TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (router_id) REFERENCES routers(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE SET NULL,
    UNIQUE(router_id, mac)
);

-- Address List Mapping (cache de estado MikroTik)
CREATE TABLE address_list_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    router_id INTEGER NOT NULL,
    device_id INTEGER,
    list_name VARCHAR(50) NOT NULL,  -- INET_PERMITIDO, INET_BLOQUEADO
    address VARCHAR(50) NOT NULL,  -- IP o MAC
    mikrotik_id VARCHAR(20),  -- *5, *A (MikroTik internal ID)
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMP,
    FOREIGN KEY (router_id) REFERENCES routers(id) ON DELETE CASCADE,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- Service Plans
CREATE TABLE plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    upload_limit VARCHAR(20) NOT NULL,  -- 10M, 50M, unlimited
    download_limit VARCHAR(20) NOT NULL,
    burst_upload VARCHAR(20),
    burst_download VARCHAR(20),
    burst_threshold VARCHAR(50),
    burst_time VARCHAR(20),
    priority INTEGER DEFAULT 8,  -- 1-8 MikroTik priority
    type VARCHAR(20) DEFAULT 'simple_queue',  -- simple_queue, pcq
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Plan Assignments
CREATE TABLE plan_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER,
    plan_id INTEGER NOT NULL,
    router_id INTEGER NOT NULL,
    queue_mikrotik_id VARCHAR(20),  -- *A MikroTik queue ID
    target VARCHAR(50),  -- 192.168.1.100/32 or MAC
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    removed_at TIMESTAMP,
    assigned_by_user_id INTEGER,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
    FOREIGN KEY (router_id) REFERENCES routers(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Audit Events
CREATE TABLE audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    correlation_id VARCHAR(50),
    user_id INTEGER,
    username VARCHAR(50),
    action VARCHAR(100) NOT NULL,  -- permit_device, deny_device, assign_plan, etc.
    target VARCHAR(200),  -- MAC, IP, device_id, router_id
    router_id INTEGER,
    method_used VARCHAR(10),  -- API, SSH
    result VARCHAR(20),  -- success, error
    error_message TEXT,
    metadata JSON,  -- Additional context
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (router_id) REFERENCES routers(id) ON DELETE SET NULL
);

-- Stats Snapshots (pre-agregados para dashboard)
CREATE TABLE stats_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    router_id INTEGER NOT NULL,
    snapshot_date DATE NOT NULL,
    total_traffic_up_bytes BIGINT DEFAULT 0,
    total_traffic_down_bytes BIGINT DEFAULT 0,
    allowed_devices_count INTEGER DEFAULT 0,
    denied_devices_count INTEGER DEFAULT 0,
    bound_leases_count INTEGER DEFAULT 0,
    active_queues_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (router_id) REFERENCES routers(id) ON DELETE CASCADE,
    UNIQUE(router_id, snapshot_date)
);

-- Device Traffic Stats (granular, por dispositivo)
CREATE TABLE device_traffic_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    router_id INTEGER NOT NULL,
    date DATE NOT NULL,
    traffic_up_bytes BIGINT DEFAULT 0,
    traffic_down_bytes BIGINT DEFAULT 0,
    packets_up BIGINT DEFAULT 0,
    packets_down BIGINT DEFAULT 0,
    source VARCHAR(20),  -- queue, interface_monitor, traffic_flow
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    FOREIGN KEY (router_id) REFERENCES routers(id) ON DELETE CASCADE,
    UNIQUE(device_id, date)
);
```

### 4.2 Índices Recomendados

```sql
-- Performance indexes
CREATE INDEX idx_devices_router_mac ON devices(router_id, mac);
CREATE INDEX idx_devices_state ON devices(state);
CREATE INDEX idx_devices_last_seen ON devices(last_seen);
CREATE INDEX idx_address_list_router_list ON address_list_entries(router_id, list_name);
CREATE INDEX idx_plan_assignments_device ON plan_assignments(device_id);
CREATE INDEX idx_plan_assignments_active ON plan_assignments(removed_at) WHERE removed_at IS NULL;
CREATE INDEX idx_audit_timestamp ON audit_events(timestamp DESC);
CREATE INDEX idx_audit_user ON audit_events(user_id);
CREATE INDEX idx_audit_action ON audit_events(action);
CREATE INDEX idx_stats_router_date ON stats_snapshots(router_id, snapshot_date);
CREATE INDEX idx_device_traffic_date ON device_traffic_stats(device_id, date DESC);
```

---

## 5. BACKLOG POR FASES

### 5.1 FASE 1: MVP (2-3 semanas)

**Backend Core**
- [ ] Setup proyecto FastAPI + SQLite + SQLAlchemy
- [ ] Config.env loading, logging, security (JWT)
- [ ] DB models + migrations (Alembic)
- [ ] MikroTik API Client (routeros-api wrapper)
- [ ] Auth endpoints (login, me)
- [ ] Router CRUD + test connection (API only)
- [ ] DHCP service: read leases (status=bound)
- [ ] Access Control: permit/deny devices (address-list)
- [ ] Device endpoints + basic sync
- [ ] Plans CRUD
- [ ] QoS: assign plan via simple queue
- [ ] Audit logging básico

**Frontend Core**
- [ ] Setup React + Vite + TailwindCSS
- [ ] Auth flow (login, protected routes)
- [ ] Layout con sidebar
- [ ] Dashboard básico (contadores)
- [ ] Devices page (tabla + permit/deny)
- [ ] Plans page (CRUD)
- [ ] Routers page (CRUD + test)
- [ ] API client (axios) + Zustand store

**Testing**
- [ ] Unit tests clave (access_control, qos)
- [ ] Integration test: permit device end-to-end

### 5.2 FASE 2: Hardening (1-2 semanas)

**Backend**
- [ ] SSH fallback client (paramiko)
- [ ] Circuit breaker implementation
- [ ] Advanced sync: reconcile DB ↔ MikroTik
- [ ] Stats collection service (queue bytes)
- [ ] Stats snapshots daily job
- [ ] Export CSV reports
- [ ] User management + RBAC enforcement
- [ ] Rate limiting middleware
- [ ] Error handling standardization

**Frontend**
- [ ] Stats Dashboard con gráficos (recharts)
- [ ] Reports page + CSV download
- [ ] Users management page
- [ ] Audit log viewer
- [ ] Toast notifications
- [ ] Loading states + error boundaries
- [ ] Responsive mobile layout

**Deployment**
- [ ] Dockerfile backend (uvicorn)
- [ ] Dockerfile frontend (nginx)
- [ ] docker-compose.yml
- [ ] Backup scripts (SQLite)
- [ ] systemd service files (Ubuntu)

### 5.3 FASE 3: Advanced Features (2-3 semanas)

**Backend**
- [ ] Multi-router support completo
- [ ] Router config module: WAN status, DNS view
- [ ] Firewall rules viewer (safe templates)
- [ ] Traffic-flow integration (opcional)
- [ ] SNMP fallback stats (opcional)
- [ ] PDF reports (WeasyPrint)
- [ ] Webhooks/notifications (email/telegram)
- [ ] API versioning

**Frontend**
- [ ] Router config tabs (WAN, DNS, Firewall)
- [ ] Advanced filters + saved searches
- [ ] Bulk actions (permit/deny múltiples)
- [ ] Plan assignment to groups
- [ ] Dark mode
- [ ] i18n (español/inglés)

**Performance**
- [ ] DB indexes optimization
- [ ] API response caching (Redis opcional)
- [ ] Pagination backend
- [ ] React Query optimistic updates

### 5.4 FASE 4: Production Ready (continuo)

- [ ] Comprehensive test coverage (>80%)
- [ ] Load testing (Locust)
- [ ] Security audit
- [ ] Documentation (Swagger, README, runbooks)
- [ ] Monitoring (Prometheus/Grafana opcional)
- [ ] Log aggregation
- [ ] Automated backups
- [ ] Disaster recovery plan

---

## 6. ESTRATEGIA DE ERRORES Y FALLBACK API/SSH

### 6.1 Cuándo Usar API (SIEMPRE PRIMERO)

**Operaciones soportadas 100% por RouterOS API:**
- `/ip/dhcp-server/lease` (read leases)
- `/ip/firewall/address-list` (add/remove/print)
- `/queue/simple` (add/set/remove/print)
- `/system/resource` (system info)
- `/interface` (list interfaces)
- `/ip/route` (routes)
- `/ip/dns` (DNS settings - read/write)
- `/ip/firewall/filter` (firewall rules - read/add)
- `/system/identity` (router name)

**Decisión**: Usar API para **todo lo anterior**. No usar SSH salvo fallo de conectividad.

### 6.2 Cuándo Usar SSH (FALLBACK EXCEPCIONAL)

**Escenarios válidos para SSH:**
1. **API timeout o conexión rechazada**: Si `routeros-api` no puede conectar (puerto bloqueado, servicio API deshabilitado).
2. **Comandos no soportados por API**: Ejemplo: `/tool/torch` (captura tráfico tiempo real), `/export` (backup config).
3. **Troubleshooting**: Diagnóstico cuando API falla sistemáticamente.

**Circuit Breaker Logic:**
```
Router X state:
- CLOSED: usar API (normal)
- OPEN: 3+ fallos consecutivos API → forzar SSH por 5 minutos
- HALF_OPEN: después de 5 min, reintentar API (1 intento)
  - Si éxito → CLOSED
  - Si fallo → OPEN de nuevo
```

### 6.3 Manejo de Errores por Capa

| Capa | Error | Acción |
|------|-------|--------|
| **API Client** | `ConnectionError` | Incrementar circuit counter, loguear, raise custom `MikrotikConnectionError` |
| **API Client** | `Timeout` | Retry 2 veces (exponential backoff), luego raise |
| **API Client** | `AuthenticationError` | No retry, raise `MikrotikAuthError`, marcar router status=error |
| **SSH Client** | `SSHException` | Loguear, raise `MikrotikSSHError` |
| **Orquestador** | API fail + SSH fail | Return error response, method_used="NONE", correlation_id para audit |
| **Service Layer** | Validation error (invalid MAC) | Return 400 Bad Request, no tocar MikroTik |
| **Service Layer** | DB constraint error | Return 409 Conflict (ej: dispositivo ya existe) |
| **API Routes** | Unhandled exception | Middleware global catch, return 500, loguear stack trace |

### 6.4 Logging y Auditoría

**Cada operación debe loguear:**
- `correlation_id` (UUID único por request)
- `method_used`: "API" | "SSH" | "NONE"
- `router_id` y `user_id`
- `action` (permit_device, assign_plan, etc.)
- `result`: "success" | "error"
- `error_message` (si aplica)
- `duration_ms`

**No loguear:**
- Contraseñas
- Tokens JWT completos
- Datos sensibles de usuarios

---

## 7. VARIABLES DE CONFIGURACIÓN (config.env)

```env
# ============================================
# APPLICATION
# ============================================
APP_NAME=SmartControl
APP_VERSION=1.0.0
ENVIRONMENT=production  # development, production
DEBUG=false

# ============================================
# SERVER
# ============================================
HOST=0.0.0.0
PORT=8000
WORKERS=4  # uvicorn workers (production)
RELOAD=false  # hot reload (solo development)

# ============================================
# SECURITY
# ============================================
SECRET_KEY=your-super-secret-key-min-32-chars-change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440  # 24 hours
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
CORS_CREDENTIALS=true

# ============================================
# DATABASE
# ============================================
DATABASE_URL=sqlite:///./smartbjportal.db
# Para SQLite async (opcional): sqlite+aiosqlite:///./smartbjportal.db

# ============================================
# LOGGING
# ============================================
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_FILE=logs/smartcontrol.log
LOG_MAX_BYTES=10485760  # 10MB
LOG_BACKUP_COUNT=5
LOG_FORMAT=json  # json o text

# ============================================
# MIKROTIK DEFAULT (para router único)
# ============================================
# NOTA: En multi-router, esto es opcional; routers se guardan en DB
MT_HOST=10.80.0.1
MT_PORT=8728
MT_SSH_PORT=2214
MT_USER=portal
MT_PASS=Porta123!!
MT_USE_SSL=false
MT_SSL_VERIFY=false
MT_TIMEOUT=10  # segundos

# ============================================
# ADDRESS LISTS (nombres configurables)
# ============================================
LIST_PERMITIDO=INET_PERMITIDO
LIST_BLOQUEADO=INET_BLOQUEADO

# ============================================
# CIRCUIT BREAKER
# ============================================
CIRCUIT_FAILURE_THRESHOLD=3  # fallos antes de abrir
CIRCUIT_TIMEOUT_SECONDS=300  # 5 minutos en SSH antes de retry API
CIRCUIT_HALF_OPEN_MAX_CALLS=1

# ============================================
# STATS & REPORTS
# ============================================
STATS_COLLECTION_INTERVAL_MINUTES=60  # cada hora
STATS_RETENTION_DAYS=90
REPORTS_TEMP_DIR=/tmp/smartcontrol_reports

# ============================================
# RATE LIMITING (opcional)
# ============================================
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD_SECONDS=60

# ============================================
# EXTERNAL SERVICES (fase avanzada)
# ============================================
# SMTP para notificaciones
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@smartcontrol.local

# Telegram notifications (opcional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Redis (opcional, para cache)
REDIS_URL=redis://localhost:6379/0

# ============================================
# BACKUP
# ============================================
BACKUP_ENABLED=true
BACKUP_SCHEDULE=0 2 * * *  # cron: daily 2 AM
BACKUP_RETENTION_DAYS=30
BACKUP_PATH=/var/backups/smartcontrol
```

---

## 8. DEPENDENCIAS (requirements.txt y package.json)

### 8.1 Backend: requirements.txt

```txt
# FastAPI & ASGI server
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# Database & ORM
sqlalchemy==2.0.25
alembic==1.13.1
aiosqlite==0.19.0  # async SQLite (opcional)

# MikroTik clients
routeros-api==0.17.0
paramiko==3.4.0

# Auth & Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0

# Utilities
pydantic==2.5.3
pydantic-settings==2.1.0

# HTTP client (para testing)
httpx==0.26.0

# Reports
pandas==2.1.4
openpyxl==3.1.2  # Excel export (opcional)

# PDF reports (fase 2)
# weasyprint==60.2

# Monitoring & Logging
structlog==24.1.0

# Rate limiting
slowapi==0.1.9

# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
faker==22.0.0

# Dev tools
black==23.12.1
isort==5.13.2
flake8==7.0.0
mypy==1.8.0
```

### 8.2 Frontend: package.json (dependencies)

```json
{
  "name": "smartcontrol-frontend",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.21.0",
    "@tanstack/react-query": "^5.17.0",
    "axios": "^1.6.5",
    "zustand": "^4.4.7",
    "recharts": "^2.10.3",
    "react-hot-toast": "^2.4.1",
    "react-table": "^7.8.0",
    "@headlessui/react": "^1.7.17",
    "@heroicons/react": "^2.1.1",
    "date-fns": "^3.0.6",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.48",
    "@types/react-dom": "^18.2.18",
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.0.11",
    "tailwindcss": "^3.4.1",
    "postcss": "^8.4.33",
    "autoprefixer": "^10.4.16",
    "typescript": "^5.3.3",
    "eslint": "^8.56.0",
    "prettier": "^3.1.1"
  }
}
```

---

## 9. CONSIDERACIONES PARA PRODUCCIÓN

### 9.1 Deployment Backend

**Uvicorn + Gunicorn (Ubuntu)**
```bash
# systemd service: /etc/systemd/system/smartcontrol.service
[Unit]
Description=SmartControl Backend
After=network.target

[Service]
Type=notify
User=smartcontrol
WorkingDirectory=/opt/smartcontrol/backend
Environment="PATH=/opt/smartcontrol/venv/bin"
ExecStart=/opt/smartcontrol/venv/bin/gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile /var/log/smartcontrol/access.log \
    --error-logfile /var/log/smartcontrol/error.log
Restart=always

[Install]
WantedBy=multi-user.target
```

**Windows Server**
- Usar `waitress` en lugar de gunicorn
- Crear servicio con NSSM (Non-Sucking Service Manager)
- O ejecutar en contenedor Docker

### 9.2 Deployment Frontend

**Nginx (producción)**
```nginx
server {
    listen 80;
    server_name smartcontrol.yourdomain.com;
    
    root /var/www/smartcontrol/frontend/dist;
    index index.html;
    
    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # Proxy API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 9.3 Seguridad

**Hardening checklist:**
- [ ] Cambiar `SECRET_KEY` en producción (mínimo 32 caracteres random)
- [ ] HTTPS obligatorio (Nginx + Let's Encrypt)
- [ ] No exponer puerto 8000 directamente (usar reverse proxy)
- [ ] Firewall: solo permitir 80/443 público, 8000 localhost
- [ ] Rate limiting activo
- [ ] Validar todos los inputs (pydantic validators)
- [ ] SQL injection: usar ORM (SQLAlchemy), no SQL raw
- [ ] XSS: React escapa por defecto, no usar `dangerouslySetInnerHTML`
- [ ] CORS: listar dominios explícitos, no `*`
- [ ] Contraseñas MikroTik encriptadas en DB (AES con `SECRET_KEY`)
- [ ] Logs sin secretos (filtro automático)
- [ ] Actualizar dependencias regularmente (`pip-audit`, `npm audit`)

### 9.4 Backups

**SQLite backup automatizado (cron)**
```bash
#!/bin/bash
# /opt/smartcontrol/scripts/backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/var/backups/smartcontrol
DB_PATH=/opt/smartcontrol/smartbjportal.db

mkdir -p $BACKUP_DIR
sqlite3 $DB_PATH ".backup '$BACKUP_DIR/smartbjportal_$DATE.db'"
gzip $BACKUP_DIR/smartbjportal_$DATE.db

# Retener solo últimos 30 días
find $BACKUP_DIR -name "smartbjportal_*.db.gz" -mtime +30 -delete

# crontab: 0 2 * * * /opt/smartcontrol/scripts/backup.sh
```

**Backup de config.env:**
- Versionar en Git privado (con `git-crypt` para secretos)
- O almacenar encriptado en Vault/KeePass

### 9.5 Monitoreo (Fase Avanzada)

**Métricas recomendadas:**
- Request latency (p50, p95, p99)
- Error rate (HTTP 5xx)
- MikroTik API call duration
- Circuit breaker state changes
- DB query performance
- Active users concurrent

**Herramientas sugeridas:**
- Prometheus + Grafana (opcional)
- Healthcheck endpoint: `/health` con checks DB, MikroTik
- Uptime monitoring externo (UptimeRobot, Pingdom)

### 9.6 Logs

**Estructura logs JSON (para agregación):**
```json
{
  "timestamp": "2026-01-29T20:00:00.123Z",
  "level": "INFO",
  "correlation_id": "abc-123",
  "service": "smartcontrol",
  "module": "access_control",
  "message": "Device permitted",
  "user_id": 1,
  "router_id": 1,
  "mac": "00:11:22:33:44:55",
  "method_used": "API",
  "duration_ms": 125
}
```

**Rotación logs:**
- Usar `RotatingFileHandler` (Python logging)
- O `logrotate` (Linux)
- Retener 30 días, comprimir antiguos

---

## 10. COMANDOS DE VERIFICACIÓN

### 10.1 Test Conectividad MikroTik por API (Python)

**Script standalone: `test_api.py`**
```python
#!/usr/bin/env python3
import os
from routeros_api import RouterOsApiPool
from dotenv import load_dotenv

load_dotenv("config.env")

try:
    pool = RouterOsApiPool(
        host=os.getenv("MT_HOST"),
        username=os.getenv("MT_USER"),
        password=os.getenv("MT_PASS"),
        port=int(os.getenv("MT_PORT", 8728)),
        use_ssl=(os.getenv("MT_USE_SSL", "false").lower() == "true"),
        ssl_verify=(os.getenv("MT_SSL_VERIFY", "false").lower() == "true"),
        plaintext_login=True
    )
    
    api = pool.get_api()
    identity = api.get_resource("/system/identity").get()
    print(f"✅ Conectado a MikroTik: {identity[0]['name']}")
    
    # Test leases
    leases = api.get_resource("/ip/dhcp-server/lease").get()
    print(f"✅ DHCP Leases: {len(leases)}")
    
    # Test address-list
    addrlist = api.get_resource("/ip/firewall/address-list").get()
    print(f"✅ Address List Entries: {len(addrlist)}")
    
    pool.disconnect()
    print("✅ Test API exitoso")
    
except Exception as e:
    print(f"❌ Error API: {e}")
    exit(1)
```

**Ejecutar:**
```bash
python test_api.py
```

### 10.2 Test Conectividad MikroTik por SSH

**Script standalone: `test_ssh.py`**
```python
#!/usr/bin/env python3
import os
import paramiko
from dotenv import load_dotenv

load_dotenv("config.env")

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    ssh.connect(
        hostname=os.getenv("MT_HOST"),
        port=int(os.getenv("MT_SSH_PORT", 22)),
        username=os.getenv("MT_USER"),
        password=os.getenv("MT_PASS"),
        timeout=10
    )
    
    stdin, stdout, stderr = ssh.exec_command("/system identity print")
    identity = stdout.read().decode().strip()
    print(f"✅ Conectado por SSH: {identity}")
    
    stdin, stdout, stderr = ssh.exec_command("/ip dhcp-server lease print count-only")
    lease_count = stdout.read().decode().strip()
    print(f"✅ DHCP Leases: {lease_count}")
    
    ssh.close()
    print("✅ Test SSH exitoso")
    
except Exception as e:
    print(f"❌ Error SSH: {e}")
    exit(1)
```

**Ejecutar:**
```bash
python test_ssh.py
```

### 10.3 Test Conectividad desde Backend FastAPI

**Usar endpoint `/api/routers/{id}/test-connection`:**
```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | jq -r '.data.access_token')

# Test router
curl -X POST http://localhost:8000/api/routers/1/test-connection \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 10.4 Verificación DB

**SQLite CLI:**
```bash
sqlite3 smartbjportal.db

-- Ver tablas
.tables

-- Ver esquema
.schema devices

-- Contar dispositivos
SELECT state, COUNT(*) FROM devices GROUP BY state;

-- Ver últimos audit events
SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT 10;

-- Salir
.quit
```

### 10.5 Healthcheck Endpoint

```bash
curl http://localhost:8000/health
```

Respuesta esperada:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "db": "connected",
  "timestamp": "2026-01-29T20:30:00Z"
}
```

---

## 11. ESTRATEGIA DE MÉTRICAS Y ESTADÍSTICAS

### 11.1 Fuentes de Métricas

| Métrica | Fuente | Método | Confiabilidad | MVP/Fase2 |
|---------|--------|--------|---------------|-----------|
| **Devices permitidos/bloqueados** | `/ip/firewall/address-list` | API | Alta | MVP |
| **Leases bound** | `/ip/dhcp-server/lease` | API | Alta | MVP |
| **Tráfico por queue** | `/queue/simple` (bytes) | API | Alta | MVP |
| **Tráfico por interface** | `/interface/monitor-traffic` | API (snapshot) | Media | Fase2 |
| **Tráfico por IP (detallado)** | Traffic-Flow + collector | Traffic-Flow export | Alta (requiere setup) | Fase2 (opcional) |
| **Top consumers** | Queries agregadas (bytes diff) | API polling | Media-Alta | MVP (aproximado) |
| **Uptime router** | `/system/resource` | API | Alta | MVP |
| **CPU/RAM router** | `/system/resource` | API | Alta | Fase2 |

### 11.2 Implementación MVP

**Recolección cada hora (background task):**
1. Leer `/queue/simple` → obtener bytes actuales por queue
2. Calcular diferencia con snapshot anterior → tráfico periodo
3. Guardar en `device_traffic_stats` por día
4. Agregar en `stats_snapshots` (totales por router)

**Limitaciones MVP:**
- Precisión: granularidad 1 hora
- Si queue se elimina/recrea, se pierde contador
- No se captura tráfico sin queue (dispositivos sin plan)

**Ventajas:**
- No requiere config adicional en MikroTik
- Solo API (no SSH, no SNMP)
- Suficiente para dashboard básico

### 11.3 Mejoras Fase 2 (Opcionales)

**Traffic-Flow (NetFlow):**
- Habilitar en MikroTik: `/ip traffic-flow` → exportar a collector
- Usar `nfcapd` (collector) + `nfdump` (query)
- Pro: tráfico granular por IP/puerto
- Contra: requiere servidor adicional, procesamiento CPU

**SNMP Polling:**
- Habilitar SNMP en MikroTik
- Usar `pysnmp` para leer OIDs (tráfico interface, stats device)
- Pro: estándar, muchas herramientas
- Contra: overhead, menos granular que Traffic-Flow

**Recomendación:**
- MVP: solo API `/queue/simple`
- Fase 2: evaluar Traffic-Flow si cliente requiere granularidad alta
- No usar SNMP (redundante con API)

---

## 12. IMPLEMENTACIÓN QoS: Simple Queues vs Queue Tree

### 12.1 Enfoque Recomendado: **Simple Queues**

**Justificación:**
- **API completo**: `/queue/simple` tiene soporte CRUD completo por API
- **Simplicidad**: 1 queue = 1 dispositivo/IP, fácil mapeo
- **Suficiente para 90% casos**: límite bidireccional (up/down), burst, priority
- **Compatible con address-list**: `target=address-list:INET_PERMITIDO`

**Limitaciones:**
- No soporta estructura jerárquica compleja (parent/child avanzado)
- Performance: 100-200 queues OK, >500 puede impactar (RouterOS 7 mejor)

**Cuándo NO usar Simple Queues:**
- Si necesitas jerarquía compleja (grupos de grupos)
- Si necesitas compartir ancho de banda dinámico entre muchos usuarios (PCQ mejor)

### 12.2 Alternativa: Queue Tree + PCQ (Fase Avanzada)

**Uso:**
- Para planes compartidos (ej: edificio entero 100M, distribuir entre N usuarios)
- Requiere mangle rules (marcar tráfico)
- API soporta Queue Tree pero es más complejo

**Decisión MVP:**
- Usar **Simple Queues** exclusivamente
- Si cliente necesita PCQ → Fase 2

### 12.3 Ejemplo Queue Simple (API)

**Crear queue para dispositivo:**
```python
queue_resource = api.get_resource("/queue/simple")
queue_resource.add(
    name=f"queue-{device_ip}",
    target=f"{device_ip}/32",
    max_limit=f"{plan.upload_limit}/{plan.download_limit}",
    burst_limit=f"{plan.burst_upload}/{plan.burst_download}",
    burst_threshold=plan.burst_threshold,
    burst_time=plan.burst_time,
    priority=f"{plan.priority}/{plan.priority}",
    comment=f"Plan: {plan.name} | Device ID: {device_id}"
)
```

---

## 13. CONFIGURACIÓN MIKROTIK REQUERIDA

Este sistema requiere configuraciones específicas en los dispositivos MikroTik RouterOS para funcionar correctamente.

### 13.1 Habilitar API RouterOS

**Por Winbox/WebFig:**
1. IP → Services → api
2. Habilitar servicio
3. Puerto: 8728 (default, sin SSL)
4. Address: 0.0.0.0/0 (o restringir a IP del servidor)

**Por CLI/SSH:**
```routeros
/ip service
set api disabled=no port=8728 address=""
```

**Verificar:**
```routeros
/ip service print
# Debe mostrar: api enabled, port 8728
```

**Notas importantes:**
- API usa protocolo binario propietario de MikroTik (no HTTP/REST)
- Puerto 8728 = API sin SSL
- Puerto 8729 = API con SSL (requiere certificados)
- Para MVP usar puerto 8728

### 13.2 Habilitar SSH

**Por CLI:**
```routeros
/ip service
set ssh disabled=no port=2214
```

**Crear usuario para el sistema:**
```routeros
/user add name=portal password=Porta123!! group=full
```

### 13.3 Configurar Address Lists

El sistema gestiona dos listas principales:

```routeros
# Crear address-lists vacías (el sistema las poblará)
/ip firewall address-list
add list=INET_PERMITIDO comment="Dispositivos con internet activo"
add list=INET_BLOQUEADO comment="Dispositivos bloqueados"
```

**Reglas de firewall para aplicar bloqueo:**
```routeros
/ip firewall filter
add chain=forward src-address-list=INET_BLOQUEADO action=drop \
    comment="Bloquear dispositivos en lista BLOQUEADO"
    
add chain=forward src-address-list=INET_PERMITIDO action=accept \
    comment="Permitir dispositivos en lista PERMITIDO"
```

**Orden de reglas importante:**
- Regla BLOQUEADO debe ir ANTES que PERMITIDO
- Colocar al inicio del chain forward

### 13.4 Configurar DHCP Server (Opcional)

Si el sistema gestiona asignaciones DHCP estáticas:

```routeros
# Configurar red
/ip address add address=10.80.0.1/24 interface=bridge1

# Crear pool DHCP
/ip pool add name=dhcp_pool ranges=10.80.0.100-10.80.0.250

# Configurar DHCP server
/ip dhcp-server add name=dhcp1 interface=bridge1 address-pool=dhcp_pool disabled=no
/ip dhcp-server network add address=10.80.0.0/24 gateway=10.80.0.1 dns-server=8.8.8.8,8.8.4.4

# El sistema agregará leases estáticos con:
# /ip dhcp-server lease add address=10.80.0.150 mac-address=AA:BB:CC:DD:EE:FF comment="Cliente X"
```

### 13.5 Configurar Simple Queues (Base)

**Configuración inicial (vacía, el sistema las crea):**
```routeros
# No requiere configuración previa
# El sistema creará queues dinámicamente por API:
# /queue/simple add name="queue-10.80.0.150" target=10.80.0.150/32 max-limit=5M/10M
```

**Verificar que Queue está habilitado:**
```routeros
/queue simple print
# Debe responder (vacío inicialmente)
```

### 13.6 Acceso Remoto (Producción)

Si el servidor SmartControl está fuera de la red del MikroTik:

**Opción A: Port Forwarding**
```routeros
/ip firewall nat
add chain=dstnat dst-port=8728 protocol=tcp action=dst-nat \
    to-addresses=10.80.0.1 to-ports=8728 comment="API externa"
    
add chain=dstnat dst-port=2214 protocol=tcp action=dst-nat \
    to-addresses=10.80.0.1 to-ports=2214 comment="SSH externa"
```

**Opción B: VPN (Recomendado)**
- Configurar WireGuard o IPSec entre servidor y MikroTik
- Más seguro que exponer puertos públicos

**Opción C: IP Cloud (RouterOS)**
```routeros
/ip cloud set ddns-enabled=yes
/ip cloud print
# Usará dominio: xxxxxx.sn.mynetname.net
```

### 13.7 Seguridad Recomendada

```routeros
# Limitar acceso API solo desde IP del servidor
/ip service set api address=192.168.1.100/32

# Limitar acceso SSH
/ip service set ssh address=192.168.1.100/32

# Deshabilitar servicios no usados
/ip service
set telnet disabled=yes
set ftp disabled=yes
set www disabled=yes
set www-ssl disabled=yes
set api-ssl disabled=yes

# Firewall: denegar acceso a router desde usuarios finales
/ip firewall filter
add chain=input src-address=10.80.0.0/24 dst-port=8728 protocol=tcp action=drop \
    comment="Bloquear API desde clientes"
add chain=input src-address=10.80.0.0/24 dst-port=22,2214 protocol=tcp action=drop \
    comment="Bloquear SSH desde clientes"
```

### 13.8 Script de Configuración Completo

**Para copiar/pegar en terminal MikroTik:**
```routeros
# ============================================
# CONFIGURACIÓN SMARTCONTROL - MIKROTIK
# ============================================

# 1. Habilitar servicios
/ip service
set api disabled=no port=8728
set ssh disabled=no port=2214
set telnet disabled=yes
set ftp disabled=yes
set www disabled=yes
set www-ssl disabled=yes

# 2. Crear usuario para sistema
/user add name=portal password=Porta123!! group=full comment="Usuario SmartControl"

# 3. Crear address-lists
/ip firewall address-list
add list=INET_PERMITIDO comment="Dispositivos con internet activo - Gestionado por SmartControl"
add list=INET_BLOQUEADO comment="Dispositivos bloqueados - Gestionado por SmartControl"

# 4. Reglas de firewall para aplicar listas
/ip firewall filter
add chain=forward src-address-list=INET_BLOQUEADO action=drop comment="SmartControl: Bloquear lista BLOQUEADO" place-before=0
add chain=forward src-address-list=INET_PERMITIDO action=accept comment="SmartControl: Permitir lista PERMITIDO" place-before=1

# 5. Proteger router de acceso desde clientes (ajustar red según corresponda)
/ip firewall filter
add chain=input src-address=10.80.0.0/24 dst-port=8728 protocol=tcp action=drop comment="Bloquear API desde LAN"
add chain=input src-address=10.80.0.0/24 dst-port=22,2214 protocol=tcp action=drop comment="Bloquear SSH desde LAN"

# 6. Permitir acceso desde servidor SmartControl (ajustar IP del servidor)
# /ip service set api address=192.168.1.100/32
# /ip service set ssh address=192.168.1.100/32

Й
:put "Configuración SmartControl completada. Verificar con: /ip service print"
```

**Verificación post-configuración:**
```routeros
/ip service print
/ip firewall address-list print
/ip firewall filter print where comment~"SmartControl"
/user print
```

### 13.9 Troubleshooting

**Problema: API no conecta**
```routeros
# Verificar servicio activo
/ip service print

# Verificar firewall no bloquea
/ip firewall filter print where chain=input

# Test desde MikroTik (instalar curl si está disponible)
/tool fetch url="http://127.0.0.1:8728" mode=http
```

**Problema: Address-list no aplica bloqueo**
```routeros
# Verificar orden de reglas
/ip firewall filter print where chain=forward

# Las reglas de address-list deben estar ANTES que accept all
# Usar place-before para reordenar
```

**Problema: Queues no limitan velocidad**
```routeros
/queue simple print detail

# Verificar:
# - target correcto (IP del dispositivo)
# - max-limit en formato correcto: "upload/download" (ej: 5M/10M)
# - queue no deshabilitado (disabled=no)
```

---

## 14. MANUALES DE DESPLIEGUE

### 14.1 Despliegue en Windows Server

#### 14.1.1 Requisitos Previos

**Hardware mínimo:**
- Windows Server 2019/2022
- 4GB RAM
- 20GB disco
- Conectividad IP con routers MikroTik

**Software:**
- Python 3.11+ (https://www.python.org/downloads/windows/)
- Git for Windows (https://git-scm.com/download/win)
- Node.js 18+ (https://nodejs.org/) - para build frontend
- IIS 10+ (incluido en Windows Server)

#### 14.1.2 Instalación Backend

**Paso 1: Instalar Python**
```powershell
# Descargar Python 3.11 desde python.org
# Durante instalación:
# - Marcar "Add Python to PATH"
# - Marcar "Install pip"

# Verificar instalación
python --version
pip --version
```

**Paso 2: Clonar/copiar proyecto**
```powershell
# Crear directorio
mkdir C:\SmartControl
cd C:\SmartControl

# Si usas Git
git clone <repository-url> .

# O copiar archivos manualmente
```

**Paso 3: Crear entorno virtual**
```powershell
cd C:\SmartControl\backend
python -m venv venv

# Activar entorno
.\venv\Scripts\Activate.ps1

# Si hay error de permisos:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Paso 4: Instalar dependencias**
```powershell
pip install -r requirements.txt
```

**Paso 5: Configurar variables de entorno**
```powershell
# Crear archivo .env en backend\
@"
DATABASE_URL=sqlite:///./smartbjportal.db
SECRET_KEY=tu-secreto-super-seguro-cambiar-en-produccion
DEBUG=false
ALLOWED_ORIGINS=http://localhost,http://tu-dominio.com
"@ | Out-File -FilePath .env -Encoding UTF8
```

**Paso 6: Inicializar base de datos**
```powershell
python scripts/migrate.js  # Crear tablas
python scripts/seed.js     # Usuario admin default
```

**Paso 7: Probar manualmente**
```powershell
uvicorn src.main:app --host 0.0.0.0 --port 8000

# Abrir navegador: http://localhost:8000/docs
# Debe mostrar Swagger UI
```

#### 14.1.3 Configurar como Servicio Windows

**Opción A: NSSM (Recomendado)**

```powershell
# Descargar NSSM: https://nssm.cc/download
cd C:\Tools
Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile nssm.zip
Expand-Archive nssm.zip
cd nssm\win64

# Instalar servicio
.\nssm.exe install SmartControlAPI "C:\SmartControl\backend\venv\Scripts\python.exe" `
    "C:\SmartControl\backend\venv\Scripts\uvicorn.exe" `
    "src.main:app --host 0.0.0.0 --port 8000"

# Configurar directorio de trabajo
.\nssm.exe set SmartControlAPI AppDirectory "C:\SmartControl\backend"

# Configurar reinicio automático
.\nssm.exe set SmartControlAPI AppExit Default Restart

# Iniciar servicio
Start-Service SmartControlAPI

# Verificar estado
Get-Service SmartControlAPI
```

**Opción B: Task Scheduler**

```powershell
$action = New-ScheduledTaskAction -Execute "C:\SmartControl\backend\venv\Scripts\python.exe" `
    -Argument "C:\SmartControl\backend\venv\Scripts\uvicorn.exe src.main:app --host 0.0.0.0 --port 8000" `
    -WorkingDirectory "C:\SmartControl\backend"

$trigger = New-ScheduledTaskTrigger -AtStartup

$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask -TaskName "SmartControlAPI" `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Description "SmartControl Backend API"
```

#### 14.1.4 Instalación Frontend

**Paso 1: Build producción**
```powershell
cd C:\SmartControl\frontend
npm install
npm run build

# Genera carpeta dist\ con archivos estáticos
```

**Paso 2: Configurar IIS**

```powershell
# Instalar IIS (si no está instalado)
Install-WindowsFeature -Name Web-Server -IncludeManagementTools

# Instalar URL Rewrite (para React Router)
Invoke-WebRequest -Uri "https://download.microsoft.com/download/1/2/8/128E2E22-C1B9-44A4-BE2A-5859ED1D4592/rewrite_amd64_en-US.msi" -OutFile rewrite.msi
Start-Process msiexec.exe -ArgumentList '/i rewrite.msi /quiet' -Wait

# Crear sitio IIS
Import-Module WebAdministration
New-WebSite -Name "SmartControl" `
    -Port 80 `
    -PhysicalPath "C:\SmartControl\frontend\dist" `
    -ApplicationPool "DefaultAppPool"

# Configurar URL Rewrite para React Router
$webConfig = @"
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <rule name="React Routes" stopProcessing="true">
          <match url=".*" />
          <conditions logicalGrouping="MatchAll">
            <add input="{REQUEST_FILENAME}" matchType="IsFile" negate="true" />
            <add input="{REQUEST_FILENAME}" matchType="IsDirectory" negate="true" />
          </conditions>
          <action type="Rewrite" url="/" />
        </rule>
      </rules>
    </rewrite>
  </system.webServer>
</configuration>
"@

$webConfig | Out-File -FilePath "C:\SmartControl\frontend\dist\web.config" -Encoding UTF8
```

**Paso 3: Configurar proxy reverso a API**

```powershell
# Instalar ARR (Application Request Routing)
Invoke-WebRequest -Uri "https://download.microsoft.com/download/E/9/8/E9849D6A-020E-47E4-9FD0-A023E99B54EB/requestRouter_amd64.msi" -OutFile arr.msi
Start-Process msiexec.exe -ArgumentList '/i arr.msi /quiet' -Wait

# Agregar regla proxy /api/* → localhost:8000
# Editar C:\SmartControl\frontend\dist\web.config:
$webConfigProxy = @"
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <rule name="API Proxy" stopProcessing="true">
          <match url="^api/(.*)" />
          <action type="Rewrite" url="http://localhost:8000/api/{R:1}" />
        </rule>
        <rule name="React Routes" stopProcessing="true">
          <match url=".*" />
          <conditions logicalGrouping="MatchAll">
            <add input="{REQUEST_FILENAME}" matchType="IsFile" negate="true" />
            <add input="{REQUEST_FILENAME}" matchType="IsDirectory" negate="true" />
            <add input="{REQUEST_URI}" pattern="^/api/" negate="true" />
          </conditions>
          <action type="Rewrite" url="/" />
        </rule>
      </rules>
    </rewrite>
  </system.webServer>
</configuration>
"@

$webConfigProxy | Out-File -FilePath "C:\SmartControl\frontend\dist\web.config" -Encoding UTF8 -Force
```

#### 14.1.5 Verificación

```powershell
# Test backend
Invoke-WebRequest -Uri http://localhost:8000/health

# Test frontend
Invoke-WebRequest -Uri http://localhost/

# Test login
$body = @{username="admin"; password="Soporte123!!"} | ConvertTo-Json
Invoke-WebRequest -Uri http://localhost/api/auth/login -Method POST -Body $body -ContentType "application/json"

# Verificar servicios
Get-Service SmartControlAPI
Get-WebSite -Name "SmartControl"
```

#### 14.1.6 Firewall Windows

```powershell
# Abrir puertos si es necesario
New-NetFirewallRule -DisplayName "SmartControl HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
New-NetFirewallRule -DisplayName "SmartControl API" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

---

### 14.2 Despliegue en Ubuntu Server

#### 14.2.1 Requisitos Previos

**Sistema:**
- Ubuntu Server 22.04 LTS o 24.04 LTS
- 4GB RAM
- 20GB disco
- Usuario con sudo

#### 14.2.2 Instalación Backend

**Paso 1: Actualizar sistema**
```bash
sudo apt update
sudo apt upgrade -y
```

**Paso 2: Instalar Python y dependencias**
```bash
sudo apt install -y python3.11 python3.11-venv python3-pip git

# Verificar
python3.11 --version
```

**Paso 3: Crear usuario de servicio**
```bash
sudo useradd -r -m -s /bin/bash smartcontrol
sudo mkdir -p /opt/smartcontrol
sudo chown smartcontrol:smartcontrol /opt/smartcontrol
```

**Paso 4: Clonar proyecto**
```bash
sudo su - smartcontrol
cd /opt/smartcontrol
git clone <repository-url> .

# O copiar archivos
exit
sudo cp -r /ruta/archivos/* /opt/smartcontrol/
sudo chown -R smartcontrol:smartcontrol /opt/smartcontrol
```

**Paso 5: Crear entorno virtual**
```bash
sudo su - smartcontrol
cd /opt/smartcontrol/backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Paso 6: Configurar variables**
```bash
cat > /opt/smartcontrol/backend/.env << EOF
DATABASE_URL=sqlite:///./smartbjportal.db
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=false
ALLOWED_ORIGINS=http://localhost,http://tu-dominio.com
EOF

chmod 600 .env
```

**Paso 7: Inicializar base de datos**
```bash
python scripts/migrate.js
python scripts/seed.js
exit
```

#### 14.2.3 Configurar systemd Service

**Crear archivo de servicio:**
```bash
sudo nano /etc/systemd/system/smartcontrol-api.service
```

**Contenido:**
```ini
[Unit]
Description=SmartControl API Backend
After=network.target

[Service]
Type=simple
User=smartcontrol
Group=smartcontrol
WorkingDirectory=/opt/smartcontrol/backend
Environment="PATH=/opt/smartcontrol/backend/venv/bin"
ExecStart=/opt/smartcontrol/backend/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Habilitar e iniciar:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable smartcontrol-api
sudo systemctl start smartcontrol-api
sudo systemctl status smartcontrol-api

# Ver logs
sudo journalctl -u smartcontrol-api -f
```

#### 14.2.4 Instalación Frontend con Nginx

**Paso 1: Instalar Node.js (para build)**
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Verificar
node --version
npm --version
```

**Paso 2: Build frontend**
```bash
sudo su - smartcontrol
cd /opt/smartcontrol/frontend
npm install
npm run build

# Archivos generados en dist/
exit
```

**Paso 3: Instalar Nginx**
```bash
sudo apt install -y nginx
sudo systemctl enable nginx
```

**Paso 4: Configurar sitio**
```bash
sudo nano /etc/nginx/sites-available/smartcontrol
```

**Contenido:**
```nginx
server {
    listen 80;
    server_name tu-dominio.com;  # Cambiar según dominio/IP

    # Frontend (archivos estáticos React)
    root /opt/smartcontrol/frontend/dist;
    index index.html;

    # Proxy a backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # React Router (SPA)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache estáticos
    location ~* \.(?:css|js|jpg|jpeg|gif|png|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

**Habilitar sitio:**
```bash
sudo ln -s /etc/nginx/sites-available/smartcontrol /etc/nginx/sites-enabled/
sudo nginx -t  # Verificar sintaxis
sudo systemctl restart nginx
```

#### 14.2.5 Configurar SSL con Let's Encrypt (Opcional)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d tu-dominio.com

# Renovación automática (ya configurado por defecto)
sudo systemctl status certbot.timer
```

#### 14.2.6 Firewall (UFW)

```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
sudo ufw status
```

#### 14.2.7 Verificación

```bash
# Test backend
curl http://localhost:8000/health

# Test frontend
curl http://localhost/

# Test login
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Soporte123!!"}'

# Estado servicios
sudo systemctl status smartcontrol-api
sudo systemctl status nginx
```

#### 14.2.8 Logs y Monitoreo

```bash
# Logs backend
sudo journalctl -u smartcontrol-api -f

# Logs Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Logs aplicación (dentro de backend/logs/)
sudo tail -f /opt/smartcontrol/backend/logs/app.log
```

#### 14.2.9 Backups Automáticos

**Crear script:**
```bash
sudo nano /opt/smartcontrol/backup.sh
```

**Contenido:**
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/smartcontrol"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup base de datos
cp /opt/smartcontrol/backend/smartbjportal.db "$BACKUP_DIR/smartbjportal_$DATE.db"

# Mantener solo últimos 7 días
find "$BACKUP_DIR" -name "*.db" -mtime +7 -delete

echo "Backup completado: $DATE"
```

**Programar con cron:**
```bash
sudo chmod +x /opt/smartcontrol/backup.sh
sudo crontab -e

# Agregar línea (backup diario a las 2 AM):
0 2 * * * /opt/smartcontrol/backup.sh >> /var/log/smartcontrol-backup.log 2>&1
```

---

### 14.3 Checklist Post-Instalación

**Para ambos sistemas (Windows/Ubuntu):**

- [ ] Backend ejecutándose en puerto 8000
- [ ] Frontend accesible en puerto 80
- [ ] Login exitoso con admin/Soporte123!!
- [ ] Conectividad a MikroTik (prueba desde dashboard)
- [ ] Address-lists visibles en tabla
- [ ] Crear dispositivo de prueba
- [ ] Asignar plan y verificar queue en MikroTik
- [ ] Bloquear/desbloquear dispositivo
- [ ] Verificar logs en `logs/app.log`
- [ ] Backups configurados (producción)
- [ ] Firewall configurado
- [ ] SSL configurado (producción)
- [ ] Monitoreo/alertas configurado (opcional)

**Comandos útiles:**

**Windows:**
```powershell
# Reiniciar API
Restart-Service SmartControlAPI

# Reiniciar IIS
iisreset

# Ver logs
Get-Content C:\SmartControl\backend\logs\app.log -Tail 50 -Wait
```

**Ubuntu:**
```bash
# Reiniciar API
sudo systemctl restart smartcontrol-api

# Reiniciar Nginx
sudo systemctl restart nginx

# Ver logs
sudo journalctl -u smartcontrol-api -f
```

---

## RESUMEN EJECUTIVO

Este plan define un sistema **completo, modular y escalable** para gestión de red MikroTik con las siguientes características clave:

✅ **API-first**: 95% operaciones por `routeros-api`, SSH solo fallback  
✅ **Multi-router**: Soporte múltiples routers desde DB  
✅ **RBAC**: Admin/Operator/ReadOnly con JWT  
✅ **Persistencia**: SQLite con auditoría completa  
✅ **QoS flexible**: Simple Queues por API, planes asignables  
✅ **Dashboard moderno**: React + TailwindCSS, gráficos, reportes CSV  
✅ **Production-ready**: Logging, backups, circuit breaker, rate limiting  
✅ **Cross-platform**: Windows Server y Ubuntu  

**Próximos pasos:**
1. Aprobar plan
2. Iniciar Fase 1 (MVP) siguiendo backlog
3. Iterar con cliente en Fase 2
