#!/usr/bin/env python3
"""
Codebot monitor server: watches your inputs and Codebot frontend/backend in one place.

Usage:
  1. Start the monitor (from repo root):
     python scripts/codebot-monitor/server.py
     # Optional: also stream backend logs:
     python scripts/codebot-monitor/server.py --backend "uv run uvicorn backend.main:app --reload"

  2. Open http://localhost:38765 in a browser and copy the one-liner.

  3. In the Codebot builder page, open DevTools → Console and paste the one-liner.
     Then use Codebot as usual (paste prompt, click Build). This terminal will show
     a live timeline of your actions and API traffic.

  4. If you passed --backend, backend stdout/stderr appears in the same timeline.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

PORT = 38765
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INJECT_JS_PATH = os.path.join(SCRIPT_DIR, "inject.js")


def log(prefix: str, msg: str, detail: str | None = None) -> None:
    ts = time.strftime("%H:%M:%S", time.localtime())
    line = f"[{ts}] {prefix} {msg}"
    if detail:
        for d in detail.split("\n"):
            line += "\n    " + d
    print(line, flush=True)


class MonitorHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors()
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/inject.js":
            base_url = f"http://localhost:{PORT}"
            if self.headers.get("Host"):
                host = self.headers.get("Host").split(":")[0]
                base_url = f"http://{host}:{PORT}"
            try:
                with open(INJECT_JS_PATH, "r", encoding="utf-8") as f:
                    js = f.read()
            except FileNotFoundError:
                js = "console.error('inject.js not found');"
            js = js.replace("MONITOR_URL_PLACEHOLDER", base_url)
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_cors()
            self.end_headers()
            self.wfile.write(js.encode("utf-8"))
            return

        if path == "/" or path == "/index.html":
            one_liner = (
                "fetch('http://localhost:" + str(PORT) + "/inject.js').then(r=>r.text()).then(eval);"
            )
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Codebot Monitor</title></head>
<body style="font-family: system-ui; max-width: 720px; margin: 2rem auto; padding: 1rem;">
  <h1>Codebot Monitor</h1>
  <p>This server is receiving events. <strong>Watch the terminal</strong> where you started <code>server.py</code> for the live timeline.</p>
  <h2>Attach to Codebot</h2>
  <p>Open the Codebot <strong>builder</strong> page, open DevTools (F12) → Console, and paste this:</p>
  <pre style="background: #f0f0f0; padding: 1rem; overflow: auto;">{one_liner}</pre>
  <p>Then use Codebot (paste prompt, click Build). Your inputs and API calls will appear in the terminal.</p>
</body></html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_cors()
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if urlparse(self.path).path != "/event":
            self.send_response(404)
            self.send_cors()
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        self.send_response(204)
        self.send_cors()
        self.end_headers()

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            log("MONITOR", "invalid JSON in /event")
            return

        source = data.get("source", "?")
        evt_type = data.get("type", "?")

        if source == "user":
            if evt_type == "prompt_paste":
                preview = (data.get("preview") or "").strip()
                preview_short = (preview[:120] + "…") if len(preview) > 120 else preview
                log("USER", f"Pasted prompt ({data.get('length', 0)} chars)", preview_short)
            elif evt_type == "build_click":
                log("USER", f"Clicked Build (prompt length {data.get('promptLength', 0)})")
                if data.get("preview"):
                    log("USER", "Prompt preview:", (data.get("preview") or "")[:200])
            elif evt_type == "prompt_submit":
                log("USER", f"Submitted prompt (Ctrl+Enter, length {data.get('length', 0)})")
            else:
                log("USER", evt_type, json.dumps(data)[:200])
        elif source == "frontend":
            if evt_type == "fetch_start":
                log("FRONTEND", f"→ {data.get('method', '?')} {data.get('url', '?')}")
            elif evt_type == "fetch_end":
                status = data.get("status", "?")
                ok = "ok" if data.get("ok") else "FAIL"
                log("FRONTEND", f"← {status} {ok} ({data.get('ms', 0)} ms) {data.get('url', '')}")
            elif evt_type == "fetch_error":
                log("FRONTEND", f"✗ Error: {data.get('error', '?')} {data.get('url', '')}")
            elif evt_type == "monitor_attached":
                log("FRONTEND", "Monitor attached", data.get("url", ""))
            else:
                log("FRONTEND", evt_type, json.dumps(data)[:200])
        else:
            log(source.upper(), evt_type, json.dumps(data)[:300])

    def log_message(self, format, *args):
        pass  # suppress default request logging


def run_backend_subprocess(cmd: str) -> None:
    """Run backend command and stream stdout/stderr to our log."""
    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert proc.stdout
    for line in proc.stdout:
        line = (line or "").rstrip()
        if line:
            log("BACKEND", line[:200])


def main() -> None:
    global PORT
    parser = argparse.ArgumentParser(description="Codebot monitor: watch inputs + frontend/backend.")
    parser.add_argument(
        "--port",
        type=int,
        default=38765,
        help="Port for monitor HTTP server (default 38765)",
    )
    parser.add_argument(
        "--backend",
        type=str,
        metavar="CMD",
        help="Run this command and stream its output (e.g. 'uv run uvicorn backend.main:app --reload')",
    )
    args = parser.parse_args()
    PORT = args.port

    if args.backend:
        t = threading.Thread(target=run_backend_subprocess, args=(args.backend,), daemon=True)
        t.start()
        time.sleep(0.5)

    log("MONITOR", f"Listening on http://localhost:{PORT} – open in browser for inject snippet.")
    server = HTTPServer(("", PORT), MonitorHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("MONITOR", "Stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
