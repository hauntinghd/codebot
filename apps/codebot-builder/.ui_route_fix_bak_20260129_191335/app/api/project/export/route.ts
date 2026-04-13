import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST() {
  // Phase 2 will zip the generated workspace and return it as a downloadable file.
  return NextResponse.json(
    { ok: true, message: "Export wired. Phase 2 will return a ZIP of generated project files." },
    { status: 200 }
  );
}
