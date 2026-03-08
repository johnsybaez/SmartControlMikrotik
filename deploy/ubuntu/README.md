# SmartControl - Produccion con MySQL (Ubuntu 24.04)

## Objetivo
Este paquete de despliegue deja el sistema con hardening base de prioridad critica:
- CSP en Nginx (no en `index.html`).
- HSTS cuando hay TLS.
- Bloqueo de `.env` y archivos sensibles.
- Rate limiting para `/api/auth/login` (Nginx + backend).
- Servicio `systemd` con restricciones de seguridad.

## Archivos clave
- `deploy/ubuntu/setup_mysql_production.sh`
- `deploy/ubuntu/update_production.sh`
- `deploy/ubuntu/nginx/smartcontrol-hardened-http.conf`
- `deploy/ubuntu/nginx/smartcontrol-hardened-https.conf`
- `deploy/ubuntu/templates/smartcontrol-backend.service`
- `deploy/ubuntu/HARDENING_CHECKLIST.md`

## Instalacion inicial
### Sin TLS (solo red interna)
```bash
sudo bash deploy/ubuntu/setup_mysql_production.sh \
  --repo-url https://github.com/johnsybaez/SmartControlMikrotik.git \
  --domain 192.168.1.50 \
  --db-name smartcontoldb \
  --db-user dbuser \
  --db-pass 'Soport3DB123!!' \
  --secret-key 'CAMBIA_ESTO_POR_UNA_LLAVE_DE_32+_CHARS' \
  --mt-host 10.80.0.1 --mt-user portal --mt-pass 'CAMBIA_ESTO'
```

### Con TLS (recomendado)
```bash
sudo bash deploy/ubuntu/setup_mysql_production.sh \
  --repo-url https://github.com/johnsybaez/SmartControlMikrotik.git \
  --domain app.tudominio.com \
  --db-name smartcontoldb \
  --db-user dbuser \
  --db-pass 'Soport3DB123!!' \
  --secret-key 'CAMBIA_ESTO_POR_UNA_LLAVE_DE_32+_CHARS' \
  --mt-host 10.80.0.1 --mt-user portal --mt-pass 'CAMBIA_ESTO' \
  --tls-cert /etc/letsencrypt/live/app.tudominio.com/fullchain.pem \
  --tls-key /etc/letsencrypt/live/app.tudominio.com/privkey.pem
```

## Update de version
```bash
sudo bash deploy/ubuntu/update_production.sh main
# o rama hardened
sudo bash deploy/ubuntu/update_production.sh SMARTCONTROL2.0
```

## Verificacion rapida
```bash
systemctl status smartcontrol-backend --no-pager
nginx -t
curl http://127.0.0.1:8000/health
```

## Usuario admin (seed)
```bash
sudo cp /opt/smartcontrol/.env /opt/smartcontrol/backend/.env
sudo chown smartcontrol:smartcontrol /opt/smartcontrol/backend/.env
sudo -u smartcontrol bash -lc "cd /opt/smartcontrol/backend; /opt/smartcontrol/venv/bin/python -m scripts.seed"
```
Credenciales iniciales seed: `admin / Soporte123`. Cambiar inmediatamente.
