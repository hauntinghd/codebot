"""
Project Type Classifier — determines what the user wants to build.

Runs BEFORE the 5-layer pipeline to configure the build context:
- Which templates/frameworks to use
- Whether image gen is needed (websites/landing pages)
- Whether to scaffold backend (SaaS/API)
- File structure patterns

Categories:
  website        — static site, landing page, portfolio, blog
  web-app        — interactive SPA (React, Vue, Svelte) with state
  saas           — full-stack: auth, billing, dashboard, API
  api            — backend service, REST/GraphQL API
  mobile         — React Native, Flutter, Expo app
  desktop        — Electron, Tauri desktop app
  cli            — command-line tool, script
  library        — npm/pip package, reusable module
  game           — browser game, game logic
  extension      — browser extension, VS Code extension
  bot            — Discord bot, Telegram bot, chatbot
  automation     — cron jobs, scrapers, pipelines
  unknown        — ask user to clarify
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

# Pattern-based classification rules (checked in order, first match wins)
CLASSIFICATION_RULES: List[Tuple[str, List[str], Dict]] = [
    # (project_type, keyword_patterns, config_overrides)

    ("saas", [
        r"saas", r"subscription", r"billing.*dashboard", r"user.*accounts?\s+.*(pay|stripe|billing)",
        r"multi.?tenant", r"pricing\s+page", r"free\s+trial", r"admin\s+panel.*auth",
        r"stripe.*auth.*dashboard", r"login.*signup.*dashboard.*api",
    ], {
        "framework": "nextjs",
        "needs_backend": True,
        "needs_auth": True,
        "needs_billing": True,
        "needs_database": True,
        "needs_images": True,
        "suggested_files": ["app/page.tsx", "app/dashboard/page.tsx", "app/api/auth/route.ts",
                           "app/api/billing/route.ts", "app/pricing/page.tsx", "lib/db.ts"],
    }),

    ("web-app", [
        r"web\s*app", r"single\s*page\s*app", r"spa\b", r"react\s+app", r"vue\s+app",
        r"svelte\s+app", r"next\.?js\s+app", r"dashboard(?!.*billing)", r"admin\s+panel",
        r"crud", r"real.?time", r"form.*submit.*display", r"interactive",
        r"state\s+management", r"todo\s+app", r"task\s+manager", r"kanban",
    ], {
        "framework": "react",
        "needs_backend": False,
        "needs_auth": False,
        "needs_billing": False,
        "needs_database": False,
        "needs_images": False,
        "suggested_files": ["src/App.tsx", "src/components/", "src/hooks/", "src/pages/"],
    }),

    ("api", [
        r"\bapi\b(?!.*website)", r"rest\s*api", r"graphql", r"backend\s+service",
        r"microservice", r"endpoint", r"webhook\s+handler", r"serverless\s+function",
    ], {
        "framework": "fastapi",
        "needs_backend": True,
        "needs_auth": False,
        "needs_billing": False,
        "needs_database": True,
        "needs_images": False,
        "suggested_files": ["main.py", "routes/", "models.py", "database.py"],
    }),

    ("mobile", [
        r"mobile\s+app", r"ios\s+app", r"android\s+app", r"react\s+native",
        r"flutter", r"expo\s+app", r"cross.?platform\s+app",
    ], {
        "framework": "react-native",
        "needs_backend": False,
        "needs_auth": False,
        "needs_billing": False,
        "needs_database": False,
        "needs_images": False,
        "suggested_files": ["App.tsx", "src/screens/", "src/navigation/", "app.json"],
    }),

    ("extension", [
        r"browser\s+extension", r"chrome\s+extension", r"firefox\s+addon",
        r"vs\s*code\s+extension", r"plugin",
    ], {
        "framework": "vanilla",
        "needs_backend": False,
        "needs_auth": False,
        "needs_billing": False,
        "needs_database": False,
        "needs_images": False,
        "suggested_files": ["manifest.json", "popup.html", "content.js", "background.js"],
    }),

    ("bot", [
        r"discord\s+bot", r"telegram\s+bot", r"slack\s+bot", r"chatbot",
        r"twitter\s+bot", r"twitch\s+bot",
    ], {
        "framework": "nodejs",
        "needs_backend": True,
        "needs_auth": False,
        "needs_billing": False,
        "needs_database": False,
        "needs_images": False,
        "suggested_files": ["bot.js", "commands/", "events/", "config.js"],
    }),

    ("game", [
        r"game", r"canvas\s+game", r"phaser", r"three\.?js", r"pixi",
        r"platformer", r"puzzle", r"arcade",
    ], {
        "framework": "vanilla",
        "needs_backend": False,
        "needs_auth": False,
        "needs_billing": False,
        "needs_database": False,
        "needs_images": True,
        "suggested_files": ["index.html", "game.js", "assets/"],
    }),

    ("cli", [
        r"cli\s+tool", r"command.?line", r"terminal\s+app", r"script",
        r"bash\s+script", r"python\s+script",
    ], {
        "framework": "nodejs",
        "needs_backend": False,
        "needs_auth": False,
        "needs_billing": False,
        "needs_database": False,
        "needs_images": False,
        "suggested_files": ["index.js", "cli.js", "package.json"],
    }),

    ("library", [
        r"npm\s+package", r"pip\s+package", r"library", r"sdk",
        r"reusable\s+component", r"npm\s+module",
    ], {
        "framework": "typescript",
        "needs_backend": False,
        "needs_auth": False,
        "needs_billing": False,
        "needs_database": False,
        "needs_images": False,
        "suggested_files": ["src/index.ts", "package.json", "tsconfig.json", "README.md"],
    }),

    ("desktop", [
        r"desktop\s+app", r"electron", r"tauri", r"native\s+app",
    ], {
        "framework": "electron",
        "needs_backend": False,
        "needs_auth": False,
        "needs_billing": False,
        "needs_database": False,
        "needs_images": False,
        "suggested_files": ["main.js", "preload.js", "renderer/", "package.json"],
    }),

    ("automation", [
        r"cron", r"scraper", r"web\s+scraping", r"pipeline", r"etl",
        r"data\s+processing", r"batch\s+job",
    ], {
        "framework": "python",
        "needs_backend": False,
        "needs_auth": False,
        "needs_billing": False,
        "needs_database": False,
        "needs_images": False,
        "suggested_files": ["main.py", "config.py", "requirements.txt"],
    }),

    # Website is the catch-all for anything with visual/page keywords
    ("website", [
        r"website", r"landing\s+page", r"homepage", r"portfolio", r"blog",
        r"store", r"shop", r"e.?commerce", r"restaurant", r"agency",
        r"business\s+site", r"personal\s+site", r"marketing\s+page",
        r"one.?page", r"multi.?page", r"html.*css", r"static\s+site",
    ], {
        "framework": "html-css-js",
        "needs_backend": False,
        "needs_auth": False,
        "needs_billing": False,
        "needs_database": False,
        "needs_images": True,
        "suggested_files": ["index.html", "styles.css", "app.js"],
    }),
]


def classify_project(prompt: str) -> Dict:
    """
    Analyze user prompt and return project classification + build config.

    Returns:
        {
            "type": "website" | "web-app" | "saas" | "api" | "mobile" | etc.,
            "confidence": 0.0-1.0,
            "framework": "react" | "nextjs" | "html-css-js" | etc.,
            "needs_backend": bool,
            "needs_auth": bool,
            "needs_billing": bool,
            "needs_database": bool,
            "needs_images": bool,   # auto-triggers image gen for assets
            "suggested_files": [...],
            "features_detected": [...],
        }
    """
    text = (prompt or "").lower().strip()
    if not text:
        return _default("unknown", 0.0)

    # Check each rule
    for project_type, patterns, config in CLASSIFICATION_RULES:
        matches = []
        for pattern in patterns:
            if re.search(pattern, text):
                matches.append(pattern)
        if matches:
            confidence = min(1.0, 0.5 + len(matches) * 0.15)
            result = _default(project_type, confidence)
            result.update(config)
            result["features_detected"] = matches
            # Detect additional features
            result.update(_detect_features(text, result))
            return result

    # No match — default to website if it mentions visual stuff, else unknown
    if any(w in text for w in ["page", "design", "layout", "ui", "ux", "button", "nav", "header", "footer"]):
        result = _default("website", 0.4)
        result["needs_images"] = True
        return result

    return _default("unknown", 0.0)


def _detect_features(text: str, base: Dict) -> Dict:
    """Detect additional features from the prompt."""
    extras = {}

    # Auth detection
    if re.search(r"login|signup|sign.?up|auth|user\s+accounts?|register", text):
        extras["needs_auth"] = True

    # Billing detection
    if re.search(r"stripe|payment|billing|subscription|pricing|checkout|pay", text):
        extras["needs_billing"] = True
        extras["needs_backend"] = True

    # Database detection
    if re.search(r"database|store\s+data|persist|sqlite|postgres|mongo|save.*data", text):
        extras["needs_database"] = True
        extras["needs_backend"] = True

    # Real-time detection
    if re.search(r"real.?time|websocket|live\s+update|chat|notification", text):
        extras["needs_realtime"] = True

    # Framework override detection
    if re.search(r"next\.?js|nextjs", text):
        extras["framework"] = "nextjs"
    elif re.search(r"react(?!\s+native)", text):
        extras["framework"] = "react"
    elif re.search(r"vue|vuejs", text):
        extras["framework"] = "vue"
    elif re.search(r"svelte", text):
        extras["framework"] = "svelte"
    elif re.search(r"express|node\.?js\s+server", text):
        extras["framework"] = "express"
    elif re.search(r"fastapi|flask|django", text):
        extras["framework"] = "python"

    return extras


def _default(project_type: str, confidence: float) -> Dict:
    return {
        "type": project_type,
        "confidence": confidence,
        "framework": "html-css-js",
        "needs_backend": False,
        "needs_auth": False,
        "needs_billing": False,
        "needs_database": False,
        "needs_images": False,
        "needs_realtime": False,
        "suggested_files": [],
        "features_detected": [],
    }
