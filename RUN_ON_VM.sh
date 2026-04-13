#!/bin/bash
# CodeBot Complete Deployment - RUN THIS ON YOUR VM
# Copy-paste this entire block into your VM SSH session

set -e

echo "🚀 CodeBot Final Deployment Starting..."
cd /home/omatic657/aicoderbot

# Step 1: Install dependencies
echo "📦 Step 1/6: Installing Python dependencies..."
pip3 install -r requirements.txt -q 2>&1 | tail -1

# Step 2: Setup systemd service
echo "⚙️  Step 2/6: Setting up systemd service..."
sudo cp aicodebot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable aicodebot.service

# Step 3: Start service
echo "▶️  Step 3/6: Starting CodeBot service..."
sudo systemctl start aicodebot.service

# Step 4: Wait for initialization
echo "⏳ Step 4/6: Waiting for service to initialize..."
sleep 3

# Step 5: Verify service
echo "📊 Step 5/6: Verifying service status..."
if sudo systemctl is-active --quiet aicodebot.service; then
    echo "✅ Service is RUNNING"
else
    echo "❌ Service failed to start - showing logs:"
    sudo journalctl -u aicodebot.service -n 30
    exit 1
fi

# Step 6: Display status
echo ""
echo "=========================================="
echo "✨ Step 6/6: Deployment Complete!"
echo "=========================================="
echo ""
echo "📊 Service Status:"
sudo systemctl status aicodebot.service --no-pager | head -8
echo ""
echo "📝 Recent Logs:"
sudo journalctl -u aicodebot.service -n 10 --no-pager
echo ""
echo "🌐 Access your app at:"
echo "   https://chatbot.nyptidindustries.com/codebot/dashboard"
echo ""
echo "💡 Next steps:"
echo "   1. Verify .env has REAL credentials (not placeholders)"
echo "   2. If .env needs updating, run: nano /home/omatic657/aicoderbot/.env"
echo "   3. Then restart: sudo systemctl restart aicodebot.service"
echo ""
echo "📋 Useful commands:"
echo "   View logs:       sudo journalctl -u aicodebot.service -f"
echo "   Restart service: sudo systemctl restart aicodebot.service"
echo "   Stop service:    sudo systemctl stop aicodebot.service"
echo ""
