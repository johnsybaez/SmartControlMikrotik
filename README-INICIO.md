# SmartControl - Guía de Inicio

## Inicio Rápido

### Opción 1: Iniciar todo (Recomendado)
Ejecuta este comando desde el directorio raíz del proyecto:
```powershell
.\start-all.ps1
```
Esto abrirá dos ventanas de PowerShell:
- Una para el backend (http://localhost:8000)
- Una para el frontend (http://localhost:5173)

### Opción 2: Iniciar servicios por separado

**Backend:**
```powershell
.\start-backend.ps1
```

**Frontend:**
```powershell
.\start-frontend.ps1
```

## URLs del Sistema

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **Documentación API:** http://localhost:8000/docs
- **OpenAPI Schema:** http://localhost:8000/openapi.json

## Credenciales por Defecto

- **Usuario:** admin
- **Contraseña:** admin123

## Problemas Solucionados

### 1. Duplicación de IPs en Address Lists
**Problema:** Las IPs aparecían en múltiples listas (INET_PERMITIDO, INET_LIMITADO, INET_BLOQUEADO) simultáneamente.

**Solución:** Corregido el campo de ID en `api_client.py`. El MikroTik API retorna el campo como `id` (sin punto) pero el código buscaba `.id`.

**Archivo modificado:** `backend/app/mikrotik/api_client.py`
```python
# Antes:
entry_id = entry.get(".id")

# Ahora:
entry_id = entry.get("id") or entry.get(".id")
```

### 2. Backend no cargaba variables de entorno
**Problema:** Uvicorn fallaba con error `SECRET_KEY Field required` cuando se ejecutaba desde directorios incorrectos.

**Solución:** Agregado `load_dotenv()` en `config.py` para cargar automáticamente el archivo `.env` sin importar desde dónde se ejecute.

**Archivo modificado:** `backend/app/core/config.py`
```python
from dotenv import load_dotenv
from pathlib import Path

# Cargar .env automáticamente
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
```

## Estructura del Proyecto

```
SmartControl/
├── backend/               # Backend FastAPI
│   ├── app/
│   │   ├── core/         # Configuración y seguridad
│   │   ├── db/           # Modelos y base de datos
│   │   ├── mikrotik/     # Cliente MikroTik API/SSH
│   │   └── routes/       # Endpoints de la API
│   ├── .env              # Variables de entorno
│   └── requirements.txt  # Dependencias Python
├── frontend/             # Frontend React + Vite
│   ├── src/
│   │   ├── components/   # Componentes React
│   │   ├── pages/        # Páginas de la aplicación
│   │   └── services/     # Cliente API
│   └── package.json      # Dependencias Node
├── .venv/                # Entorno virtual Python
├── start-all.ps1         # Iniciar todo
├── start-backend.ps1     # Iniciar solo backend
└── start-frontend.ps1    # Iniciar solo frontend
```

## Notas Importantes

1. **Siempre ejecuta desde el directorio raíz:** Los scripts están diseñados para ejecutarse desde `C:\SmartControl`

2. **No uses la misma terminal para múltiples servicios:** Los scripts `start-all.ps1` abren ventanas separadas automáticamente para evitar conflictos.

3. **Recarga automática habilitada:** Tanto el backend (uvicorn --reload) como el frontend (Vite HMR) se recargan automáticamente cuando detectan cambios en los archivos.

4. **Puerto 8000 ocupado:** Si obtienes error de puerto ocupado, ejecuta:
   ```powershell
   Stop-Process -Name "python","uvicorn" -Force
   ```

## Desarrollo

Para desarrollo activo, usa ventanas de terminal separadas:
1. Terminal 1: `cd C:\SmartControl; .\start-backend.ps1`
2. Terminal 2: `cd C:\SmartControl; .\start-frontend.ps1`
3. Terminal 3: Para comandos de desarrollo (git, pruebas, etc.)
