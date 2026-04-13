#!/bin/bash
# CodeBot - Start All Services
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting CodeBot services..."

# Start backend
echo "Starting backend..."
sudo systemctl start aicodebot.service
sleep 3

# Check backend
if curl -s http://localhost:8000/codebot/health | grep -q ok; then
    echo "✓ Backend running on port 8000"
else
    echo "✗ Backend failed to start"
    sudo journalctl -u aicodebot.service -n 20
    exit 1
fi

# Start frontend
echo "Starting frontend..."
if ! pgrep -f "next-server.*3000" > /dev/null; then
    cd apps/codebot-builder
    PORT=3000 pnpm start > /tmp/nextjs.log 2>&1 &
    cd ../..
    sleep 5
fi

# Check frontend
if curl -s http://localhost:3000/codebot/ | head -50 | grep -q CodeBot; then
    echo "✓ Frontend running on port 3000"
else
    echo "✗ Frontend may not be responding"
    echo "Check logs: tail -f /tmp/nextjs.log"
fi

echo ""
echo "✅ CodeBot is ready!"
echo "   Backend:  http://localhost:8000/codebot/health"
echo "   Frontend: http://localhost:3000/codebot/"
echo "   Live:     https://chatbot.nyptidindustries.com/codebot"
