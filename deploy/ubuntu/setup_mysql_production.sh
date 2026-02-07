#!/usr/bin/env bash
set -euo pipefail

# SmartControl production setup for Ubuntu 24.04 + MySQL/MariaDB
# Usage:
#   sudo bash setup_mysql_production.sh \
#     --repo-url https://github.com/johnsybaez/SmartControlMikrotik.git \
#     --domain app.tudominio.com \
#     --db-name smartcontoldb \
#     --db-user dbuser \
#     --db-pass 'Soport3DB123!!' \
#     --secret-key 'REEMPLAZA_CON_UNA_LLAVE_SEGURA' \
#     --mt-host 10.80.0.1 --mt-user portal --mt-pass 'Porta123!!'

REPO_URL=""
DOMAIN=""
DB_NAME=""
DB_USER=""
DB_PASS=""
SECRET_KEY=""
MT_HOST=""
MT_USER=""
MT_PASS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-url) REPO_URL="$2"; shift 2;;
    --domain) DOMAIN="$2"; shift 2;;
    --db-name) DB_NAME="$2"; shift 2;;
    --db-user) DB_USER="$2"; shift 2;;
    --db-pass) DB_PASS="$2"; shift 2;;
    --secret-key) SECRET_KEY="$2"; shift 2;;
    --mt-host) MT_HOST="$2"; shift 2;;
    --mt-user) MT_USER="$2"; shift 2;;
    --mt-pass) MT_PASS="$2"; shift 2;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
 done

if [[ -z "$REPO_URL" || -z "$DOMAIN" || -z "$DB_NAME" || -z "$DB_USER" || -z "$DB_PASS" || -z "$SECRET_KEY" ]]; then
  echo "Missing required args. See script header for usage." >&2
  exit 1
fi

# 1) System packages
apt update
apt install -y git nginx mysql-server python3.12 python3.12-venv python3.12-dev build-essential libssl-dev libffi-dev pkg-config

# 2) Node.js 20 for frontend build
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt install -y nodejs
fi

# 3) Create app user and folders
if ! id smartcontrol >/dev/null 2>&1; then
  adduser --disabled-password --gecos "" smartcontrol
fi
mkdir -p /opt/smartcontrol /var/lib/smartcontrol /var/www/smartcontrol
chown -R smartcontrol:smartcontrol /opt/smartcontrol /var/lib/smartcontrol /var/www/smartcontrol

# 4) MySQL DB/user
mysql --protocol=socket -uroot <<SQL
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL

# 5) Clone repo
if [[ ! -d /opt/smartcontrol/.git ]]; then
  sudo -u smartcontrol git clone "$REPO_URL" /opt/smartcontrol
else
  sudo -u smartcontrol git -C /opt/smartcontrol pull
fi

# 6) Backend venv + deps
sudo -u smartcontrol python3.12 -m venv /opt/smartcontrol/venv
sudo -u smartcontrol /opt/smartcontrol/venv/bin/pip install --upgrade pip
sudo -u smartcontrol /opt/smartcontrol/venv/bin/pip install -r /opt/smartcontrol/backend/requirements.txt

# 7) .env
cat >/opt/smartcontrol/.env <<ENV
ENVIRONMENT=production
DEBUG=False
RELOAD=False
WORKERS=2

SECRET_KEY=${SECRET_KEY}
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440

CORS_ORIGINS=https://${DOMAIN}

DATABASE_URL=mysql+pymysql://${DB_USER}:${DB_PASS}@127.0.0.1:3306/${DB_NAME}

LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=logs/smartcontrol.log

MT_HOST=${MT_HOST}
MT_USER=${MT_USER}
MT_PASS=${MT_PASS}
ENV

chown smartcontrol:smartcontrol /opt/smartcontrol/.env

# 8) Backend systemd service
cat >/etc/systemd/system/smartcontrol-backend.service <<SERVICE
[Unit]
Description=SmartControl Backend
After=network.target mysql.service

[Service]
User=smartcontrol
WorkingDirectory=/opt/smartcontrol/backend
EnvironmentFile=/opt/smartcontrol/.env
ExecStart=/opt/smartcontrol/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable --now smartcontrol-backend

# 9) Frontend build
sudo -u smartcontrol bash -lc "cd /opt/smartcontrol/frontend; npm ci; npm run build"
rsync -a --delete /opt/smartcontrol/frontend/dist/ /var/www/smartcontrol/

# 10) Nginx
cat >/etc/nginx/sites-available/smartcontrol <<'NGINX'
server {
    listen 80;
    server_name ${DOMAIN};

    root /var/www/smartcontrol;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri /index.html;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/smartcontrol /etc/nginx/sites-enabled/smartcontrol
nginx -t
systemctl enable --now nginx
systemctl reload nginx

# 11) Firewall
ufw allow 22
ufw allow 80
ufw allow 443
ufw --force enable

echo "Done. Backend: systemctl status smartcontrol-backend --no-pager"
echo "Frontend: http://${DOMAIN}"
