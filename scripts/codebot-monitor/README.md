# Codebot Monitor

Watch **your inputs** and **Codebot frontend/backend** in one place while you test (e.g. paste a prompt and run a build).

## Quick start

1. **Start the monitor** (from repo root):

   ```bash
   python scripts/codebot-monitor/server.py
   ```

   Optional: stream backend logs in the same terminal:

   ```bash
   python scripts/codebot-monitor/server.py --backend "uv run uvicorn backend.main:app --reload"
   ```

2. **Open** http://localhost:38765 in a browser and copy the one-liner shown there.

3. **In the Codebot builder page** (where you use the app):
   - Open DevTools (F12) → **Console**
   - Paste the one-liner and press Enter.

4. Use Codebot as usual (paste your prompt, click Build). The **terminal** where the monitor is running will show a live timeline:

   - **USER** – when you paste into the prompt, click Build, or submit with Ctrl+Enter
   - **FRONTEND** – when the app sends requests (e.g. `POST .../builder/run`) and when responses come back (status, timing)
   - **BACKEND** – (only if you used `--backend`) backend log lines

## What gets captured

- **User:** paste into the builder prompt, Build button click, Ctrl+Enter submit (with prompt length/preview).
- **Frontend:** start/end of Codebot API calls (`builder/run`, `builder/npm-install`, projects, auth). Status code and duration for each request.
- **Backend:** stdout/stderr of the command you pass to `--backend`.

## Options

- `--port 38765` – HTTP port (default 38765).
- `--backend "cmd"` – run `cmd` and stream its output into the same log.

## Tips

- Keep the monitor terminal visible while you test so you can see the order of events (your paste → frontend request → backend logs → frontend response).
- If Codebot is on **HTTPS** (e.g. staging), browsers may block loading `http://localhost` from that page (mixed content). Run the monitor on the same machine and use Codebot at `http://localhost` for testing, or run the monitor with HTTPS and use its URL in the one-liner.
