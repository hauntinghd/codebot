#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/omatic657/aicoderbot"
BUILDER="$ROOT/apps/codebot-builder"
ORCH="$ROOT/apps/codebot-orchestrator"

echo "=== Wire CodeBot Builder (safe, minimal) ==="

if [[ ! -d "$BUILDER" ]]; then
  echo "ERROR: builder not found at $BUILDER"
  exit 1
fi

mkdir -p "$BUILDER/app/api/orchestrator/[...path]"
mkdir -p "$BUILDER/app"

# 1) Next.js API proxy route -> orchestrator
cat > "$BUILDER/app/api/orchestrator/[...path]/route.ts" <<'ROUTE'
import { NextRequest } from "next/server";

const ORCH = process.env.ORCH_URL || "http://127.0.0.1:8091";

export async function POST(
  req: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const url = `${ORCH}/${params.path.join("/")}`;
  const body = await req.text();

  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });

  const text = await r.text();
  return new Response(text, {
    status: r.status,
    headers: { "Content-Type": r.headers.get("content-type") || "application/json" },
  });
}
ROUTE

# 2) builder .env.local
if [[ ! -f "$BUILDER/.env.local" ]]; then
  cat > "$BUILDER/.env.local" <<'ENV'
ORCH_URL=http://127.0.0.1:8091
ENV
else
  if ! grep -q '^ORCH_URL=' "$BUILDER/.env.local"; then
    echo 'ORCH_URL=http://127.0.0.1:8091' >> "$BUILDER/.env.local"
  fi
fi

# 3) Split-panel Builder UI page (Preview/Code/Logs + WebContainer run)
cat > "$BUILDER/app/page.tsx" <<'PAGE'
"use client";

import React, { useRef, useState } from "react";
import dynamic from "next/dynamic";
import { WebContainer } from "@webcontainer/api";

const Monaco = dynamic(() => import("@monaco-editor/react"), { ssr: false });

type PlanResponse = { plan: string };
type FilesResponse = { files: Record<string, string>; devCommand?: string };

type Tab = "preview" | "code" | "logs";

export default function Home() {
  const [prompt, setPrompt] = useState("Build a minimal Next.js app with auth and a dashboard");
  const [plan, setPlan] = useState("");
  const [code, setCode] = useState("");
  const [logs, setLogs] = useState<string[]>([]);
  const [tab, setTab] = useState<Tab>("preview");
  const [busy, setBusy] = useState(false);

  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const wcRef = useRef<WebContainer | null>(null);

  const log = (s: string) => setLogs((x) => [...x, s].slice(-600));

  async function postJSON<T>(url: string, body: any): Promise<T> {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) {
      const t = await r.text();
      throw new Error(`${r.status} ${r.statusText}: ${t}`);
    }
    return r.json();
  }

  async function ensureWebContainer() {
    if (wcRef.current) return wcRef.current;
    log("[webcontainer] booting...");
    const wc = await WebContainer.boot();
    wcRef.current = wc;

    wc.on("server-ready", (port, url) => {
      log(`[webcontainer] server-ready port=${port} url=${url}`);
      if (iframeRef.current) iframeRef.current.src = url;
    });

    return wc;
  }

  function toWebContainerFS(files: Record<string, string>) {
    const tree: any = {};
    for (const [path, contents] of Object.entries(files)) {
      const parts = path.split("/").filter(Boolean);
      let cur = tree;
      for (let i = 0; i < parts.length; i++) {
        const p = parts[i];
        const isLast = i === parts.length - 1;
        if (isLast) {
          cur[p] = { file: { contents } };
        } else {
          cur[p] = cur[p] || { directory: {} };
          cur = cur[p].directory;
        }
      }
    }
    return tree;
  }

  async function runBuild() {
    setBusy(true);
    setLogs([]);
    setPlan("");
    setCode("");

    try {
      log("[orchestrator] requesting plan...");
      const planRes = await postJSON<PlanResponse>("/api/orchestrator/api/build/plan", { prompt });
      setPlan(planRes.plan || "");
      log("[orchestrator] plan received");

      log("[orchestrator] requesting files...");
      const filesRes = await postJSON<FilesResponse>("/api/orchestrator/api/build/files", { prompt });

      if (!filesRes?.files || Object.keys(filesRes.files).length === 0) {
        throw new Error("No files returned from orchestrator.");
      }

      const merged = Object.entries(filesRes.files)
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([p, c]) => `// ===== ${p} =====\n${c}\n`)
        .join("\n");
      setCode(merged);

      const wc = await ensureWebContainer();
      log("[webcontainer] mounting files...");
      await wc.mount(toWebContainerFS(filesRes.files));

      log("[webcontainer] pnpm install...");
      const install = await wc.spawn("pnpm", ["install"]);
      install.output.pipeTo(new WritableStream({ write: (d) => log(String(d).trimEnd()) }));
      const installExit = await install.exit;
      if (installExit !== 0) throw new Error(`pnpm install failed with exit ${installExit}`);

      const devCmd = filesRes.devCommand || "pnpm dev -- --host 0.0.0.0 --port 3000";
      log(`[webcontainer] starting dev: ${devCmd}`);
      const [cmd, ...args] = devCmd.split(" ");
      const proc = await wc.spawn(cmd, args);
      proc.output.pipeTo(new WritableStream({ write: (d) => log(String(d).trimEnd()) }));

      setTab("preview");
    } catch (e: any) {
      log(`[error] ${e?.message || String(e)}`);
      setTab("logs");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="flex h-screen">
        <div className="w-[420px] border-r border-zinc-800 p-4 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div className="font-semibold">CodeBot Builder</div>
            <button
              onClick={runBuild}
              disabled={busy}
              className="px-3 py-2 rounded bg-cyan-600 hover:bg-cyan-500 disabled:opacity-60"
            >
              {busy ? "Building..." : "Build"}
            </button>
          </div>

          <div className="text-xs text-zinc-400">
            Describe what you want. CodeBot generates files, runs pnpm, and previews it in-browser.
          </div>

          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="flex-1 w-full resize-none rounded bg-zinc-900 border border-zinc-800 p-3 outline-none"
          />

          <div className="rounded border border-zinc-800 bg-zinc-900 p-3 text-xs">
            <div className="font-semibold mb-2">Plan</div>
            <pre className="whitespace-pre-wrap text-zinc-200">{plan || "No plan yet."}</pre>
          </div>
        </div>

        <div className="flex-1 flex flex-col">
          <div className="border-b border-zinc-800 p-3 flex items-center gap-2">
            <button
              onClick={() => setTab("preview")}
              className={`px-3 py-2 rounded ${tab === "preview" ? "bg-zinc-800" : "bg-zinc-900 border border-zinc-800"}`}
            >
              Preview
            </button>
            <button
              onClick={() => setTab("code")}
              className={`px-3 py-2 rounded ${tab === "code" ? "bg-zinc-800" : "bg-zinc-900 border border-zinc-800"}`}
            >
              Code
            </button>
            <button
              onClick={() => setTab("logs")}
              className={`px-3 py-2 rounded ${tab === "logs" ? "bg-zinc-800" : "bg-zinc-900 border border-zinc-800"}`}
            >
              Logs
            </button>
          </div>

          <div className="flex-1">
            {tab === "preview" && <iframe ref={iframeRef} className="w-full h-full bg-white" title="preview" />}
            {tab === "code" && (
              <div className="h-full">
                <Monaco
                  height="100%"
                  defaultLanguage="typescript"
                  value={code || "// No code yet"}
                  options={{ readOnly: true, minimap: { enabled: false }, fontSize: 13 }}
                />
              </div>
            )}
            {tab === "logs" && (
              <div className="h-full p-3 bg-black">
                <pre className="text-xs whitespace-pre-wrap">{logs.join("\n") || "No logs yet."}</pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
PAGE

# 4) Orchestrator: create a safe, additive files-endpoint module
# (You still must import it from your existing server.ts; this script will not edit server.ts.)
mkdir -p "$ORCH/src"
cat > "$ORCH/src/files_endpoint.ts" <<'ORCHFILE'
import { z } from "zod";

export const FilesResponseSchema = z.object({
  files: z.record(z.string(), z.string()).min(1),
  devCommand: z.string().optional(),
});

export type FilesResponse = z.infer<typeof FilesResponseSchema>;

/**
 * Implement in your server.ts:
 *   import { registerBuildFilesRoute } from "./files_endpoint";
 *   registerBuildFilesRoute(fastifyOrApp, buildFilesWithXai);
 *
 * buildFilesWithXai(prompt) must return:
 *   { files: { "package.json": "...", ... }, devCommand?: "pnpm dev -- --host 0.0.0.0 --port 3000" }
 */
export function registerBuildFilesRoute(app: any, buildFilesWithXai: (prompt: string) => Promise<any>) {
  app.post("/api/build/files", async (req: any, reply: any) => {
    const prompt = String(req.body?.prompt || "").trim();
    if (!prompt) return reply.code(400).send({ error: "Missing prompt" });

    const raw = await buildFilesWithXai(prompt);
    const parsed = FilesResponseSchema.safeParse(raw);

    if (!parsed.success) {
      return reply.code(500).send({
        error: "Invalid files payload from LLM",
        issues: parsed.error.issues,
      });
    }

    return reply.send(parsed.data);
  });
}
ORCHFILE

echo
echo "✓ Builder wired (UI + proxy)."
echo "✓ Orchestrator helper module created at apps/codebot-orchestrator/src/files_endpoint.ts"
echo
echo "NEXT (you run these, not this script):"
echo "  1) Add /api/build/files to orchestrator by importing registerBuildFilesRoute(...) in your server.ts"
echo "  2) Start orchestrator + builder:"
echo "     cd $ORCH && pnpm dev"
echo "     cd $BUILDER && pnpm dev -- --port 3000"
echo
echo "=== Done ==="
