#!/usr/bin/env bash
set -euo pipefail

# Update SmartControl production deployment
# Usage:
#   sudo bash update_production.sh

REPO_DIR="/opt/smartcontrol"
FRONTEND_DIR="$REPO_DIR/frontend"
BACKEND_DIR="$REPO_DIR/backend"
VENV_BIN="$REPO_DIR/venv/bin"

if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "Repo not found at $REPO_DIR" >&2
  exit 1
fi

# Pull latest changes
sudo -u smartcontrol git -C "$REPO_DIR" pull

# Backend deps update (if needed)
if [[ -f "$BACKEND_DIR/requirements.txt" ]]; then
  sudo -u smartcontrol "$VENV_BIN/pip" install -r "$BACKEND_DIR/requirements.txt"
fi

# Frontend build
if [[ -f "$FRONTEND_DIR/package.json" ]]; then
  sudo -u smartcontrol bash -lc "cd $FRONTEND_DIR; npm ci; npm run build"
  rsync -a --delete "$FRONTEND_DIR/dist/" /var/www/smartcontrol/
fi

# Restart backend
systemctl restart smartcontrol-backend

# Reload nginx
systemctl reload nginx

echo "Update complete."
