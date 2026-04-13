# 🚀 CodeBot Production Ready - Launch Guide

**Status**: ✅ **READY FOR PRODUCTION**

**Last Updated**: February 3, 2026  
**Version**: 1.0.0  
**Launch Date**: Tomorrow

---

## 🎯 Executive Summary

CodeBot is a **production-ready AI code generation platform** with:
- ✅ Multi-layer AI architecture (Router → Engineer → Auditor → Corrector)
- ✅ Google OAuth authentication
- ✅ Stripe billing integration ($50/month plan)
- ✅ BYOK (Bring Your Own Key) support
- ✅ Credit system with real-time tracking
- ✅ Next.js 16 frontend + FastAPI backend
- ✅ Database with 13 tables (SQLite)
- ✅ Verification badges and hallucination detection
- ✅ Live preview support

---

## 🌐 Live URLs

- **Production Site**: https://chatbot.nyptidindustries.com/codebot
- **API Base**: https://chatbot.nyptidindustries.com/codebot/api
- **Health Check**: https://chatbot.nyptidindustries.com/codebot/health

---

## 💰 Pricing Plans

### 🌍 Earth (Free Tier)
- **Price**: $0/month
- **Credits**: Limited
- **Features**: Basic access, rate limited

### 🔴 Mars (Pioneer/Basic)
- **Price**: $50/month
- **Credits**: 10,000/month
- **Stripe Price ID**: `price_1Sk4SVBL8lRmwao2TwWN730u`
- **Features**: Priority queue, BYOK, file uploads

### 🪐 Titan (Voyager/Pro)
- **Price**: $250/month
- **Credits**: 75,000/month
- **Stripe Price ID**: `price_1Sk4SgBL8lRmwao2B9gcRbTg`
- **Features**: Full codebase access, unlimited projects, premium support

---

## 🏗️ System Architecture

### Backend (Python/FastAPI)
- **Port**: 8000
- **Service**: `aicodebot.service` (systemd)
- **Location**: `/home/omatic657/aicoderbot/backend/`
- **Database**: SQLite at `/home/omatic657/aicoderbot/data/database.db`
- **Environment**: `/home/omatic657/aicoderbot/.env`

### Frontend (Next.js 16)
- **Port**: 3000
- **Location**: `/home/omatic657/aicoderbot/apps/codebot-builder/`
- **Base Path**: `/codebot`
- **Build Command**: `cd apps/codebot-builder && pnpm build`
- **Start Command**: `cd apps/codebot-builder && PORT=3000 pnpm start`

### Reverse Proxy (Nginx + CloudFlare)
- Backend API: `https://chatbot.nyptidindustries.com/codebot/api/*` → `http://127.0.0.1:8000/codebot/api/*`
- Frontend: `https://chatbot.nyptidindustries.com/codebot/*` → `http://127.0.0.1:3000/codebot/*`

---

## 🔧 Current Service Status

```bash
# Check backend status
sudo systemctl status aicodebot.service

# Check if Next.js is running
ps aux | grep "next-server"

# Check ports
netstat -tlnp | grep -E ":(8000|3000)"

# Test API health
curl http://localhost:8000/codebot/health
```

**Expected Output**:
```json
{"ok": true}
```

---

## 🚀 Starting the System

### Quick Start (All Services)

```bash
cd /home/omatic657/aicoderbot

# Start backend
sudo systemctl start aicodebot.service

# Start frontend (in background)
cd apps/codebot-builder
PORT=3000 pnpm start > /tmp/nextjs.log 2>&1 &

# Verify both are running
sleep 5
curl http://localhost:8000/codebot/health
curl http://localhost:3000/codebot/ | head -10
```

### Individual Service Control

```bash
# Backend only
sudo systemctl start aicodebot.service
sudo systemctl stop aicodebot.service
sudo systemctl restart aicodebot.service

# Frontend only
cd /home/omatic657/aicoderbot/apps/codebot-builder
PORT=3000 pnpm start

# View logs
sudo journalctl -u aicodebot.service -f
tail -f /tmp/nextjs.log
```

---

## ✅ Pre-Launch Checklist

### Backend ✅
- [x] Database initialized with all 13 tables
- [x] Chat routes registered in main.py
- [x] Corrector layer integrated into chat API
- [x] Google OAuth configured
- [x] Stripe live keys configured
- [x] xAI/Grok API key configured
- [x] BYOK encryption working
- [x] Rate limiting active (60/min per user)
- [x] Health endpoint responding
- [x] Legacy server.py archived

### Frontend ✅
- [x] Next.js build completed successfully
- [x] Base path set to `/codebot`
- [x] Asset prefix configured
- [x] API calls pointing to correct backend
- [x] Authentication flow tested
- [x] Builder interface working
- [x] Dashboard accessible

### Infrastructure ✅
- [x] Backend service running on port 8000
- [x] Frontend running on port 3000
- [x] Nginx reverse proxy configured
- [x] CloudFlare SSL active
- [x] Domain resolving correctly
- [x] CORS headers configured
- [x] Session cookies working

### Security ✅
- [x] JWT secrets configured (secure random)
- [x] Session secrets configured
- [x] Stripe webhook secret configured
- [x] API keys encrypted in database
- [x] HTTPS enforced via CloudFlare
- [x] SameSite=Lax cookies
- [x] Foreign keys enabled in SQLite

---

## 📊 Database Schema

**13 Tables** (fully migrated):
1. `users` - User accounts with Stripe integration
2. `refresh_tokens` - JWT refresh tokens
3. `chats` - Chat sessions
4. `messages` - Chat messages (includes `ai_layer` column)
5. `projects` - Uploaded projects
6. `usage_daily` - Token usage tracking
7. `user_credits` - Credit balances
8. `credit_transactions` - Credit history
9. `file_uploads` - Uploaded files
10. `preview_registry` - Live preview sessions
11. `provider_spend` - Provider spending tracking
12. `provider_spend_daily` - Daily spending breakdown
13. `message_verifications` - Hallucination detection data *(NEW)*

---

## 🔑 Environment Variables

**Critical Variables** (from `.env`):

```bash
# OAuth
GOOGLE_OAUTH_CLIENT_ID=<configured>
GOOGLE_OAUTH_CLIENT_SECRET=<configured>

# Stripe (LIVE MODE)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PRICE_BASIC=price_1Sk4SVBL8lRmwao2TwWN730u
STRIPE_PRICE_PRO=price_1Sk4SgBL8lRmwao2B9gcRbTg
STRIPE_WEBHOOK_SECRET=whsec_...

# AI Provider (xAI/Grok)
XAI_API_KEY=<configured>
DEFAULT_MODEL=grok-4-1-fast-reasoning
ROUTER_MODEL=grok-4-1-fast-reasoning

# Application
APP_BASE_URL=https://chatbot.nyptidindustries.com
APP_BASE_PATH=/codebot
JWT_SECRET=<secure-random>
SESSION_SECRET=<secure-random>

# Database
DB_PATH=data/database.db
```

---

## 🎯 Key Features Working

### 1. Multi-Layer AI Pipeline ✅
- **Router Layer**: Plans the approach (grok-4-1-fast-reasoning)
- **Engineer Layer**: Generates code (user's BYOK or grok-4-1-fast-reasoning)
- **Auditor Layer**: Reviews code quality
- **Corrector Layer**: Detects hallucinations, adds source citations

### 2. Authentication ✅
- Google OAuth 2.0 working
- JWT access tokens (15 min expiry)
- Refresh tokens (30 day expiry)
- Session management via cookies

### 3. Billing ✅
- Stripe integration (LIVE mode)
- Subscription plans active
- Credit system tracking
- Automatic deductions

### 4. BYOK (Bring Your Own Key) ✅
- OpenAI, Anthropic, xAI supported
- Keys encrypted with PBKDF2
- Stored securely in database
- Can be updated via Settings page

### 5. File Uploads ✅
- ZIP files for project context
- Code files (.py, .js, .ts, etc.)
- Images (PNG, WebP)
- Videos (MP4)
- Audio (MP3)

---

## 🔥 Common Operations

### Add a New Admin User

```bash
cd /home/omatic657/aicoderbot
python3 -c "
from backend.database import db
with db() as conn:
    conn.execute('UPDATE users SET is_admin = 1 WHERE email = ?', ('admin@example.com',))
    print('Admin access granted')
"
```

### Check Credit Balance

```bash
python3 -c "
from backend.database import db
with db() as conn:
    rows = conn.execute('SELECT email, credits_remaining FROM users JOIN user_credits ON users.id = user_credits.user_id').fetchall()
    for row in rows:
        print(f'{row[0]}: {row[1]} credits')
"
```

### View Recent Chats

```bash
python3 -c "
from backend.database import db
with db() as conn:
    chats = conn.execute('SELECT c.id, u.email, c.title, c.updated_at FROM chats c JOIN users u ON c.user_id = u.id ORDER BY c.updated_at DESC LIMIT 10').fetchall()
    for chat in chats:
        print(f'{chat[1]}: {chat[2]} (ID: {chat[0]})')
"
```

---

## 🛠️ Troubleshooting

### Backend Won't Start (Port Already in Use)

```bash
# Find and kill the process
sudo lsof -i :8000
sudo pkill -f "uvicorn.*backend.main.*8000"

# Reset and restart
sudo systemctl reset-failed aicodebot.service
sudo systemctl start aicodebot.service
```

### Frontend Not Accessible

```bash
# Check if Next.js is running
ps aux | grep next-server

# Restart frontend
pkill -f "next-server"
cd /home/omatic657/aicoderbot/apps/codebot-builder
PORT=3000 pnpm start > /tmp/nextjs.log 2>&1 &
```

### Database Corruption

```bash
# Backup current database
cp data/database.db data/database.db.backup.$(date +%s)

# Check integrity
sqlite3 data/database.db "PRAGMA integrity_check;"

# If corrupted, restore from backup or reinitialize
# (Warning: reinitialize will lose all data)
rm data/database.db
python3 -c "from backend.database import init_db; init_db()"
```

### Check Logs

```bash
# Backend logs
sudo journalctl -u aicodebot.service -n 100 --no-pager

# Frontend logs
cat /tmp/nextjs.log

# Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

---

## 📈 Monitoring

### Key Metrics to Watch

1. **User Signups**: Check `SELECT COUNT(*) FROM users;`
2. **Active Subscriptions**: Check Stripe dashboard
3. **API Usage**: Check `usage_daily` table
4. **Credit Consumption**: Monitor `credit_transactions`
5. **Error Rate**: Monitor backend logs
6. **Response Times**: Check Nginx access logs

### Daily Health Check Script

```bash
#!/bin/bash
# Save as /home/omatic657/aicoderbot/scripts/health_check.sh

echo "=== CodeBot Health Check ==="
echo "Date: $(date)"
echo ""

# Backend
echo "Backend Status:"
systemctl is-active aicodebot.service
curl -s http://localhost:8000/codebot/health || echo "Backend DOWN!"
echo ""

# Frontend
echo "Frontend Status:"
ps aux | grep "next-server" | grep -v grep > /dev/null && echo "Running" || echo "DOWN!"
curl -s http://localhost:3000/codebot/ > /dev/null && echo "Responding" || echo "Not responding!"
echo ""

# Database
echo "Database:"
ls -lh data/database.db
echo ""

# Disk space
echo "Disk Space:"
df -h /home/omatic657/aicoderbot
echo ""

echo "=== End Health Check ==="
```

---

## 🎉 Launch Readiness

### System is READY if:
- ✅ `curl http://localhost:8000/codebot/health` returns `{"ok": true}`
- ✅ `curl http://localhost:3000/codebot/` returns HTML
- ✅ https://chatbot.nyptidindustries.com/codebot loads the frontend
- ✅ Login with Google OAuth works
- ✅ Stripe subscription flow works
- ✅ Chat messages generate responses

### Pre-Launch Final Steps:

1. **Test End-to-End Flow**:
   - Visit https://chatbot.nyptidindustries.com/codebot
   - Log in with Google
   - Start a new chat
   - Send a message
   - Verify AI response
   - Check credits are deducted

2. **Verify Stripe**:
   - Test subscription purchase (use Stripe test card)
   - Confirm webhook receives events
   - Check user's plan updates in database

3. **Monitor First Hour**:
   - Watch backend logs: `sudo journalctl -u aicodebot.service -f`
   - Watch frontend logs: `tail -f /tmp/nextjs.log`
   - Check Stripe dashboard for payments
   - Monitor user signups

---

## 📞 Support & Maintenance

### Restarting Services After Updates

```bash
# After code changes to backend
sudo systemctl restart aicodebot.service

# After code changes to frontend
cd apps/codebot-builder
pnpm build
pkill -f "next-server"
PORT=3000 pnpm start > /tmp/nextjs.log 2>&1 &
```

### Updating Dependencies

```bash
# Backend (Python)
cd /home/omatic657/aicoderbot
pip install -r requirements.txt

# Frontend (Node)
cd apps/codebot-builder
pnpm install
```

### Database Migrations

If you add new tables/columns, update `backend/database.py` and restart:

```bash
sudo systemctl restart aicodebot.service
```

---

## 🏆 Success Metrics

**Target for Month 1**:
- 🎯 100 signups
- 🎯 10 paid subscribers ($500 MRR)
- 🎯 1,000 AI requests processed
- 🎯 99% uptime
- 🎯 < 2 second average response time

---

## 🚨 Emergency Contacts

- **Server Access**: SSH to `omatic657@chatbot.nyptidindustries.com`
- **Domain Management**: CloudFlare dashboard
- **Payment Issues**: Stripe dashboard
- **Server Issues**: Google Cloud Console

---

**You're ready to launch! 🚀**

The system is production-ready, all services are running, and you can start selling $50/month subscriptions tomorrow!
