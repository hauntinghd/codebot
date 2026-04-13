import { NextResponse } from "next/server";
import { addTokens } from "../../../lib/cbt";

export const runtime = "nodejs";

export async function POST(req: Request) {
  const adminKey = (process.env.CODEBOT_ADMIN_KEY || "").trim();
  const provided = (req.headers.get("x-admin-key") || "").trim();

  if (!adminKey || provided !== adminKey) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const body = await req.json().catch(() => ({}));
  const userId = String(body?.userId || "").trim();
  const amount = Number(body?.amount);

  if (!userId) return NextResponse.json({ error: "missing_userId" }, { status: 400 });
  if (!Number.isFinite(amount) || Math.floor(amount) !== amount) {
    return NextResponse.json({ error: "amount_must_be_int" }, { status: 400 });
  }

  addTokens(userId, Math.floor(amount), "manual.topup", { by: "admin" });
  return NextResponse.json({ ok: true }, { status: 200 });
}
