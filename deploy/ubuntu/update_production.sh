#!/usr/bin/env bash
set -euo pipefail

# Update SmartControl production deployment
# Usage:
#   sudo bash update_production.sh [branch]

BRANCH="${1:-main}"
REPO_DIR="/opt/smartcontrol"
FRONTEND_DIR="$REPO_DIR/frontend"
BACKEND_DIR="$REPO_DIR/backend"
VENV_BIN="$REPO_DIR/venv/bin"

if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "Repo not found at $REPO_DIR" >&2
  exit 1
fi

echo "[1/7] Fetching and updating branch: $BRANCH"
sudo -u smartcontrol git -C "$REPO_DIR" fetch --all
sudo -u smartcontrol git -C "$REPO_DIR" checkout "$BRANCH"
sudo -u smartcontrol git -C "$REPO_DIR" pull --ff-only origin "$BRANCH"

echo "[2/7] Installing backend dependencies"
if [[ -f "$BACKEND_DIR/requirements.txt" ]]; then
  sudo -u smartcontrol "$VENV_BIN/pip" install -r "$BACKEND_DIR/requirements.txt"
fi

echo "[3/7] Building frontend"
if [[ -f "$FRONTEND_DIR/package.json" ]]; then
  sudo -u smartcontrol bash -lc "cd $FRONTEND_DIR && npm ci && npm run build"
  rsync -a --delete "$FRONTEND_DIR/dist/" /var/www/smartcontrol/
fi

echo "[4/7] Validating Nginx config"
nginx -t

echo "[5/7] Restarting backend"
systemctl restart smartcontrol-backend

echo "[6/7] Reloading Nginx"
systemctl reload nginx

echo "[7/7] Running health checks"
if ! curl -fsS http://127.0.0.1:8000/health >/dev/null; then
  echo "Backend health check failed" >&2
  systemctl status smartcontrol-backend --no-pager || true
  exit 1
fi

echo "Update complete."
