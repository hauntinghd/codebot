#!/usr/bin/env bash
set -e

echo "=== CodeBot Builder Installation ==="

ROOT="$(pwd)"

# 1. Safety checks
if [ ! -d "$ROOT/backend" ]; then
  echo "ERROR: Must be run from CodeBot repo root (backend/ not found)."
  exit 1
fi

if [ -d "$ROOT/apps/codebot-builder" ]; then
  echo "Builder already installed at apps/codebot-builder. Aborting."
  exit 0
fi

echo "✓ Root verified"

# 2. Create builder directories (NO touching existing ones)
mkdir -p apps/codebot-builder
mkdir -p apps/codebot-orchestrator
mkdir -p apps/codebot-runner
mkdir -p packages/codebot-templates
mkdir -p packages/codebot-shared
mkdir -p data/builder-projects

echo "✓ Directories created"

# 3. Builder Web (Next.js + WebContainers)
cd apps/codebot-builder
pnpm create next-app . \
  --ts \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*" \
  --no-git

pnpm add @webcontainer/api monaco-editor @monaco-editor/react zustand

echo "✓ Builder UI scaffolded"

# 4. Orchestrator API (stub)
cd "$ROOT/apps/codebot-orchestrator"
pnpm init -y >/dev/null 2>&1 || true
pnpm add fastify @fastify/cors zod sqlite3 openai
pnpm add -D typescript tsx @types/node

cat > index.ts <<'EOT'
import Fastify from "fastify";
import cors from "@fastify/cors";

const app = Fastify();
app.register(cors, { origin: true, credentials: true });

app.get("/health", async () => ({ ok: true }));

app.listen({ port: 9100, host: "0.0.0.0" }, () => {
  console.log("[CodeBot Builder Orchestrator] running on :9100");
});
EOT

echo "✓ Orchestrator API created"

# 5. Runner (stub)
cd "$ROOT/apps/codebot-runner"
pnpm init -y >/dev/null 2>&1 || true
pnpm add execa fs-extra
pnpm add -D typescript tsx @types/node

cat > runner.ts <<'EOT'
console.log("CodeBot Runner ready");
EOT

echo "✓ Runner scaffolded"

# 6. Templates (Vite baseline stub)
cd "$ROOT/packages/codebot-templates"
mkdir -p vite-react-ts
cd vite-react-ts

pnpm init -y >/dev/null 2>&1 || true
pnpm add react react-dom
pnpm add -D vite typescript @types/react @types/react-dom

echo "✓ Base Vite template created"

# 7. DO NOT TOUCH AUTH / OAUTH / SETTINGS
echo "✓ Existing backend untouched"

echo "=== CodeBot Builder Installed Successfully ==="
echo "Next step: route /codebot/builder to apps/codebot-builder"
