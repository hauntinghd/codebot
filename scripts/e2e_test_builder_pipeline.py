#!/usr/bin/env python3
"""
Live E2E test: run the full CodeBot build pipeline (router + engineer) and assert
output is Bolt-competitive (multiple files including index.html, styles.css, app.js, + pages).
Requires XAI_API_KEY in env. Run from repo root: python scripts/e2e_test_builder_pipeline.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

# Load .env from project root
def _load_env():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(root, ".env")
    if os.path.isfile(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v


_load_env()

if not os.environ.get("XAI_API_KEY"):
    print("ERROR: XAI_API_KEY not set. Set it in .env or environment.")
    sys.exit(1)

# Ensure backend is importable
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)


async def run_e2e():
    from backend.routes.builder import _pipeline_build

    prompt = (
        "Build a luxury handbag e-commerce website with home, products, contact, and terms pages. "
        "Include a hero, product grid, and professional styling."
    )
    project_id = "e2e-test-project"
    project_name = "E2E Test"

    print("Running full build pipeline (router -> engineer -> files)...")
    print(f"Prompt: {prompt[:80]}...")

    files_received = []
    error_message = None
    complete = False

    gen = _pipeline_build(prompt, [], "grok-4-1-fast-reasoning", project_id, project_name)
    async for chunk in gen:
        if not chunk.startswith("data: "):
            continue
        try:
            data = json.loads(chunk[5:].strip())
        except json.JSONDecodeError:
            continue
        typ = data.get("type")
        if typ == "file":
            path = data.get("path") or ""
            content = data.get("content") or ""
            if path:
                files_received.append({"path": path, "content": content})
                print(f"  [file] {path} ({len(content)} chars)")
        elif typ == "error":
            error_message = data.get("message") or "Unknown error"
            print(f"  [ERROR] {error_message}")
        elif typ == "complete":
            complete = True

    print()
    paths = [f["path"] for f in files_received]

    # Assertions: Bolt-competitive = at least 4 files, must have index + styles + js + extra page
    failures = []
    if error_message:
        failures.append(f"Pipeline emitted error: {error_message}")
    if not complete:
        failures.append("Pipeline did not emit 'complete' event")
    if len(files_received) < 4:
        failures.append(f"Expected at least 4 files, got {len(files_received)}: {paths}")
    if "index.html" not in paths:
        failures.append("Missing index.html")
    has_css = "styles.css" in paths or any("styles.css" in p for p in paths)
    if not has_css:
        failures.append("Missing styles.css (or path containing styles.css)")
    if not any(p.endswith(".js") for p in paths):
        failures.append("Missing .js file (e.g. app.js)")
    extra_pages = [p for p in paths if p != "index.html" and (".html" in p or ".htm" in p)]
    if not extra_pages:
        failures.append("Missing extra HTML page (e.g. products.html, contact.html)")

    if failures:
        print("E2E TEST FAILED:")
        for f in failures:
            print(f"  - {f}")
        print(f"Files received: {paths}")
        sys.exit(1)

    print("E2E TEST PASSED: Pipeline produced Bolt-competitive output.")
    print(f"  Total files: {len(files_received)}")
    print(f"  Paths: {paths}")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(run_e2e())
