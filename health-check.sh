#!/bin/bash
# CodeBot Health Check Script
# Run this anytime to verify system health

echo "======================================"
echo "   CodeBot Health Check"
echo "   $(date)"
echo "======================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 1. Backend Service
echo "1. Backend Service (FastAPI)"
if systemctl is-active --quiet aicodebot.service; then
    pass "Service is running"
else
    fail "Service is not running"
    echo "   Fix: sudo systemctl start aicodebot.service"
fi

# 2. Backend Health Endpoint
echo ""
echo "2. Backend Health Check"
HEALTH=$(curl -s http://localhost:8000/codebot/health 2>/dev/null)
if echo "$HEALTH" | grep -q '"ok":true'; then
    pass "Health endpoint responding: $HEALTH"
else
    fail "Health endpoint not responding"
    echo "   Check: sudo journalctl -u aicodebot.service -n 20"
fi

# 3. Frontend
echo ""
echo "3. Frontend (Next.js)"
if pgrep -f "next-server" > /dev/null; then
    pass "Next.js process is running"
    FRONTEND=$(curl -s http://localhost:3000/codebot/ 2>/dev/null | head -100)
    if echo "$FRONTEND" | grep -q "CodeBot"; then
        pass "Frontend is responding"
    else
        warn "Frontend running but may not be responding correctly"
    fi
else
    fail "Next.js is not running"
    echo "   Fix: cd apps/codebot-builder && PORT=3000 pnpm start > /tmp/nextjs.log 2>&1 &"
fi

# 4. Database
echo ""
echo "4. Database"
if [ -f "data/codebot.db" ]; then
    DB_SIZE=$(du -h data/codebot.db | cut -f1)
    pass "Database file exists ($DB_SIZE)"
    
    # Check if we can query it
    USER_COUNT=$(sqlite3 data/codebot.db "SELECT COUNT(*) FROM users;" 2>/dev/null)
    if [ $? -eq 0 ]; then
        pass "Database is queryable ($USER_COUNT users)"
    else
        fail "Database exists but cannot be queried"
    fi
else
    fail "Database file not found (looking for data/codebot.db)"
    echo "   Fix: python3 -c 'from backend.database import init_db; init_db()'"
fi

# 5. Environment Variables
echo ""
echo "5. Environment Configuration"
if [ -f ".env" ]; then
    pass ".env file exists"
    
    # Check critical variables
    source .env 2>/dev/null
    
    if [ ! -z "$GOOGLE_OAUTH_CLIENT_ID" ]; then
        pass "Google OAuth configured"
    else
        warn "Google OAuth not configured"
    fi
    
    if [ ! -z "$STRIPE_SECRET_KEY" ]; then
        pass "Stripe configured"
    else
        warn "Stripe not configured"
    fi
    
    if [ ! -z "$XAI_API_KEY" ]; then
        pass "xAI/Grok configured"
    else
        warn "xAI/Grok not configured"
    fi
else
    fail ".env file not found"
fi

# 6. Ports
echo ""
echo "6. Network Ports"
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    pass "Port 8000 (backend) is listening"
else
    fail "Port 8000 (backend) is not listening"
fi

if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    pass "Port 3000 (frontend) is listening"
else
    warn "Port 3000 (frontend) is not listening"
fi

# 7. Disk Space
echo ""
echo "7. Disk Space"
DISK_USAGE=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    pass "Disk usage: ${DISK_USAGE}%"
elif [ $DISK_USAGE -lt 90 ]; then
    warn "Disk usage: ${DISK_USAGE}% (getting high)"
else
    fail "Disk usage: ${DISK_USAGE}% (critical)"
fi

# 8. Recent Errors
echo ""
echo "8. Recent Errors (last 100 lines)"
ERROR_COUNT=$(sudo journalctl -u aicodebot.service -n 100 2>/dev/null | grep -i error | wc -l)
if [ $ERROR_COUNT -eq 0 ]; then
    pass "No recent errors in logs"
elif [ $ERROR_COUNT -lt 5 ]; then
    warn "$ERROR_COUNT errors found in recent logs"
else
    fail "$ERROR_COUNT errors found in recent logs"
    echo "   Check: sudo journalctl -u aicodebot.service -n 100 | grep -i error"
fi

# Summary
echo ""
echo "======================================"
echo "   Summary"
echo "======================================"
echo ""
echo "Live URL: https://chatbot.nyptidindustries.com/codebot"
echo "Backend:  http://localhost:8000/codebot/health"
echo "Frontend: http://localhost:3000/codebot/"
echo ""
echo "Useful Commands:"
echo "  • Restart backend:  sudo systemctl restart aicodebot.service"
echo "  • Backend logs:     sudo journalctl -u aicodebot.service -f"
echo "  • Frontend logs:    tail -f /tmp/nextjs.log"
echo "  • Stop all:         sudo systemctl stop aicodebot.service && pkill -f next-server"
echo ""
