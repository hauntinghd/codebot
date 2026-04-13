#!/usr/bin/env bash
# CodeBot - Deploy to chatbot.nyptidindustries.com
# Run this ON THE SERVER from the project root: ./deploy-to-production.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  CodeBot - Production Deploy"
echo "  chatbot.nyptidindustries.com"
echo "=========================================="
echo ""

# 1. Build frontend
echo "1. Building frontend..."
cd apps/codebot-builder
pnpm build
cd "$SCRIPT_DIR"
echo "   Done."
echo ""

# 2. Install/update systemd services
echo "2. Installing systemd services..."
sudo cp aicodebot.service /etc/systemd/system/
sudo cp deploy/systemd/codebot-frontend.service /etc/systemd/system/
sudo systemctl daemon-reload
echo "   Done."
echo ""

# 3. Enable and start backend
echo "3. Starting backend..."
sudo systemctl enable aicodebot.service
sudo systemctl restart aicodebot.service
sleep 3
if curl -s http://localhost:8000/codebot/health | grep -q ok; then
    echo "   Backend OK (port 8000)"
else
    echo "   WARNING: Backend may not be ready. Check: sudo journalctl -u aicodebot.service -n 20"
fi
echo ""

# 4. Enable and start frontend
echo "4. Starting frontend..."
sudo systemctl enable codebot-frontend.service
sudo systemctl restart codebot-frontend.service
sleep 5
if curl -s http://localhost:3000/codebot/ | head -20 | grep -q -i codebot; then
    echo "   Frontend OK (port 3000)"
else
    echo "   WARNING: Frontend may not be ready. Check: sudo journalctl -u codebot-frontend.service -n 20"
fi
echo ""

# 5. Nginx
echo "5. Nginx configuration"
if [ -f /etc/nginx/sites-available/chatbot ]; then
    echo "   Config exists. To update:"
    echo "   sudo cp deploy/nginx_chatbot_production.conf /etc/nginx/sites-available/chatbot"
    echo "   sudo nginx -t && sudo systemctl reload nginx"
else
    echo "   Installing nginx config..."
    sudo cp deploy/nginx_chatbot_production.conf /etc/nginx/sites-available/chatbot
    sudo ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/chatbot 2>/dev/null || true
    sudo nginx -t && sudo systemctl reload nginx
    echo "   Done."
fi
echo ""

echo "=========================================="
echo "  Deploy complete!"
echo "=========================================="
echo ""
echo "  Live:  https://chatbot.nyptidindustries.com/codebot/"
echo "  Health: https://chatbot.nyptidindustries.com/codebot/health"
echo ""
echo "  Commands:"
echo "    Status:  sudo systemctl status aicodebot.service codebot-frontend.service"
echo "    Logs:    sudo journalctl -u aicodebot.service -f"
echo "    Restart: sudo systemctl restart aicodebot.service codebot-frontend.service"
echo ""
