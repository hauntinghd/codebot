#!/usr/bin/env bash
# Deploy Nginx config for chatbot.nyptidindustries.com -> /codebot
# Requires sudo. Usage: sudo ./tools/deploy_nginx_codebot.sh
set -euo pipefail
CONF_SRC="$(pwd)/deploy/nginx_chatbot_nyptidindustries.conf"
SITES_AVAILABLE="/etc/nginx/sites-available/chatbot.nyptidindustries.com"
SITES_ENABLED="/etc/nginx/sites-enabled/chatbot.nyptidindustries.com"
WWW_DIR="/var/www/codebot"

if [ "$EUID" -ne 0 ]; then
  echo "This script must be run as root (sudo)." >&2
  exit 2
fi

if [ ! -f "$CONF_SRC" ]; then
  echo "Missing config source: $CONF_SRC" >&2
  exit 2
fi

# Create web root and copy built frontend (assumes you ran `npm run build` in frontend)
mkdir -p "$WWW_DIR"
# If you have a built frontend at frontend/dist, frontend/build, or static/app, copy it. Try common locations:
if [ -d "frontend/dist" ]; then
  cp -r frontend/dist/* "$WWW_DIR/"
elif [ -d "frontend/build" ]; then
  cp -r frontend/build/* "$WWW_DIR/"
elif [ -d "static/app" ]; then
  cp -r static/app/* "$WWW_DIR/"
elif [ -d "frontend/static/app" ]; then
  cp -r frontend/static/app/* "$WWW_DIR/"
else
  echo "Warning: frontend build not found under frontend/dist, frontend/build, or static/app. Run 'cd frontend && npm run build' first." >&2
fi

# Install config
cp "$CONF_SRC" "$SITES_AVAILABLE"
ln -sf "$SITES_AVAILABLE" "$SITES_ENABLED"

# Test and reload nginx
nginx -t
systemctl reload nginx

echo "Deployed nginx config, web root: $WWW_DIR"
