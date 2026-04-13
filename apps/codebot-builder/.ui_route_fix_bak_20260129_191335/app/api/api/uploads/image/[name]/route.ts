import { NextResponse } from "next/server";
import path from "path";
import { promises as fs } from "fs";

export async function GET(_: Request, ctx: { params: Promise<{ name: string }> }) {
  const { name } = await ctx.params;

  const abs = path.join(process.cwd(), ".uploads", name);
  const buf = await fs.readFile(abs);
  return new NextResponse(buf, { status: 200, headers: { "Content-Type": "application/octet-stream" } });
}

