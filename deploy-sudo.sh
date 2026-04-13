#!/usr/bin/env bash
# Run with: sudo ./deploy-sudo.sh
# (You'll be prompted for your password once)

set -e
cd /home/omatic657/aicoderbot

echo "Installing systemd services..."
cp aicodebot.service /etc/systemd/system/
cp deploy/systemd/codebot-frontend.service /etc/systemd/system/
systemctl daemon-reload

echo "Enabling and restarting backend..."
systemctl enable aicodebot.service
systemctl restart aicodebot.service

echo "Enabling and restarting frontend..."
systemctl enable codebot-frontend.service
systemctl restart codebot-frontend.service

echo "Updating nginx..."
cp deploy/nginx_chatbot_production.conf /etc/nginx/sites-available/chatbot
ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/chatbot 2>/dev/null || true
nginx -t && systemctl reload nginx

echo ""
echo "Done! https://chatbot.nyptidindustries.com/codebot/"
