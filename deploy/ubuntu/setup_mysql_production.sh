#!/usr/bin/env bash
set -euo pipefail

# SmartControl production setup for Ubuntu 24.04 + MySQL/MariaDB + hardened Nginx/systemd
# Usage:
#   sudo bash setup_mysql_production.sh \
#     --repo-url https://github.com/johnsybaez/SmartControlMikrotik.git \
#     --domain app.tudominio.com \
#     --db-name smartcontoldb \
#     --db-user dbuser \
#     --db-pass 'Soport3DB123!!' \
#     --secret-key 'REEMPLAZA_CON_UNA_LLAVE_SEGURA' \
#     --mt-host 10.80.0.1 --mt-user portal --mt-pass 'CAMBIA_ESTO' \
#     [--tls-cert /etc/letsencrypt/live/app/fullchain.pem --tls-key /etc/letsencrypt/live/app/privkey.pem]

REPO_URL=""
DOMAIN=""
DB_NAME=""
DB_USER=""
DB_PASS=""
SECRET_KEY=""
MT_HOST=""
MT_USER=""
MT_PASS=""
TLS_CERT=""
TLS_KEY=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-url) REPO_URL="$2"; shift 2 ;;
    --domain) DOMAIN="$2"; shift 2 ;;
    --db-name) DB_NAME="$2"; shift 2 ;;
    --db-user) DB_USER="$2"; shift 2 ;;
    --db-pass) DB_PASS="$2"; shift 2 ;;
    --secret-key) SECRET_KEY="$2"; shift 2 ;;
    --mt-host) MT_HOST="$2"; shift 2 ;;
    --mt-user) MT_USER="$2"; shift 2 ;;
    --mt-pass) MT_PASS="$2"; shift 2 ;;
    --tls-cert) TLS_CERT="$2"; shift 2 ;;
    --tls-key) TLS_KEY="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [[ -z "$REPO_URL" || -z "$DOMAIN" || -z "$DB_NAME" || -z "$DB_USER" || -z "$DB_PASS" || -z "$SECRET_KEY" ]]; then
  echo "Missing required args. See script header for usage." >&2
  exit 1
fi

if [[ ${#SECRET_KEY} -lt 32 ]]; then
  echo "SECRET_KEY must be at least 32 chars." >&2
  exit 1
fi

if [[ -n "$TLS_CERT" && ! -f "$TLS_CERT" ]]; then
  echo "TLS cert not found: $TLS_CERT" >&2
  exit 1
fi

if [[ -n "$TLS_KEY" && ! -f "$TLS_KEY" ]]; then
  echo "TLS key not found: $TLS_KEY" >&2
  exit 1
fi

if [[ -n "$TLS_CERT" && -z "$TLS_KEY" ]] || [[ -z "$TLS_CERT" && -n "$TLS_KEY" ]]; then
  echo "You must provide both --tls-cert and --tls-key." >&2
  exit 1
fi

FORCE_HTTPS_VALUE="false"
CORS_ORIGINS_VALUE="http://${DOMAIN}"
if [[ -n "$TLS_CERT" && -n "$TLS_KEY" ]]; then
  FORCE_HTTPS_VALUE="true"
  CORS_ORIGINS_VALUE="https://${DOMAIN}"
fi

apt update
apt install -y git nginx mysql-server python3.12 python3.12-venv python3.12-dev build-essential libssl-dev libffi-dev pkg-config rsync curl

if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt install -y nodejs
fi

if ! id smartcontrol >/dev/null 2>&1; then
  adduser --disabled-password --gecos "" smartcontrol
fi

mkdir -p /opt/smartcontrol /var/lib/smartcontrol /var/www/smartcontrol
chown -R smartcontrol:smartcontrol /opt/smartcontrol /var/lib/smartcontrol /var/www/smartcontrol

mysql --protocol=socket -uroot <<SQL
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL

if [[ ! -d /opt/smartcontrol/.git ]]; then
  sudo -u smartcontrol git clone "$REPO_URL" /opt/smartcontrol
else
  sudo -u smartcontrol git -C /opt/smartcontrol pull --ff-only
fi

sudo -u smartcontrol python3.12 -m venv /opt/smartcontrol/venv
sudo -u smartcontrol /opt/smartcontrol/venv/bin/pip install --upgrade pip
sudo -u smartcontrol /opt/smartcontrol/venv/bin/pip install -r /opt/smartcontrol/backend/requirements.txt

cat >/opt/smartcontrol/.env <<ENV
APP_NAME=SmartControl
APP_VERSION=1.0.0
ENVIRONMENT=production
DEBUG=False
RELOAD=False
HOST=127.0.0.1
PORT=8000
WORKERS=2

SECRET_KEY=${SECRET_KEY}
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

CORS_ORIGINS=${CORS_ORIGINS_VALUE}
CORS_CREDENTIALS=true
TRUSTED_HOSTS=${DOMAIN},localhost,127.0.0.1
ENABLE_SECURITY_HEADERS=true
FORCE_HTTPS=${FORCE_HTTPS_VALUE}

DATABASE_URL=mysql+pymysql://${DB_USER}:${DB_PASS}@127.0.0.1:3306/${DB_NAME}

LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=logs/smartcontrol.log

MT_HOST=${MT_HOST}
MT_USER=${MT_USER}
MT_PASS=${MT_PASS}
MT_SSH_ALLOW_UNKNOWN_HOSTS=false

RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD_SECONDS=60
RATE_LIMIT_LOGIN=5/minute
ENV

chown smartcontrol:smartcontrol /opt/smartcontrol/.env
cp /opt/smartcontrol/.env /opt/smartcontrol/backend/.env
chown smartcontrol:smartcontrol /opt/smartcontrol/backend/.env

install -m 0644 /opt/smartcontrol/deploy/ubuntu/templates/smartcontrol-backend.service /etc/systemd/system/smartcontrol-backend.service
systemctl daemon-reload
systemctl enable --now smartcontrol-backend

sudo -u smartcontrol bash -lc "cd /opt/smartcontrol/frontend && npm ci && npm run build"
rsync -a --delete /opt/smartcontrol/frontend/dist/ /var/www/smartcontrol/

if [[ -n "$TLS_CERT" && -n "$TLS_KEY" ]]; then
  cp /opt/smartcontrol/deploy/ubuntu/nginx/smartcontrol-hardened-https.conf /etc/nginx/sites-available/smartcontrol
  sed -i "s|__DOMAIN__|${DOMAIN}|g" /etc/nginx/sites-available/smartcontrol
  sed -i "s|__SSL_CERT__|${TLS_CERT}|g" /etc/nginx/sites-available/smartcontrol
  sed -i "s|__SSL_KEY__|${TLS_KEY}|g" /etc/nginx/sites-available/smartcontrol
else
  cp /opt/smartcontrol/deploy/ubuntu/nginx/smartcontrol-hardened-http.conf /etc/nginx/sites-available/smartcontrol
  sed -i "s|__DOMAIN__|${DOMAIN}|g" /etc/nginx/sites-available/smartcontrol
fi

ln -sf /etc/nginx/sites-available/smartcontrol /etc/nginx/sites-enabled/smartcontrol
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable --now nginx
systemctl reload nginx

ufw allow 22
ufw allow 80
if [[ -n "$TLS_CERT" ]]; then
  ufw allow 443
fi
ufw --force enable

echo "Deployment complete."
echo "Backend status: systemctl status smartcontrol-backend --no-pager"
echo "Backend health: curl http://127.0.0.1:8000/health"
if [[ -n "$TLS_CERT" ]]; then
  echo "Frontend URL: https://${DOMAIN}"
else
  echo "Frontend URL: http://${DOMAIN}"
fi
