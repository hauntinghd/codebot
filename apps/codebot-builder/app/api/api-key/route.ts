import { NextRequest, NextResponse } from "next/server";

const INTERNAL_BACKEND = process.env.CODEBOT_BACKEND_INTERNAL || "http://127.0.0.1:8000";
const API_PREFIX = "/codebot/api";

function backendUrl(req: NextRequest) {
  // Keep the same path, just forward to FastAPI internally.
  // This route is mounted at /codebot/api/api-key
  return `${INTERNAL_BACKEND}${API_PREFIX}/api-key`;
}

function passHeaders(req: NextRequest) {
  const h = new Headers();
  // Forward cookies so FastAPI session auth works
  const cookie = req.headers.get("cookie");
  if (cookie) h.set("cookie", cookie);

  const ct = req.headers.get("content-type");
  if (ct) h.set("content-type", ct);

  return h;
}

export async function GET(req: NextRequest) {
  const res = await fetch(backendUrl(req), {
    method: "GET",
    headers: passHeaders(req),
    cache: "no-store",
  });

  return new NextResponse(res.body, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") || "application/json" },
  });
}

export async function POST(req: NextRequest) {
  const body = await req.text();

  const res = await fetch(backendUrl(req), {
    method: "POST",
    headers: passHeaders(req),
    body,
    cache: "no-store",
  });

  return new NextResponse(res.body, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") || "application/json" },
  });
}

export async function DELETE(req: NextRequest) {
  const res = await fetch(backendUrl(req), {
    method: "DELETE",
    headers: passHeaders(req),
    cache: "no-store",
  });

  return new NextResponse(res.body, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") || "application/json" },
  });
}
