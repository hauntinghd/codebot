# 🚀 CodeBot Deployment Guide - Google Cloud VM

## Prerequisites

- Google Cloud VM instance running (Ubuntu 20.04+)
- SSH access to your VM
- Your domain pointing to VM via CloudFlare
- Python 3.8+, pip, Node.js, npm installed on VM

## Deployment Steps

### Step 1: Prepare Your Google Cloud VM Details

You'll need:
- **VM IP Address** or **Hostname** (e.g., `chatbot.nyptidindustries.com` or `35.xxx.xxx.xxx`)
- **Username** (default: `omatic657`)
- **SSH key** for authentication

### Step 2: Update Deployment Script

Edit `/home/omatic657/aicoderbot/deploy.sh`:

```bash
# Open the script
nano /home/omatic657/aicoderbot/deploy.sh

# Find these lines and update with YOUR values:
GCP_VM_USER="omatic657"
GCP_VM_IP="YOUR_GCP_VM_IP"              # e.g., 35.192.45.123
GCP_VM_HOSTNAME="YOUR_GCP_VM_HOSTNAME"  # e.g., chatbot.nyptidindustries.com
```

### Step 3: Make Script Executable

```bash
chmod +x /home/omatic657/aicoderbot/deploy.sh
```

### Step 4: Run Deployment

```bash
# From your local machine (where you have this code)
bash /home/omatic657/aicoderbot/deploy.sh
```

This will:
- ✅ Create deployment package
- ✅ Upload to Google Cloud VM
- ✅ Extract files
- ✅ Install Python dependencies

### Step 5: Configure on Google Cloud VM

SSH into your VM:

```bash
ssh omatic657@your-vm-ip
```

Update the `.env` file with real credentials:

```bash
# Edit .env
nano /home/omatic657/aicoderbot/.env

# Update these with your actual values:
GOOGLE_CLIENT_ID=your-real-google-client-id
GOOGLE_CLIENT_SECRET=your-real-google-client-secret
OPENAI_API_KEY=sk-your-real-openai-key
STRIPE_SECRET_KEY=sk_live_your-real-stripe-key
STRIPE_PUBLISHABLE_KEY=pk_live_your-real-stripe-key
STRIPE_WEBHOOK_SECRET=whsec_your-real-webhook-secret
SECRET_KEY=generate-a-new-secure-random-key-min-32-chars
```

### Step 6: Setup Systemd Service

On your VM, install the systemd service:

```bash
# Copy service file
sudo cp /home/omatic657/aicoderbot/aicodebot.service /etc/systemd/system/

# Enable service
sudo systemctl daemon-reload
sudo systemctl enable aicodebot.service

# Start service
sudo systemctl start aicodebot.service

# Check status
sudo systemctl status aicodebot.service

# View logs
sudo journalctl -u aicodebot.service -f
```

### Step 7: Verify Deployment

**Access your app at:**
```
https://chatbot.nyptidindustries.com/codebot/dashboard
```

**Check API is running:**
```bash
curl http://your-vm-ip:8000/docs
```

**Monitor logs in real-time:**
```bash
sudo journalctl -u aicodebot.service -f
```

## Troubleshooting

### Service Won't Start
```bash
# Check systemd errors
sudo systemctl status aicodebot.service
sudo journalctl -u aicodebot.service -n 50
```

### Port Already in Use
```bash
# Check what's using port 8000
sudo lsof -i :8000

# If needed, change port in aicodebot.service
```

### Database Locked
```bash
# Remove database lock files
rm -f /home/omatic657/aicoderbot/database.db-*

# Restart service
sudo systemctl restart aicodebot.service
```

### Google OAuth Still Showing Error
Verify `.env` file exists and has actual (not placeholder) credentials:
```bash
cat /home/omatic657/aicoderbot/.env | grep GOOGLE
```

## Maintenance

### View Real-Time Logs
```bash
sudo journalctl -u aicodebot.service -f
```

### Restart Service
```bash
sudo systemctl restart aicodebot.service
```

### Stop Service
```bash
sudo systemctl stop aicodebot.service
```

### Update Code (after pushing changes)
```bash
# From your local machine
bash /home/omatic657/aicoderbot/deploy.sh

# Then on VM:
sudo systemctl restart aicodebot.service
```

## CloudFlare Configuration

Your CloudFlare should:
- **DNS**: Point `chatbot.nyptidindustries.com` → Your VM IP
- **SSL/TLS**: Set to "Full (strict)" for HTTPS
- **Caching**: Configure cache rules for static files
- **Security**: Enable rate limiting to protect API

## Production Checklist

- [x] Frontend built for production
- [ ] Google OAuth credentials set in `.env`
- [ ] OpenAI API key set in `.env`
- [ ] Stripe keys set in `.env`
- [ ] Secret key generated and set in `.env`
- [ ] Database initialized on VM
- [ ] Systemd service installed
- [ ] Service enabled for auto-start
- [ ] CloudFlare DNS configured
- [ ] SSL certificate working
- [ ] App accessible at domain

## 24/7 Operation

Once deployed with systemd service:
- ✅ CodeBot runs 24/7 automatically
- ✅ Auto-restarts on crashes
- ✅ Auto-starts on VM reboot
- ✅ VS Code doesn't need to stay open
- ✅ Your local machine can be shut down
- ✅ CloudFlare provides CDN caching

## Next Steps

1. ✅ Update `deploy.sh` with your VM details
2. ✅ Run deployment script
3. ✅ SSH to VM and configure `.env`
4. ✅ Install systemd service
5. ✅ Test at `https://chatbot.nyptidindustries.com/codebot/dashboard`
6. ✅ Monitor logs
7. ✅ Celebrate! 🎉
