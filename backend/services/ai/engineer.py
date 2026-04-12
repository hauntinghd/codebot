from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, TypedDict

from fastapi import HTTPException
from backend.config import PLAN_MAX_TOKENS_PER_CALL

logger = logging.getLogger("codebot")


# -------------------------------------------------
# Types
# -------------------------------------------------

class FileObject(TypedDict):
    path: str
    content: str


class ProjectObject(TypedDict, total=False):
    project_name: str
    files: List[FileObject]
    commands: List[str]
    notes: str
    _preview: str


# -------------------------------------------------
# Utilities
# -------------------------------------------------

def _sanitize_ascii_lookalikes(text: str) -> str:
    if not text:
        return text

    replacements: Dict[str, str] = {
        "\u043a": "x", "\u0430": "a", "\u043e": "o", "\u0435": "e",
        "\u0440": "p", "\u0441": "c", "\u0443": "y", "\u0445": "x",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


def _safe_json_extract(text: str) -> ProjectObject:
    text = (text or "").strip()
    if not text:
        return {}

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}

    blob = re.sub(r",\s*([}\]])", r"\1", match.group(0))
    try:
        parsed = json.loads(blob)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    return _recover_truncated_files(text)


def _recover_truncated_files(text: str) -> ProjectObject:
    files: List[FileObject] = []
    pattern = re.compile(r'"path"\s*:\s*"([^"]+)"\s*,\s*"content"\s*:\s*"')

    for m in pattern.finditer(text):
        path: str = m.group(1).strip().lstrip("/")
        i: int = m.end()
        buf: List[str] = []

        while i < len(text):
            ch = text[i]
            if ch == "\\" and i + 1 < len(text):
                buf.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                break
            buf.append(ch)
            i += 1

        content = "".join(buf)
        if path.lower() == "index.html" and "</html>" not in content:
            content += "\n</body>\n</html>"

        files.append({"path": path, "content": content})

    if not files:
        return {}

    return {
        "project_name": "generated-project",
        "files": files,
        "commands": [],
        "notes": "Recovered from truncated output",
    }


def _placeholder_file(basename: str, existing: List[FileObject]) -> Optional[FileObject]:
    """Return a minimal placeholder for a missing blueprint file so the project is complete."""
    from datetime import datetime
    year = datetime.now().year
    bl = basename.lower()
    if bl.endswith(".html"):
        title = bl.replace(".html", "").replace("-", " ").replace("_", " ").title()
        # Reuse same css/js path as existing HTML if any
        css_href = "styles.css"
        js_src = "app.js"
        for f in existing:
            p = (f.get("path") or "").lower()
            if "styles" in p and p.endswith(".css"):
                css_href = f["path"].strip().lstrip("/")
                break
        for f in existing:
            p = (f.get("path") or "").lower()
            if "app" in p and p.endswith(".js"):
                js_src = f["path"].strip().lstrip("/")
                break
        content = (
            f'<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{title}</title>\n<link rel="stylesheet" href="{css_href}">\n</head>\n<body>\n'
            f'<header><nav><a href="index.html">Home</a> <a href="products.html">Products</a> <a href="contact.html">Contact</a></nav></header>\n'
            f'<main><h1>{title}</h1><p>Content for {title}.</p></main>\n'
            f'<footer>&copy; {year}</footer>\n<script src="{js_src}"></script>\n</body>\n</html>'
        )
        return {"path": basename, "content": content}
    if bl.endswith(".css"):
        return {"path": basename, "content": "/* Placeholder */\nbody { margin: 0; font-family: sans-serif; }\n"}
    if bl.endswith(".js"):
        # Backend server file vs frontend app
        if "server" in bl:
            content = (
                "const express = require('express');\nconst path = require('path');\nconst app = express();\n"
                "app.use(express.json());\napp.use(express.static(path.join(__dirname, '.')));\n"
                "app.get('/api/products', (req, res) => res.json([]));\n"
                "const PORT = process.env.PORT || 3000;\napp.listen(PORT, () => console.log('Server on', PORT));\n"
            )
            return {"path": basename, "content": content}
        content = (
            "document.addEventListener('DOMContentLoaded', function() {\n"
            "  if (typeof setupNavigation === 'function') setupNavigation();\n"
            "  if (typeof setupButtons === 'function') setupButtons();\n"
            "  if (typeof setupCart === 'function') setupCart();\n"
            "  if (typeof setupAuth === 'function') setupAuth();\n"
            "  if (typeof setupMobileMenu === 'function') setupMobileMenu();\n"
            "});\n"
        )
        return {"path": basename, "content": content}
    if bl == "package.json":
        return {"path": basename, "content": '{"name":"generated-project","version":"1.0.0","scripts":{"start":"node server.js"},"dependencies":{"express":"^4.18.0"}}\n'}
    if bl == ".env.example":
        return {"path": basename, "content": "PORT=3000\nSTRIPE_SECRET_KEY=\nSTRIPE_WEBHOOK_SECRET=\nSESSION_SECRET=\n"}
    if bl == "readme.md":
        return {"path": basename, "content": "# Generated Project\n\n1. Copy .env.example to .env and set values.\n2. Run: npm install && npm start.\n3. Open http://localhost:3000\n"}
    return None


def _render_files_preview(files: List[FileObject], max_chars: int = 9000) -> str:
    out: List[str] = []
    used: int = 0

    for f in files:
        block = f"\n\n### {f['path']}\n{f['content']}"
        if used + len(block) > max_chars:
            out.append(block[: max_chars - used] + "\n\n...[truncated]")
            break
        out.append(block)
        used += len(block)

    return "Generated project files preview:" + "".join(out)


# -------------------------------------------------
# Core Generator
# -------------------------------------------------

async def generate_code(
    user_request: str,
    blueprint: Dict[str, Any],
    file_context: Optional[str],
    chat_history: Optional[List[Dict[str, Any]]],
    api_client: Any,
    model: str,
    user_plan: str = "none",
    user_id: Optional[str] = None,
) -> ProjectObject:

    from datetime import datetime

    current_year: int = datetime.now().year

    plan_cap: int = max(
        int(PLAN_MAX_TOKENS_PER_CALL.get(str(user_plan), 16384)),
        131072,
    )

    SYSTEM_PROMPT = f"""
You are CodeBot Engineer, an expert full-stack engineer. Build complete, Bolt.new-competitive websites. Every file and every button must work. No placeholders.

OUTPUT FORMAT: Output ONLY one valid JSON object. The JSON must have a "files" array; each element is {{ "path": "relative/path/to/file", "content": "COMPLETE file contents" }}. You MUST output the COMPLETE content of every file — never partial content, never "rest of code remains the same", never truncation. Think step by step: list the files you will create, then output each file in full. Consider the BLUEPRINT file list as the source of truth for which files to create.

OUTPUT ONLY ONE VALID JSON OBJECT.

FILE CHECKLIST (MANDATORY):
- You MUST output EVERY file in BLUEPRINT.files_to_edit. If the blueprint lists 15 files, you output 15 files. Do not skip any.
- Frontend minimum: index.html, styles.css, app.js. For e-commerce/multi-page also include: products.html, contact.html, featured.html, content.html, terms.html (and any others in the blueprint).
- When the blueprint includes backend files (server.js, package.json, .env.example, README.md), you MUST output them with real, runnable code. Frontend and backend together form one deliverable.
- Every HTML file MUST have <link rel="stylesheet" href="styles.css"> (or css/styles.css) and <script src="app.js"></script> (or js/app.js). Use the same path in all pages.
- Put ALL frontend CSS in one styles.css file. Put ALL frontend JavaScript in one app.js file. No inline scripts for behavior (only JSON data in HTML is OK). Backend code goes in server.js (and optional db.js, auth.js).

JSON FORMAT:
{{
  "project_name": "string",
  "files": [ {{ "path": "index.html", "content": "..." }}, {{ "path": "styles.css", "content": "..." }}, {{ "path": "app.js", "content": "..." }}, ... every file in blueprint ],
  "commands": [],
  "notes": ""
}}

BUTTON AND LINK BEHAVIOR (MANDATORY — EVERY BUTTON MUST WORK):
- Nav links: Every <a> in the header/nav MUST have href pointing to a file you generate (e.g. href="index.html", href="products.html", href="contact.html") or href="#section-id" that exists on the current page. No # or javascript:void(0) placeholders.
- "Shop Now" / "Discover" / "View Collection": Must either link to products.html or scroll to the products section on the same page. Implement with addEventListener or onclick that does location.href='products.html' or element.scrollIntoView({{behavior:'smooth'}}).
- "Add to Cart": Must call a function that adds the item to a cart (array or object), updates a cart count in the DOM, and optionally stores in localStorage. No alert('Added') only — update the UI.
- "Contact" / "Get in Touch": Must link to contact.html or scroll to #contact.
- "Featured" / "Collections": Must link to featured.html or products.html or scroll to a real section.
- Hamburger menu (mobile): Must toggle a class or display on the nav so the menu opens and closes. Attach click handler in app.js.
- Every button must have a real click handler defined in app.js. NO empty onclick, NO alert('Coming soon'), NO console.log as the only action.

REQUIRED IN app.js (MUST EXIST AND WIRE EVERYTHING):
- setupNavigation(): Loop over all nav links (document.querySelectorAll('header a, nav a') or similar). For each, if href ends with .html leave as-is; if href is #id, add click handler to preventDefault and scroll to document.getElementById(id). Call from DOMContentLoaded.
- setupButtons(): Find every button and CTA link. Attach click handlers: "Add to Cart" -> addToCart(...), "Shop"/"Discover" -> go to products.html or scroll to products section, "Contact" -> go to contact.html, etc. Call from DOMContentLoaded.
- setupCart(): Initialize cart (array), load from localStorage if present, render cart count in header. Expose addToCart(name, price, id) that pushes to cart, saves to localStorage, updates count. Call from DOMContentLoaded.
- setupAuth(): If you have login/signup buttons, show a simple modal or redirect; otherwise no-op. Call from DOMContentLoaded.
- setupMobileMenu(): Find hamburger button and nav; on hamburger click toggle class (e.g. .open) on nav so it shows/hides. Call from DOMContentLoaded.

FULL-STACK (when BLUEPRINT.files_to_edit includes server.js, package.json, or README.md):
- Backend: Node Express server (server.js) that:
  - Serves static frontend files (express.static) and API routes.
  - GET /api/products — return product catalog (from in-memory array or SQLite; seed 10–20 items with name, price, description, image URL).
  - POST /api/register — create account (username, password); hash password with bcrypt; store users in memory or SQLite; return session/JWT.
  - POST /api/login — verify password with bcrypt; return session/JWT.
  - POST /api/create-checkout-session — accept cart items (id, quantity, price); create Stripe Checkout Session with line_items; return session.url for redirect. Use Stripe SDK (require('stripe')). Protect: only create session if inventory allows.
  - POST /webhook — Stripe webhook (raw body); verify signature with stripe.webhooks.constructEvent; on checkout.session.completed create order and reduce inventory; respond 200.
  - Use environment variables: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, SESSION_SECRET (or JWT secret), PORT. Never hardcode secrets.
- package.json: dependencies must include express, stripe, bcrypt (or bcryptjs), cookie-parser and/or jsonwebtoken if using sessions/JWT. Script: "start": "node server.js".
- .env.example: list STRIPE_SECRET_KEY=, STRIPE_WEBHOOK_SECRET=, SESSION_SECRET=, PORT=3000.
- README.md: clear run instructions: 1) Copy .env.example to .env and fill keys. 2) npm install && npm start. 3) For webhooks: stripe listen --forward-to localhost:PORT/webhook. 4) Frontend: open index.html or point to backend URL. Include seed product data or how to add products.
- Frontend (when backend exists): Cart "Checkout" button must POST cart to /api/create-checkout-session and redirect user to the returned Stripe URL. Login/Register forms must POST to /api/register and /api/login and store session/token. Product catalog can be fetched from GET /api/products or embedded in app.js; filters/sort/search on products page must work.
- Luxury e-commerce: If the user asks for a luxury brand (e.g. high-end handbags, Maison-style), follow their visual and copy guidelines: gray gradient theme, serif+sans typography, large whitespace, 6 pages (Home, Featured, Products, Content, Contact, ToS), trust cues, product detail with gallery and Add to Cart, USD pricing. Seed products with realistic names and prices ($2k–$12k range if specified).

OTHER:
- Use Unsplash images only for frontend. Responsive (viewport, media queries). Copyright year: {current_year}.
"""

    messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    if chat_history:
        for m in chat_history[-6:]:
            messages.append({
                "role": str(m.get("role", "user")),
                "content": str(m.get("content", ""))[:2000],
            })

    if file_context:
        messages.append({
            "role": "user",
            "content": f"FILE CONTEXT (read-only):\n{file_context[:12000]}",
        })

    files_checklist = blueprint.get("files_to_edit") or []
    if not isinstance(files_checklist, list):
        files_checklist = []
    checklist_text = "You MUST output exactly these files (every one, no fewer): " + ", ".join(str(f) for f in files_checklist) if files_checklist else "Minimum: index.html, styles.css, app.js, plus any pages the user asked for."
    messages.append({
        "role": "user",
        "content": f"USER REQUEST:\n{user_request}\n\nBLUEPRINT:\n{json.dumps(blueprint)}\n\n{checklist_text}",
    })

    try:
        resp = api_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            max_tokens=plan_cap,
            response_format={"type": "json_object"},
        )

        raw_content = resp.choices[0].message.content or ""
        obj: ProjectObject = _safe_json_extract(raw_content)

        files = obj.get("files")
        if not isinstance(files, list) or len(files) < 3:
            raise ValueError("Model did not return required files")

        normalized: List[FileObject] = []
        for f in files:
            if not isinstance(f, dict):
                continue
            path = f.get("path")
            content = f.get("content")
            if not isinstance(path, str) or not isinstance(content, str):
                continue

            clean_path = path.strip().lstrip("/").replace("\\", "/")
            normalized.append({
                "path": clean_path,
                "content": _sanitize_ascii_lookalikes(content),
            })

        # Ensure every file from blueprint is present (fill missing with minimal placeholders)
        _fte: Any = blueprint.get("files_to_edit")
        requested: List[Any] = _fte if isinstance(_fte, list) else []
        if requested:
            def _basename(p: str) -> str:
                return str(p).strip().lstrip("/").replace("\\", "/").split("/")[-1].lower()

            have = {_basename(f["path"]) for f in normalized}
            for req in requested:
                name = _basename(str(req))
                if name in have:
                    continue
                placeholder = _placeholder_file(name, normalized)
                if placeholder:
                    normalized.append(placeholder)
                    have.add(name)

        obj["files"] = normalized
        obj.setdefault("project_name", "generated-project")
        obj["_preview"] = _render_files_preview(normalized)

        return obj

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Engineer generation failed")
        raise HTTPException(
            status_code=502,
            detail=f"Code generation failed: {e}",
        )