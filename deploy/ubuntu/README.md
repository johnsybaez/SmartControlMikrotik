# SmartControl - Produccion con MySQL (Ubuntu 24.04)

## Previo a ejecutar
1) Tener un dominio interno o IP privada (ej: 192.168.1.50 o smartcontrol.local).
2) Definir credenciales seguras para DB y `SECRET_KEY`.
3) Tener acceso SSH con un usuario con sudo.
4) Verificar que el repo es accesible (publico o con credenciales).

## Script de deploy
Archivo: `deploy/ubuntu/setup_mysql_production.sh`

### Ejemplo
```bash
sudo bash deploy/ubuntu/setup_mysql_production.sh \
  --repo-url https://github.com/johnsybaez/SmartControlMikrotik.git \
  --domain 192.168.1.50 \
  --db-name smartcontoldb \
  --db-user dbuser \
  --db-pass 'Soport3DB123!!' \
  --secret-key 'REEMPLAZA_CON_UNA_LLAVE_SEGURA' \
  --mt-host 10.80.0.1 --mt-user portal --mt-pass 'Porta123!!'
```

## Que hace el script
- Instala dependencias del sistema y Node.js 20.
- Instala y configura MySQL (DB limpia).
- Clona el repo en `/opt/smartcontrol`.
- Crea `venv` y dependencias Python.
- Genera `.env` de produccion.
- Crea servicio systemd `smartcontrol-backend`.
- Compila el frontend y lo publica en `/var/www/smartcontrol`.
- Configura Nginx como reverse proxy y sirve el frontend.
- Habilita firewall para 22/80/443.

## Verificacion
```bash
systemctl status smartcontrol-backend --no-pager
curl http://127.0.0.1:8000/health
```

## Crear usuario admin (seed)
Si la base esta limpia, ejecuta el seed para crear el usuario `admin`:

```bash
sudo cp /opt/smartcontrol/.env /opt/smartcontrol/backend/.env
sudo chown smartcontrol:smartcontrol /opt/smartcontrol/backend/.env
sudo -u smartcontrol bash -lc "cd /opt/smartcontrol/backend; /opt/smartcontrol/venv/bin/python -m scripts.seed"
```

Credenciales por defecto: `admin / Soporte123`. Cambiala al primer ingreso.

## Notas
- HTTPS con Certbot no se incluye en el script (usar Nginx Proxy Manager).
- El backend queda escuchando en `:8000` y Nginx lo expone via `/api/`.

## Update (git pull + rebuild)
Archivo: `deploy/ubuntu/update_production.sh`

```bash
sudo bash deploy/ubuntu/update_production.sh
```
