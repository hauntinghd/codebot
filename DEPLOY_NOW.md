# 🚀 CODEBOT DEPLOYMENT - FINAL STEP

## You're Almost Done! 

Your CodeBot is built and ready. Just need to run ONE command on your Google Cloud VM.

---

## 📋 What to Do (3 Simple Steps)

### Step 1: SSH to Your VM
```bash
# Using Google Cloud Console SSH button, OR run this in your terminal:
gcloud compute ssh aicoderbot-cpu-1 --zone us-central1-c
```

### Step 2: Run the Deployment Script
Once logged in, copy-paste this command:
```bash
cd /home/omatic657/aicoderbot && bash RUN_ON_VM.sh
```

This will:
- ✅ Install all Python packages
- ✅ Setup systemd service
- ✅ Start CodeBot
- ✅ Verify it's running
- ✅ Show you the logs

### Step 3: Update Credentials (if needed)
If you see OAuth errors, update your credentials:
```bash
nano /home/omatic657/aicoderbot/.env
```

Replace placeholders with real values, then restart:
```bash
sudo systemctl restart aicodebot.service
```

---

## ✅ That's It!

Your CodeBot will then be live at:
```
https://chatbot.nyptidindustries.com/codebot/dashboard
```

---

## 📚 Files Ready on VM

All these files are already in place:
- `backend/` - FastAPI application
- `static/app/` - React frontend (production build)
- `requirements.txt` - Python dependencies
- `aicodebot.service` - Systemd service
- `RUN_ON_VM.sh` - Deployment script
- `.env` - Configuration (with placeholders)

---

## 🎯 Done When:

- ✅ Script completes without errors
- ✅ Service shows "active (running)"
- ✅ Can access your domain
- ✅ Google login button works

---

## 💡 Troubleshooting

If something goes wrong, check logs:
```bash
sudo journalctl -u aicodebot.service -f
```

Or restart:
```bash
sudo systemctl restart aicodebot.service
```

---

**That's all! Go run the script and you're done! 🚀**
