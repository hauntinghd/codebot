How to enable nginx proxying for CodeBot (example)

This file shows commands to enable the nginx config created at `deploy/nginx_codebot.conf`.

1. Copy config to nginx sites-available and enable it:

```bash
sudo cp deploy/nginx_codebot.conf /etc/nginx/sites-available/codebot
sudo ln -s /etc/nginx/sites-available/codebot /etc/nginx/sites-enabled/codebot
```

2. Test nginx config and reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

3. Confirm nginx is proxying to backend:

- Ensure backend is running (uvicorn on 127.0.0.1:8080):

```bash
# from repo root
nohup python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8080 --log-level info > backend_uvicorn_8080.log 2>&1 &
```

- Test via curl (from the server):

```bash
curl -I http://127.0.0.1:8080/codebot/health
curl -I http://127.0.0.1:80/codebot/  # nginx should proxy to backend
```

4. SSL (strongly recommended)

Use Certbot to obtain certificates and configure HTTPS. Example for domain `chatbot.nyptidindustries.com`:

```bash
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d chatbot.nyptidindustries.com
```

Certbot will update your nginx config to listen on 443 and redirect HTTP to HTTPS.

5. Troubleshooting

- If you still see the default nginx "Welcome" page:
  - Ensure the `server_name` in `codebot` config matches your request host.
  - Remove or disable the default site (`/etc/nginx/sites-enabled/default`) or make sure the `codebot` config is chosen by nginx (order can matter).

- Logs:
  - Nginx access/error: `/var/log/nginx/codebot-access.log`, `/var/log/nginx/codebot-error.log`
  - Backend: `backend_uvicorn_8080.log`

6. Notes

- This setup proxies `/codebot/` to the backend. The backend serves static files and performs SPA fallback for `/codebot/*` paths.
- If you want static assets served directly by nginx (faster), you can add a `location /codebot/assets/` block with `alias /path/to/repo/static/app/assets/;` before the proxy block.
