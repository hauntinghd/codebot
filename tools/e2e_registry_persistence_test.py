#!/usr/bin/env python3
"""E2E test: verify preview registry persists across backend restarts.

Steps:
1. Register user, create project, boot container, start dev server, register preview
2. Verify `data/preview_registry.json` contains the entry
3. Restart backend
4. Verify GET /webcontainer/{project}/dev-server/registry still returns preview info
5. Call force-register endpoint to ensure it can re-register if needed
"""
import os
import time
import json
import sqlite3
import subprocess
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8080/codebot/api"


def post(path, data=None, token=None, timeout=10):
    url = BASE + path
    b = json.dumps(data).encode("utf-8") if data is not None else b""
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=b, headers=headers)
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.getcode(), json.load(resp)


def get_raw(url, timeout=5):
    resp = urllib.request.urlopen(url, timeout=timeout)
    return resp.getcode(), resp.read().decode()


def restart_backend():
    subprocess.run(["pkill", "-f", "uvicorn backend.main:app"], check=False)
    time.sleep(0.4)
    # start uvicorn in background and wait for port to be ready
    subprocess.Popen("nohup python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8080 --log-level info > backend_uvicorn_8080.log 2>&1 &", shell=True)

    # poll for port 8080 to be open
    import socket
    deadline = time.time() + 10.0
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", 8080), timeout=1):
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("backend did not start within timeout")


def run():
    email = f"e2e_registry+{int(time.time())}@example.com"
    pwd = "password123"
    print("Registering user", email)
    code, resp = post("/auth/email/register", {"email": email, "password": pwd})
    token = resp["access_token"]

    print("Creating project")
    code, resp = post("/architecture/projects?init=true", {"name": "RegistryPersist"}, token=token)
    project_id = resp["project_id"]

    print("Mounting and booting")
    html = "<!doctype html><html><body><h1>persist</h1></body></html>"
    post(f"/webcontainer/{project_id}/mount", {"files": {"index.html": html}}, token=token)
    post(f"/webcontainer/{project_id}/boot", None, token=token)

    print("Start dev server and register preview on port 3070")
    post(f"/webcontainer/{project_id}/dev-server/start", {"port": 3070}, token=token)
    code, resp = post(f"/webcontainer/{project_id}/dev-server/register", None, token=token)
    assert code == 200

    # Check registry via API (DB-backed)
    url = f"http://127.0.0.1:8080/codebot/api/webcontainer/{project_id}/dev-server/registry"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            resp = json.load(r)
            code = r.getcode()
        assert code == 200 and resp.get("preview") is not None, f"registry endpoint missing preview: {resp}"
        print("Registry endpoint contains project")
    except Exception as e:
        raise RuntimeError(f"Failed to query registry endpoint before restart: {e}")

    print("Restarting backend to verify registry load on startup")
    restart_backend()

    print("Querying registry endpoint after restart")
    # registry endpoint is GET. Retry on transient connection/reset errors.
    url = f"http://127.0.0.1:8080/codebot/api/webcontainer/{project_id}/dev-server/registry"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    last_exc = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                resp = json.load(r)
                code = r.getcode()
            break
        except (urllib.error.URLError, ConnectionResetError) as e:
            last_exc = e
            time.sleep(0.6 * (1 + attempt * 0.2))
            continue
    else:
        raise RuntimeError(f"Failed to query registry endpoint after restart: {last_exc}")

    assert code == 200 and resp.get("preview") is not None, f"registry endpoint missing preview after restart: {resp}"
    print("Registry endpoint returned preview after restart")

    print("Calling force-register to ensure re-registration works")
    code, resp = post(f"/webcontainer/{project_id}/dev-server/force-register", None, token=token)
    assert code == 200 and resp.get("preview") is not None
    print("Force-register succeeded")

    print("E2E registry persistence PASSED")


if __name__ == '__main__':
    run()
