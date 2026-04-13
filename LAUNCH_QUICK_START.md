# 🚀 CodeBot Quick Start - Tomorrow's Launch

**Date**: February 3, 2026  
**Status**: ✅ PRODUCTION READY

---

## ⚡ Quick Commands

### Start Everything
```bash
cd /home/omatic657/aicoderbot
./start-all-services.sh
```

### Check Status
```bash
# Backend
sudo systemctl status aicodebot.service
curl http://localhost:8000/codebot/health

# Frontend  
ps aux | grep next-server
curl http://localhost:3000/codebot/ | head -20
```

### View Logs
```bash
# Backend logs (live)
sudo journalctl -u aicodebot.service -f

# Frontend logs (live)
tail -f /tmp/nextjs.log

# Last 50 backend messages
sudo journalctl -u aicodebot.service -n 50 --no-pager
```

### Restart Services
```bash
# Backend
sudo systemctl restart aicodebot.service

# Frontend
pkill -f "next-server"
cd apps/codebot-builder && PORT=3000 pnpm start > /tmp/nextjs.log 2>&1 &
```

### Stop Services
```bash
# Backend
sudo systemctl stop aicodebot.service

# Frontend
pkill -f "next-server"
```

---

## 🔗 Important URLs

- **Live Site**: https://chatbot.nyptidindustries.com/codebot
- **API**: https://chatbot.nyptidindustries.com/codebot/api
- **Health Check**: https://chatbot.nyptidindustries.com/codebot/health
- **Login**: https://chatbot.nyptidindustries.com/codebot/login
- **Dashboard**: https://chatbot.nyptidindustries.com/codebot/dashboard
- **Builder**: https://chatbot.nyptidindustries.com/codebot/builder

---

## 💰 Pricing (Ready to Sell)

| Plan | Price | Stripe Price ID |
|------|-------|-----------------|
| **Mars (Basic)** | $50/month | `price_1Sk4SVBL8lRmwao2TwWN730u` |
| **Titan (Pro)** | $250/month | `price_1Sk4SgBL8lRmwao2B9gcRbTg` |

**Key Selling Points**:
- ✅ Multi-layer AI (Router → Engineer → Auditor → Corrector)
- ✅ Bring Your Own API Key (BYOK) - users control their AI costs
- ✅ Google OAuth - easy sign-up
- ✅ Project file uploads (ZIP, code, images, video, audio)
- ✅ Live preview of generated projects
- ✅ Hallucination detection with source citations
- ✅ Credit system with real-time tracking
- ✅ Multiple users can work simultaneously

---

## 🎯 What's Working (100%)

### Core Features ✅
- [x] User authentication (Google OAuth)
- [x] Multi-layer AI code generation
- [x] Chat interface with message history
- [x] File uploads (all types)
- [x] Credit system & tracking
- [x] Stripe billing integration
- [x] BYOK (API key management)
- [x] Rate limiting (60/min per user)
- [x] Project management
- [x] Settings page

### AI Pipeline ✅
- [x] **Router Layer**: Plans approach
- [x] **Engineer Layer**: Generates code
- [x] **Auditor Layer**: Reviews quality
- [x] **Corrector Layer**: Detects hallucinations

### Infrastructure ✅
- [x] Backend (FastAPI) on port 8000
- [x] Frontend (Next.js 16) on port 3000
- [x] Database (SQLite) - 13 tables
- [x] Nginx reverse proxy
- [x] CloudFlare SSL
- [x] Systemd service (auto-restart)

---

## 🔥 Critical Files

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI backend entry point |
| `backend/routes/chat.py` | Chat endpoints with corrector integration |
| `backend/database.py` | Database schema (13 tables) |
| `.env` | Environment variables (secrets) |
| `data/database.db` | SQLite database |
| `apps/codebot-builder/` | Next.js frontend |
| `start-all-services.sh` | Start backend + frontend |
| `aicodebot.service` | Systemd service file |

---

## 📊 Database Quick Access

```bash
cd /home/omatic657/aicoderbot

# View all users
sqlite3 data/database.db "SELECT id, email, plan, subscription_status FROM users;"

# View chats
sqlite3 data/database.db "SELECT c.id, u.email, c.title FROM chats c JOIN users u ON c.user_id = u.id ORDER BY c.updated_at DESC LIMIT 10;"

# View credit balances
sqlite3 data/database.db "SELECT u.email, uc.credits_remaining FROM users u JOIN user_credits uc ON u.id = uc.user_id;"

# Check subscription counts
sqlite3 data/database.db "SELECT subscription_status, COUNT(*) FROM users GROUP BY subscription_status;"
```

---

## 🚨 Troubleshooting

### "Port 8000 already in use"
```bash
sudo pkill -f "uvicorn.*backend.main.*8000"
sudo systemctl start aicodebot.service
```

### "Frontend not loading"
```bash
pkill -f "next-server"
cd apps/codebot-builder
PORT=3000 pnpm start > /tmp/nextjs.log 2>&1 &
```

### "Chat not working"
Check if chat routes are registered:
```bash
curl http://localhost:8000/codebot/api/chats/test-id/messages
# Should return 403 (Forbidden) not 404 (Not Found)
```

### "Database error"
```bash
# Check database file exists
ls -lh data/database.db

# Check integrity
sqlite3 data/database.db "PRAGMA integrity_check;"

# If corrupt, backup and reinitialize
cp data/database.db data/database.db.backup
python3 -c "from backend.database import init_db; init_db()"
```

---

## 📈 First Day Checklist

### Before Launch (Now)
- [x] Backend running
- [x] Frontend running
- [x] Database initialized
- [x] Environment variables set
- [x] Stripe in live mode
- [x] Google OAuth working
- [x] CORS configured
- [x] Domain accessible

### After Launch (Monitor)
- [ ] First user signup
- [ ] First Google OAuth login
- [ ] First chat message
- [ ] First AI response
- [ ] First subscription purchase
- [ ] Stripe webhook receiving events
- [ ] Credits being deducted correctly
- [ ] No errors in logs

### Daily Monitoring
```bash
# Run this daily
cd /home/omatic657/aicoderbot

echo "=== Daily Status Check ==="
date

echo -e "\n1. Services:"
systemctl is-active aicodebot.service
ps aux | grep next-server | grep -v grep > /dev/null && echo "Frontend: Running" || echo "Frontend: DOWN"

echo -e "\n2. Users:"
sqlite3 data/database.db "SELECT COUNT(*) || ' total users' FROM users;"
sqlite3 data/database.db "SELECT COUNT(*) || ' paid subscribers' FROM users WHERE subscription_status IN ('active', 'trialing');"

echo -e "\n3. Activity (last 24h):"
sqlite3 data/database.db "SELECT COUNT(*) || ' new chats' FROM chats WHERE created_at > strftime('%s', 'now', '-1 day');"
sqlite3 data/database.db "SELECT COUNT(*) || ' messages sent' FROM messages WHERE created_at > strftime('%s', 'now', '-1 day');"

echo -e "\n4. Disk Space:"
df -h /home/omatic657/aicoderbot | grep -v Filesystem

echo -e "\n5. Recent Errors:"
sudo journalctl -u aicodebot.service --since "24 hours ago" | grep -i error | tail -5
```

---

## 💡 Tips for Selling

### Pitch
*"CodeBot is an AI code generation platform that uses a sophisticated 4-layer AI system to generate, review, and verify code. Unlike other tools, CodeBot detects hallucinations and provides source citations. With BYOK support, users control their AI costs. Perfect for developers, agencies, and teams."*

### Key Benefits
1. **Multi-layer AI**: Not just one AI call - we route, generate, audit, and verify
2. **BYOK**: Users bring their own OpenAI/Anthropic/xAI key - they control costs
3. **Multiple concurrent users**: $50/month, multiple team members can use it
4. **File uploads**: Supports ZIP projects, code files, images, videos, audio
5. **Live preview**: See generated apps running in real-time
6. **Hallucination detection**: Confidence scores on every response

### Common Questions

**Q: How is this different from ChatGPT?**  
A: CodeBot has 4 AI layers that work together: planning, generation, auditing, and verification. Plus file uploads, project management, and live previews.

**Q: Do users need their own API key?**  
A: Optional! They can use ours (costs credits) or bring their own key (BYOK) for unlimited use.

**Q: Can multiple people use one account?**  
A: Yes! Perfect for teams. One $50/month subscription, whole team can use it.

**Q: What AI models do you support?**  
A: OpenAI (GPT-4, GPT-4o), Anthropic (Claude), xAI (Grok). We use Grok by default.

**Q: Is my code secure?**  
A: Yes. Code is stored in your private database. We use encryption for API keys.

---

## 🎉 You're Ready!

Everything is configured and working. Tomorrow, just:

1. Share the link: `https://chatbot.nyptidindustries.com/codebot`
2. Monitor logs: `sudo journalctl -u aicodebot.service -f`
3. Watch Stripe dashboard for subscriptions
4. Collect that $50/month! 💰

**Good luck with your launch! 🚀**
