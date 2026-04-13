import Fastify from "fastify";
import cors from "@fastify/cors";
import { z } from "zod";
import OpenAI from "openai";

const PORT = Number(process.env.PORT || 8091);
const HOST = process.env.HOST || "127.0.0.1";

const XAI_BASE_URL = (process.env.XAI_BASE_URL || "https://api.x.ai/v1").trim();
const XAI_API_KEY_RAW = process.env.XAI_API_KEY || "";
const XAI_API_KEY = XAI_API_KEY_RAW.trim();
const XAI_MODEL = (process.env.XAI_MODEL || "grok-4-1-fast-reasoning").trim();

function assertApiKeySafe(key: string) {
  // If this triggers, you will get the invalid header error you already saw.
  if (!key) throw new Error("Server misconfigured: missing XAI_API_KEY");
  if (/\s/.test(key)) {
    throw new Error("XAI_API_KEY contains whitespace/newlines. Re-export it cleanly (no line breaks).");
  }
}

assertApiKeySafe(XAI_API_KEY);

const client = new OpenAI({
  apiKey: XAI_API_KEY,
  baseURL: XAI_BASE_URL,
});

const app = Fastify({ logger: true });
await app.register(cors, { origin: true, credentials: true });

app.get("/health", async () => ({ ok: true }));

/**
 * === Utils ===
 * We force JSON, but models sometimes wrap it. This extracts the first {...} block.
 */
function extractFirstJsonObject(s: string): string {
  const start = s.indexOf("{");
  if (start === -1) return s;
  let depth = 0;
  for (let i = start; i < s.length; i++) {
    const ch = s[i];
    if (ch === "{") depth++;
    if (ch === "}") depth--;
    if (depth === 0) return s.slice(start, i + 1);
  }
  return s.slice(start);
}

function safeJsonParse<T>(raw: string): { ok: true; value: T } | { ok: false; error: string } {
  try {
    const trimmed = raw.trim();
    const candidate = extractFirstJsonObject(trimmed);
    return { ok: true, value: JSON.parse(candidate) as T };
  } catch (e: any) {
    return { ok: false, error: e?.message || String(e) };
  }
}

/**
 * === /api/build/plan ===
 */
const PlanReq = z.object({
  prompt: z.string().min(5),
  projectId: z.string().optional(),
});

app.post("/api/build/plan", async (req, reply) => {
  const parsed = PlanReq.safeParse(req.body);
  if (!parsed.success) {
    return reply.code(400).send({ detail: "Invalid request", issues: parsed.error.flatten() });
  }

  const resp = await client.chat.completions.create({
    model: XAI_MODEL,
    temperature: 0.2,
    messages: [
      {
        role: "system",
        content:
          "You are CodeBot Orchestrator. Output STRICT JSON only with keys: goals[], assumptions[], files[], steps[]. " +
          "files[] items: {path, purpose, dependsOn[]}. No markdown. No extra text.",
      },
      { role: "user", content: parsed.data.prompt },
    ],
  });

  return { plan: resp.choices?.[0]?.message?.content ?? "" };
});

/**
 * === /api/build/files ===
 * Returns runnable code as a files map.
 *
 * Output shape:
 * {
 *   "files": { "package.json": "...", "src/main.tsx": "...", ... },
 *   "devCommand": "pnpm dev -- --host 0.0.0.0 --port 3000"
 * }
 */
const FilesReq = z.object({
  prompt: z.string().min(5),
  projectId: z.string().optional(),
});

// Keep it strict. WebContainers needs a normal Node/Vite app for reliability.
const FilesResp = z.object({
  files: z.record(z.string(), z.string()).refine((m) => Object.keys(m).length > 0, "files is empty"),
  devCommand: z.string().optional(),
});

app.post("/api/build/files", async (req, reply) => {
  const parsed = FilesReq.safeParse(req.body);
  if (!parsed.success) {
    return reply.code(400).send({ detail: "Invalid request", issues: parsed.error.flatten() });
  }

  // This is the core “product” prompt. Don’t overcomplicate it yet.
  // Occam’s razor: Vite + React + TS, minimal deps, always runnable.
  const system = [
    "You are CodeBot Build Engine.",
    "Return STRICT JSON only. No markdown, no commentary, no code fences.",
    'Return shape: {"files":{ "<path>":"<contents>", ... }, "devCommand":"<string optional>" }',
    "The project MUST run in a WebContainer (browser node runtime).",
    "Prefer Vite + React + TypeScript. Avoid native deps (sqlite3, sharp, prisma, etc.).",
    "Do NOT require external secrets to run. If auth is requested, stub it locally (in-memory) with clear TODO comments.",
    "Include a minimal but complete package.json with scripts: dev/build/preview.",
    "Include index.html, vite config if needed, src/main.tsx, src/App.tsx.",
    "Ensure there are NO missing imports and that it compiles on first run.",
    "If user asks for Next.js: still output Vite unless explicitly asked otherwise (WebContainer reliability > SSR).",
  ].join(" ");

  const user = [
    "User prompt:",
    parsed.data.prompt,
    "",
    "Constraints:",
    "- Must be runnable immediately with: pnpm install && pnpm dev",
    "- Target dev port 3000 if you specify a devCommand.",
    "- Keep it minimal and correct.",
  ].join("\n");

  const resp = await client.chat.completions.create({
    model: XAI_MODEL,
    temperature: 0.15,
    messages: [
      { role: "system", content: system },
      { role: "user", content: user },
    ],
  });

  const raw = resp.choices?.[0]?.message?.content ?? "";
  const parsedJson = safeJsonParse<unknown>(raw);

  if (!parsedJson.ok) {
    return reply.code(500).send({
      detail: "LLM did not return valid JSON",
      error: parsedJson.error,
      raw: raw.slice(0, 2000),
    });
  }

  const validated = FilesResp.safeParse(parsedJson.value);
  if (!validated.success) {
    return reply.code(500).send({
      detail: "LLM JSON failed schema validation",
      issues: validated.error.flatten(),
      raw: raw.slice(0, 2000),
    });
  }

  // Default dev command if not provided
  const devCommand = validated.data.devCommand || "pnpm dev -- --host 0.0.0.0 --port 3000";

  return reply.send({ files: validated.data.files, devCommand });
});

await app.listen({ port: PORT, host: HOST });
app.log.info({ PORT, HOST, XAI_BASE_URL, XAI_MODEL }, "CodeBot orchestrator listening");
