import { NextResponse } from "next/server";
import { randomUUID } from "crypto";
import fs from "fs";
import path from "path";

export const runtime = "nodejs";

function j(data: any, status = 200) {
  return NextResponse.json(data, { status });
}

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const target = String(body?.target || "").toLowerCase();
  const projectId = String(body?.projectId || "default");

  if (!["vercel", "netlify", "server"].includes(target)) {
    return j({ error: "Invalid target" }, 400);
  }

  const id = randomUUID();
  const dbDir = path.join(process.cwd(), ".codebot");
  const dbPath = path.join(dbDir, "deployments.json");

  fs.mkdirSync(dbDir, { recursive: true });

  const existing = fs.existsSync(dbPath) ? JSON.parse(fs.readFileSync(dbPath, "utf8") || "[]") : [];
  existing.unshift({ id, target, projectId, createdAt: new Date().toISOString() });
  fs.writeFileSync(dbPath, JSON.stringify(existing, null, 2));

  // Unique URL every time for "My server"
  const url = `/deploy/${id}`;

  return j({ ok: true, id, url, target }, 200);
}
