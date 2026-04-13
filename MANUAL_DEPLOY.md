# 🚀 CodeBot Manual Deployment to Google Cloud VM

## Quick Start (Copy-Paste Commands)

Run these commands on your Google Cloud VM (user: `omatic657`):

### Step 1: SSH to Your VM
```bash
gcloud compute ssh aicoderbot-cpu-1 --zone us-central1-c
# Or directly:
ssh omatic657@34.10.77.2
```

### Step 2: Download Latest Code
```bash
cd /home/omatic657/aicoderbot

# Pull latest code (if using git)
git pull origin main

# OR download the tar package from your local machine and upload it:
# On your local machine, run:
# gcloud compute scp /tmp/codebot-deploy.tar.gz omatic657@aicoderbot-cpu-1:/tmp/ --zone=us-central1-c
# Then on VM, extract:
# tar xzf /tmp/codebot-deploy.tar.gz -C /home/omatic657/aicoderbot
```

### Step 3: Update Environment Variables
```bash
# Edit .env with your actual credentials
nano /home/omatic657/aicoderbot/.env

# Update these CRITICAL values:
GOOGLE_CLIENT_ID=<your-actual-google-client-id>
GOOGLE_CLIENT_SECRET=<your-actual-google-client-secret>
OPENAI_API_KEY=sk-<your-actual-openai-key>
STRIPE_SECRET_KEY=sk_live_<your-actual-stripe-key>
STRIPE_PUBLISHABLE_KEY=pk_live_<your-actual-stripe-key>
STRIPE_WEBHOOK_SECRET=whsec_<your-actual-webhook-secret>
SECRET_KEY=<generate-new-random-secure-key-min-32-chars>
```

**To generate SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 4: Install Python Dependencies
```bash
cd /home/omatic657/aicoderbot
pip3 install -r requirements.txt
```

### Step 5: Setup Systemd Service
```bash
# Copy service file
sudo cp /home/omatic657/aicoderbot/aicodebot.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable aicodebot.service
sudo systemctl start aicodebot.service

# Check status
sudo systemctl status aicodebot.service
```

### Step 6: Verify It's Running
```bash
# Check service status
sudo systemctl is-active aicodebot.service

# View logs
sudo journalctl -u aicodebot.service -n 20 -f

# Test API
curl http://localhost:8000/docs
```

### Step 7: Check CloudFlare DNS
Make sure your domain is pointing to the VM IP:
- Go to CloudFlare dashboard
- Verify DNS record for `chatbot.nyptidindustries.com` points to `34.10.77.2`
- SSL/TLS should be "Full (strict)" or "Full"

### Step 8: Access Your App
```
https://chatbot.nyptidindustries.com/codebot/dashboard
```

---

## If Something Goes Wrong

### Service Won't Start
```bash
# Check detailed error
sudo journalctl -u aicodebot.service -n 50

# Check port is available
sudo lsof -i :8000

# Check Python environment
python3 -m venv --help
pip3 --version
```

### Database Locked
```bash
# Remove lock files
rm -f /home/omatic657/aicoderbot/database.db-*

# Restart
sudo systemctl restart aicodebot.service
```

### OAuth Still Shows Error
```bash
# Verify .env file exists and has REAL credentials
cat /home/omatic657/aicoderbot/.env | grep GOOGLE

# If empty, update it:
nano /home/omatic657/aicoderbot/.env

# Restart service
sudo systemctl restart aicodebot.service
```

### Check Logs in Real-Time
```bash
sudo journalctl -u aicodebot.service -f
```

---

## Important Files

- **Config**: `/home/omatic657/aicoderbot/.env`
- **Service**: `/etc/systemd/system/aicodebot.service`
- **Backend**: `/home/omatic657/aicoderbot/backend/`
- **Frontend**: `/home/omatic657/aicoderbot/static/app/`
- **Database**: `/home/omatic657/aicoderbot/database.db`
- **Logs**: View with `sudo journalctl -u aicodebot.service`

---

## Useful Commands

```bash
# View live logs
sudo journalctl -u aicodebot.service -f

# View last 50 lines of logs
sudo journalctl -u aicodebot.service -n 50

# Restart service
sudo systemctl restart aicodebot.service

# Stop service
sudo systemctl stop aicodebot.service

# Check status
sudo systemctl status aicodebot.service

# Enable auto-start on reboot
sudo systemctl enable aicodebot.service

# Disable auto-start
sudo systemctl disable aicodebot.service

# Test API
curl -s http://localhost:8000/docs | head -20
```

---

## Deployment Complete When:

✅ Service shows "active (running)"  
✅ No errors in `journalctl` output  
✅ Can access https://chatbot.nyptidindustries.com/codebot/dashboard  
✅ Google login button is clickable (not disabled)  
✅ No OAuth error messages shown  

---

## Need Help?

1. Check logs: `sudo journalctl -u aicodebot.service -f`
2. Verify .env: `cat /home/omatic657/aicoderbot/.env`
3. Test API: `curl http://localhost:8000/docs`
4. Check port: `sudo lsof -i :8000`
5. Restart service: `sudo systemctl restart aicodebot.service`
