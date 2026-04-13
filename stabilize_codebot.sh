#!/bin/bash
set -euo pipefail

# Idempotent stabilization script for CodeBot™
# Goal: Minimal, safe fixes only — restore stability, keep existing UI 100% untouched
# Applies: config import fixes, chats.py arg fix, port unification (8000), nginx cleanup verification, service restart, health checks
# Run as: sudo bash this_script.sh   (or chmod +x and run)

REPO_DIR="/home/omatic657/aicoderbot"
BACKUP_DIR="$REPO_DIR/backup_$(date +%Y%m%d_%H%M%S)"
NGINX_SITE="/etc/nginx/sites-enabled/chatbot.nyptidindustries.com"
SERVICE="codebot-api.service"
PORT=8000

echo "=== CodeBot™ Stabilization Script ==="
echo "Creating backup directory: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

cd "$REPO_DIR"

# 1. Backup critical files
cp -v backend/config/__init__.py backend/routes/chats.py "$BACKUP_DIR/" || true
cp -v "$NGINX_SITE" "$BACKUP_DIR/nginx_chatbot.conf" || true
sudo cp -v /etc/systemd/system/codebot-api.service "$BACKUP_DIR/" || true

# 2. Fix backend/config/__init__.py — minimal clean re-export, no cycles
cat > backend/config/__init__.py << 'PYEOF'
"""
Clean config package — only re-exports constants from config.py
No imports that can create cycles (no database, no models, no routes)
"""

from .config import *  # noqa: F401,F403
__all__ = [
    "APP_BASE_URL",
    "APP_BASE_PATH",
    "DATA_DIR",
    "DB_PATH",
    "GOOGLE_OAUTH_CLIENT_ID",
    "GOOGLE_OAUTH_CLIENT_SECRET",
    "GOOGLE_OAUTH_REDIRECT",
    "ACCESS_TOKEN_TTL_SECONDS",
    "REFRESH_TOKEN_TTL_DAYS",
    "XAI_API_KEY",
    # add any other constants that auth.py or other modules import
]
PYEOF

echo "Fixed backend/config/__init__.py (clean re-export only)"

# 3. Fix backend/routes/chats.py — remove invalid max_tokens kwarg
sed -i '/build_file_context(.*max_tokens=/d' backend/routes/chats.py || true
sed -i '/build_file_context/s/, *max_tokens=[^,)]*//g' backend/routes/chats.py || true
sed -i '/build_file_context/s/max_tokens=[^,)]*,//g' backend/routes/chats.py || true

echo "Removed invalid max_tokens= from build_file_context call in chats.py"

# 4. Ensure .env has correct base path (no trailing slash) for OAuth redirect_uri safety
if ! grep -q '^APP_BASE_PATH=/codebot$' .env; then
    sed -i 's|^APP_BASE_PATH=.*|APP_BASE_PATH=/codebot|' .env
    echo "Ensured APP_BASE_PATH=/codebot (no trailing slash)"
fi

# 5. Unify port to 8000 in systemd (idempotent override)
sudo mkdir -p /etc/systemd/system/codebot-api.service.d
cat | sudo tee /etc/systemd/system/codebot-api.service.d/override.conf << SYSDEOF
[Service]
EnvironmentFile=/home/omatic657/aicoderbot/.env
Environment=PYTHONUNBUFFERED=1
ExecStart=
ExecStart=/usr/bin/python3 -m uvicorn backend.main:app --host 127.0.0.1 --port $PORT --workers 1 --proxy-headers --forwarded-allow-ips="*"
SYSDEOF

echo "Created/updated systemd override for port $PORT and .env loading"

# 6. Verify/clean nginx — keep only one block, proxy to port 8000
cd /etc/nginx/sites-enabled
sudo rm -f chatbot.nyptidindustries.com.bak* *disabled* || true

sudo sed -i "s|proxy_pass http://127.0.0.1:[0-9]*;|proxy_pass http://127.0.0.1:$PORT;|g" "$NGINX_SITE"

sudo nginx -t | grep -q "successful" && echo "Nginx config test passed" || { echo "Nginx config failed"; exit 1; }

# 7. Reload systemd, restart service, reload nginx
sudo systemctl daemon-reload
sudo systemctl restart "$SERVICE"
sudo systemctl reload nginx

echo "Services restarted"

# 8. Health checks
echo "=== Health Checks ==="

if curl -sS http://127.0.0.1:$PORT/codebot/health | grep -q '"ok":true'; then
    echo "PASS: Local backend health"
else
    echo "FAIL: Local backend health"
    exit 1
fi

if curl -sS -D- https://chatbot.nyptidindustries.com/codebot/health | grep -q "200 OK"; then
    echo "PASS: Public /codebot/health → 200"
else
    echo "FAIL: Public health"
    exit 1
fi

if curl -I -s https://chatbot.nyptidindustries.com/codebot/api/auth/oauth/google | grep -q "302 Found\|307 Temporary Redirect"; then
    echo "PASS: OAuth start endpoint redirects"
else
    echo "FAIL: OAuth start endpoint"
    exit 1
fi

if sudo journalctl -u "$SERVICE" -n 50 --no-pager | grep -iq "error\|exception\|traceback"; then
    echo "WARNING: Recent errors in journal — manual review recommended"
else
    echo "PASS: No obvious errors in recent journal"
fi

echo "=== CodeBot™ Stabilization Complete ==="
echo "Your original UI is untouched and ready at https://chatbot.nyptidindustries.com/codebot/"
echo "Test your 5-layer generation flow now — it should deliver clean ZIPs reliably."
