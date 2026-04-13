#!/bin/bash
# Manual CodeBot Deployment for Google Cloud VM
# Run this on your Google Cloud VM as: bash deploy-manual.sh

set -e

echo "🚀 CodeBot Manual Deployment"
echo "=============================="
echo ""

# Check if running as omatic657
if [ "$(whoami)" != "omatic657" ]; then
  echo "⚠️  Please run as user: omatic657"
  exit 1
fi

PROJECT_HOME="/home/omatic657/aicoderbot"

echo "📂 Navigating to project directory: $PROJECT_HOME"
cd $PROJECT_HOME || { echo "❌ Project directory not found!"; exit 1; }

echo ""
echo "✅ Installing Python dependencies..."
pip3 install -r requirements.txt -q 2>&1 | grep -v "already satisfied" || true

echo ""
echo "✅ Setting up systemd service..."
sudo cp aicodebot.service /etc/systemd/system/aicodebot.service
sudo systemctl daemon-reload
sudo systemctl enable aicodebot.service

echo ""
echo "⚙️  Starting CodeBot service..."
sudo systemctl restart aicodebot.service

echo ""
echo "⏳ Waiting for service to start..."
sleep 3

echo ""
echo "📊 Checking service status..."
if sudo systemctl is-active --quiet aicodebot.service; then
  echo "✅ Service is RUNNING"
else
  echo "⚠️  Service failed to start. Checking logs..."
  sudo journalctl -u aicodebot.service -n 20
  exit 1
fi

echo ""
echo "📝 Viewing recent logs..."
sudo journalctl -u aicodebot.service -n 10

echo ""
echo "🎉 CodeBot Deployment Complete!"
echo ""
echo "📊 Service Status: $(sudo systemctl is-active aicodebot.service)"
echo "🌐 Access at: https://chatbot.nyptidindustries.com/codebot/dashboard"
echo ""
echo "📋 Useful commands:"
echo "   View logs:       sudo journalctl -u aicodebot.service -f"
echo "   Restart service: sudo systemctl restart aicodebot.service"
echo "   Stop service:    sudo systemctl stop aicodebot.service"
echo "   Service status:  sudo systemctl status aicodebot.service"
