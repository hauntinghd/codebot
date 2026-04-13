#!/bin/bash
# CodeBot VM Setup Script (for startup-script or manual execution)

set -e
cd /home/omatic657/aicoderbot

echo "=========================================="
echo "🚀 CodeBot Deployment Starting"
echo "=========================================="

# Step 1: Ensure we have Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt -q 2>&1 | grep -v "already satisfied" | tail -5 || echo "Dependencies ready"

# Step 2: Copy service file
echo "⚙️  Setting up systemd service..."
sudo cp aicodebot.service /etc/systemd/system/aicodebot.service
sudo systemctl daemon-reload

# Step 3: Enable auto-start
echo "🔄 Enabling auto-start on reboot..."
sudo systemctl enable aicodebot.service

# Step 4: Start the service
echo "▶️  Starting CodeBot service..."
sudo systemctl start aicodebot.service

# Step 5: Wait for startup
echo "⏳ Waiting for service to initialize..."
sleep 3

# Step 6: Verify service is running
echo "📊 Checking service status..."
if sudo systemctl is-active --quiet aicodebot.service; then
    echo "✅ Service is RUNNING"
    echo ""
    echo "📝 Recent logs:"
    sudo journalctl -u aicodebot.service -n 15 --no-pager
else
    echo "⚠️  Service failed to start"
    echo ""
    echo "Error details:"
    sudo journalctl -u aicodebot.service -n 30 --no-pager
    exit 1
fi

echo ""
echo "=========================================="
echo "✨ CodeBot Deployment Complete!"
echo "=========================================="
echo ""
echo "🌐 Access your app at:"
echo "   https://chatbot.nyptidindustries.com/codebot/dashboard"
echo ""
echo "📊 Useful commands:"
echo "   View logs:        sudo journalctl -u aicodebot.service -f"
echo "   Restart service:  sudo systemctl restart aicodebot.service"
echo "   Stop service:     sudo systemctl stop aicodebot.service"
echo "   Service status:   sudo systemctl status aicodebot.service"
echo ""
