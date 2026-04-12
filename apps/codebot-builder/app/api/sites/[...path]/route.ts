import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export const runtime = "nodejs";

const SITES_DIR = path.join(process.env.HOME || "/home/omatic657", "codebot-sites");

const MIME: Record<string, string> = {
  ".html": "text/html",
  ".htm": "text/html",
  ".css": "text/css",
  ".js": "text/javascript",
  ".json": "application/json",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
};

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path: pathSegments } = await params;
  const segments = pathSegments || [];
  if (segments.length === 0) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  let filePath = path.join(SITES_DIR, ...segments);

  if (!filePath.startsWith(SITES_DIR)) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  if (fs.existsSync(filePath) && fs.statSync(filePath).isDirectory()) {
    filePath = path.join(filePath, "index.html");
  }

  if (!fs.existsSync(filePath)) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  const ext = path.extname(filePath).toLowerCase();
  const contentType = MIME[ext] || "application/octet-stream";
  const content = fs.readFileSync(filePath);

  return new NextResponse(content, {
    status: 200,
    headers: { "Content-Type": contentType },
  });
}
