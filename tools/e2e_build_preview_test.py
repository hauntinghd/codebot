#!/usr/bin/env python3
"""Programmatic E2E test: verify build->preview gating.

Usage: python3 tools/e2e_build_preview_test.py
"""
import urllib.request
import json
import time
import sqlite3
import sys

BASE = "http://127.0.0.1:8080/codebot/api"


def post(path, data=None, token=None, timeout=10):
    url = BASE + path
    b = json.dumps(data).encode("utf-8") if data is not None else b""
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=b, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.getcode(), json.load(resp)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return None, str(e)


def get_raw(url, timeout=5):
    try:
        resp = urllib.request.urlopen(url, timeout=timeout)
        return resp.getcode(), resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return None, str(e)


def run():
    email = f"e2e+{int(time.time())}@example.com"
    pwd = "password123"
    print("[1] Registering user", email)
    code, resp = post("/auth/email/register", {"email": email, "password": pwd})
    assert code == 200, f"register failed: {code} {resp}"
    token = resp["access_token"]

    print("[2] Creating project (init=true)")
    code, resp = post("/architecture/projects?init=true", {"name": "E2E Build Preview"}, token=token)
    assert code == 200, f"create failed: {code} {resp}"
    project_id = resp.get("project_id")
    assert project_id, "no project_id returned"

    preview_url = f"http://127.0.0.1:8080/codebot/api/preview-proxy/{project_id}/"

    print("[3] Confirm preview blocked before build (expect 403)")
    code, body = get_raw(preview_url)
    assert code == 403, f"expected 403 before build, got {code}: {body}"

    print("[4] Mounting index.html")
    html = "<!doctype html><html><body><h1>e2e build preview</h1></body></html>"
    code, resp = post(f"/webcontainer/{project_id}/mount", {"files": {"index.html": html}}, token=token)
    assert code == 200, f"mount failed: {code} {resp}"

    print("[5] Booting container")
    code, resp = post(f"/webcontainer/{project_id}/boot", None, token=token)
    assert code == 200, f"boot failed: {code} {resp}"

    print("[6] Starting dev server on port 3050")
    code, resp = post(f"/webcontainer/{project_id}/dev-server/start", {"port": 3050}, token=token)
    assert code == 200, f"start dev server failed: {code} {resp}"

    print("[7] Registering preview")
    code, resp = post(f"/webcontainer/{project_id}/dev-server/register", None, token=token)
    assert code == 200, f"register preview failed: {code} {resp}"

    print("[8] Confirm still blocked after dev server registered (expect 403)")
    code, body = get_raw(preview_url)
    assert code == 403, f"expected 403 after register but before build, got {code}: {body}"

    print("[9] Marking project built in DB")
    conn = sqlite3.connect("data/codebot.db")
    cur = conn.cursor()
    cur.execute("UPDATE architecture_projects SET built=1 WHERE id=?", (project_id,))
    conn.commit()
    conn.close()

    # wait/poll for backend/preview-proxy to reflect built state
    deadline = time.time() + 10.0
    last_code = None
    last_body = None
    while time.time() < deadline:
        code, body = get_raw(preview_url, timeout=3)
        last_code, last_body = code, body
        if code == 200 and body and "e2e build preview" in body:
            break
        time.sleep(0.5)

    print(f"[10] Final fetch status={last_code}")
    assert last_code == 200, f"expected 200 after built, got {last_code}: {last_body}"
    assert "e2e build preview" in last_body, "preview content mismatch"

    print("E2E PASSED: build->preview gating works as expected")


if __name__ == "__main__":
    try:
        run()
    except AssertionError as e:
        print("E2E FAILED:", e)
        sys.exit(2)
    except Exception as e:
        print("E2E ERROR:", e)
        sys.exit(3)
