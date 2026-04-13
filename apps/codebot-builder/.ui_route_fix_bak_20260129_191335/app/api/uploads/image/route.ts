import { NextResponse } from "next/server";
import path from "path";
import { promises as fs } from "fs";
import crypto from "crypto";

export async function POST(req: Request) {
  const form = await req.formData();
  const file = form.get("file");

  if (!(file instanceof File)) {
    return NextResponse.json({ detail: "Missing file" }, { status: 400 });
  }

  const ext = (file.name.split(".").pop() || "png").toLowerCase();
  const buf = Buffer.from(await file.arrayBuffer());
  const name = `${crypto.randomUUID()}.${ext}`;

  const dir = path.join(process.cwd(), ".uploads");
  await fs.mkdir(dir, { recursive: true });

  const abs = path.join(dir, name);
  await fs.writeFile(abs, buf);

  return NextResponse.json({ ok: true, filename: name, url: `/api/uploads/image/${name}` }, { status: 200 });
}

