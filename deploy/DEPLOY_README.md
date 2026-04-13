# CodeBot - Deploy to chatbot.nyptidindustries.com

## Quick Deploy (on the server)

```bash
cd /home/omatic657/aicoderbot
./deploy-to-production.sh
```

This will:
1. Build the Next.js frontend
2. Install/update systemd services (backend + frontend)
3. Start backend (port 8000) and frontend (port 3000)
4. Install nginx config if not present

## Manual Steps (if needed)

### First-time SSL (Certbot)

If HTTPS is not set up yet:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d chatbot.nyptidindustries.com
```

### Nginx (update config)

```bash
sudo cp deploy/nginx_chatbot_production.conf /etc/nginx/sites-available/chatbot
sudo nginx -t
sudo systemctl reload nginx
```

### Systemd services

```bash
# Backend
sudo cp aicodebot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable aicodebot.service
sudo systemctl restart aicodebot.service

# Frontend (after building)
sudo cp deploy/systemd/codebot-frontend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable codebot-frontend.service
sudo systemctl restart codebot-frontend.service
```

## Architecture

| Component | Port | URL |
|-----------|------|-----|
| Nginx | 443 | https://chatbot.nyptidindustries.com |
| Backend (FastAPI) | 8000 | localhost only |
| Frontend (Next.js) | 3000 | localhost only |

- `/codebot/api/*` → proxied to backend:8000
- `/codebot/*` → proxied to frontend:3000
- `/` → redirect to `/codebot/`

## Environment

Ensure `.env` has:
- `APP_BASE_URL=https://chatbot.nyptidindustries.com`
- `APP_BASE_PATH=/codebot`
- `DEV_MODE=false` (or unset)
- OAuth redirect: `https://chatbot.nyptidindustries.com/codebot/api/auth/oauth/google/callback`

## Troubleshooting

```bash
# Check services
sudo systemctl status aicodebot.service codebot-frontend.service

# Backend logs
sudo journalctl -u aicodebot.service -f

# Frontend logs
tail -f /tmp/nextjs.log

# Health check
curl https://chatbot.nyptidindustries.com/codebot/health
```
