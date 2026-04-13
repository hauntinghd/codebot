# Running CodeBot locally (dev-only, will not touch production)

These steps start CodeBot on your local machine in containers and keep production untouched.

1) Review `/.env.local` — it contains safe defaults for local development.

2) (Optional) If you want to use a hostname like `codebot.local` in your browser, add a hosts entry on your dev machine only:

```bash
sudo -- sh -c 'echo "127.0.0.1 codebot.local" >> /etc/hosts'
```

3) Build and run the stack:

```bash
# from repo root
docker compose -f docker-compose.dev.yml up --build
```

4) View logs / open in browser:

```bash
docker compose -f docker-compose.dev.yml logs -f app
# then open http://localhost:3000 or http://codebot.local (if hosts entry added)
```

5) Running DB migrations or seeds (adjust to your stack):

```bash
# open a shell in the running container
docker compose -f docker-compose.dev.yml exec app sh
# then run your app's migrations, e.g.:
# python manage.py migrate
# or alembic upgrade head
# or other framework-specific commands
```

Notes:
- These files are for local dev only. Do NOT copy production `.env` or secrets into `.env.local`.
- If your app uses `uvicorn` / FastAPI or `gunicorn`, change the `CMD` in `Dockerfile.dev` to the appropriate command.
- If `server.py` is not the correct entrypoint, tell me the proper entry (for example `backend/main.py` or a module) and I will update `Dockerfile.dev` accordingly.
