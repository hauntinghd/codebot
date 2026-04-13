# ⚡ CodeBot - Final Deployment Instructions

## Status: Ready for Final Deployment ✅

All code is built, configured, and ready to deploy to your Google Cloud VM at **34.10.77.2**

---

## 🚀 Copy-Paste Deployment (3 Steps)

### Step 1: SSH to Your VM
Open your terminal and run:
```bash
gcloud compute ssh aicoderbot-cpu-1 --zone us-central1-c
```

OR use the Google Cloud Console → SSH button on your VM instance page.

### Step 2: Run Deployment Script
Once SSH'd into the VM, run:
```bash
cd /home/omatic657/aicoderbot && bash vm-setup.sh
```

This will:
- ✅ Install Python dependencies
- ✅ Copy systemd service file
- ✅ Enable auto-start
- ✅ Start CodeBot service
- ✅ Verify it's running

### Step 3: Update Environment Variables (CRITICAL)
While still SSH'd in, edit the environment file:
```bash
nano /home/omatic657/aicoderbot/.env
```

Replace these placeholder values with your REAL credentials:
```
GOOGLE_CLIENT_ID=<your-actual-google-oauth-client-id>
GOOGLE_CLIENT_SECRET=<your-actual-google-oauth-secret>
OPENAI_API_KEY=sk-<your-actual-openai-api-key>
STRIPE_SECRET_KEY=sk_live_<your-actual-stripe-secret>
STRIPE_PUBLISHABLE_KEY=pk_live_<your-actual-stripe-publishable>
STRIPE_WEBHOOK_SECRET=whsec_<your-actual-webhook-secret>
```

Save with: `Ctrl+X`, then `Y`, then `Enter`

### Step 4: Restart Service with New Credentials
```bash
sudo systemctl restart aicodebot.service
```

### Step 5: Verify It's Working
```bash
sudo journalctl -u aicodebot.service -n 20 -f
```

Press `Ctrl+C` when done viewing logs.

---

## ✅ Deployment Complete When:

- [ ] Service shows "active (running)" in status
- [ ] No errors in logs (no red text)
- [ ] Can access https://chatbot.nyptidindustries.com/codebot/dashboard
- [ ] Google login button works (not disabled)
- [ ] No OAuth error messages shown

---

## 📋 Files Ready on VM

```
/home/omatic657/aicoderbot/
├── backend/                    # Python FastAPI backend
├── static/app/                 # React frontend (production build)
├── requirements.txt            # Python dependencies
├── aicodebot.service          # Systemd service file
├── vm-setup.sh                # Deployment script
├── .env                       # Configuration (needs updating)
└── database.db                # SQLite database (auto-created)
```

---

## 🔧 Useful Commands on VM

```bash
# View live logs
sudo journalctl -u aicodebot.service -f

# Restart service (e.g., after .env changes)
sudo systemctl restart aicodebot.service

# Stop service
sudo systemctl stop aicodebot.service

# Check status
sudo systemctl status aicodebot.service

# View last 50 lines of logs
sudo journalctl -u aicodebot.service -n 50

# Test API (should return 200)
curl -s http://localhost:8000/docs | head -20
```

---

## 🌐 After Deployment

Your CodeBot will be available at:
```
https://chatbot.nyptidindustries.com/codebot/dashboard
```

And will:
- ✅ Run 24/7 automatically (systemd manages it)
- ✅ Auto-restart on crashes
- ✅ Auto-start on VM reboot
- ✅ Work without VS Code open
- ✅ Work with CloudFlare CDN caching

---

## ❌ If Something Goes Wrong

### Service won't start?
```bash
sudo journalctl -u aicodebot.service -n 50
```
Look for error messages and fix issues in `.env`

### Port 8000 already in use?
```bash
sudo lsof -i :8000
# Kill the process if needed:
sudo kill -9 <PID>
```

### Database locked?
```bash
rm -f /home/omatic657/aicoderbot/database.db-*
sudo systemctl restart aicodebot.service
```

### OAuth still shows error?
```bash
# Verify .env has REAL (not placeholder) credentials:
grep GOOGLE /home/omatic657/aicoderbot/.env

# Then restart:
sudo systemctl restart aicodebot.service
```

---

## 📞 Need Help?

1. **Check logs**: `sudo journalctl -u aicodebot.service -f`
2. **Verify .env**: `cat /home/omatic657/aicoderbot/.env | grep OPENAI`
3. **Test API**: `curl http://localhost:8000/docs`
4. **Check process**: `ps aux | grep uvicorn`

---

## Next Steps

1. ✅ Open terminal/CloudShell
2. ✅ SSH to VM: `gcloud compute ssh aicoderbot-cpu-1 --zone us-central1-c`
3. ✅ Run setup: `cd /home/omatic657/aicoderbot && bash vm-setup.sh`
4. ✅ Update .env: `nano /home/omatic657/aicoderbot/.env`
5. ✅ Restart service: `sudo systemctl restart aicodebot.service`
6. ✅ Access: https://chatbot.nyptidindustries.com/codebot/dashboard

---

**CodeBot is ready. Let's go! 🚀**
