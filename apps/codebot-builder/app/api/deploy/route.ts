import { NextResponse } from "next/server";
import { randomUUID } from "crypto";
import fs from "fs";
import path from "path";
import crypto from "crypto";

export const runtime = "nodejs";

function j(data: any, status = 200) {
  return NextResponse.json(data, { status });
}

async function deployToNetlify(
  files: Array<{ path: string; content: string }>,
  siteName: string,
  customDomain?: string
): Promise<{ url: string; siteId: string }> {
  const token = process.env.NETLIFY_AUTH_TOKEN || "";
  if (!token) throw new Error("NETLIFY_AUTH_TOKEN not configured");

  const fileHashes: Record<string, string> = {};
  const fileContents: Record<string, string> = {};

  for (const f of files) {
    const normalPath = "/" + f.path.replace(/^\/+/, "");
    const hash = crypto.createHash("sha1").update(f.content).digest("hex");
    fileHashes[normalPath] = hash;
    fileContents[hash] = f.content;
  }

  if (!fileHashes["/index.html"]) {
    const htmlFile = files.find(f => /\.html?$/i.test(f.path));
    if (htmlFile) {
      const hash = crypto.createHash("sha1").update(htmlFile.content).digest("hex");
      fileHashes["/index.html"] = hash;
      fileContents[hash] = htmlFile.content;
    }
  }

  const safeName = siteName
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, "-")
    .replace(/-+/g, "-")
    .replace(/(^-|-$)/g, "")
    .slice(0, 40) || "codebot-project";

  const sitePayload: any = { name: `${safeName}-${randomUUID().slice(0, 8)}` };
  if (customDomain) {
    sitePayload.custom_domain = customDomain.replace(/^https?:\/\//, "").replace(/\/+$/, "");
  }

  const createRes = await fetch("https://api.netlify.com/api/v1/sites", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(sitePayload),
  });

  if (!createRes.ok) {
    const err = await createRes.text().catch(() => "");
    throw new Error(`Netlify site creation failed (${createRes.status}): ${err}`);
  }

  const site = await createRes.json();
  const siteId = site.id;

  const deployRes = await fetch(
    `https://api.netlify.com/api/v1/sites/${siteId}/deploys`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ files: fileHashes }),
    }
  );

  if (!deployRes.ok) {
    const err = await deployRes.text().catch(() => "");
    throw new Error(`Netlify deploy creation failed (${deployRes.status}): ${err}`);
  }

  const deploy = await deployRes.json();
  const deployId = deploy.id;
  const required = deploy.required || [];

  for (const hash of required) {
    const content = fileContents[hash];
    if (!content) continue;

    const filePath = Object.keys(fileHashes).find(k => fileHashes[k] === hash) || "/unknown";
    const uploadRes = await fetch(
      `https://api.netlify.com/api/v1/deploys/${deployId}/files${filePath}`,
      {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/octet-stream",
        },
        body: content,
      }
    );

    if (!uploadRes.ok) {
      console.error(`Failed to upload file hash ${hash}: ${uploadRes.status}`);
    }
  }

  const finalUrl = customDomain
    ? `https://${customDomain.replace(/^https?:\/\//, "")}`
    : deploy.ssl_url || deploy.url || site.ssl_url || `https://${safeName}.netlify.app`;

  return { url: finalUrl, siteId };
}

function deployToVM(
  files: Array<{ path: string; content: string }>,
  projectName: string
): { url: string; deployPath: string } {
  const safeName = projectName
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, "-")
    .replace(/-+/g, "-")
    .replace(/(^-|-$)/g, "")
    .slice(0, 40) || "codebot-project";

  const slug = `${safeName}-${randomUUID().slice(0, 8)}`;
  const homeDir = process.env.HOME || "/home/omatic657";
  const deployDir = `${homeDir}/codebot-sites/${slug}`;

  fs.mkdirSync(deployDir, { recursive: true });

  for (const f of files) {
    const filePath = path.join(deployDir, f.path.replace(/^\/+/, ""));
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, f.content, "utf-8");
  }

  const serverHost = process.env.VM_DEPLOY_HOST || "chatbot.nyptidindustries.com";
  const url = `https://${serverHost}/codebot/api/sites/${slug}/`;

  return { url, deployPath: deployDir };
}

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const target = String(body?.target || "").toLowerCase();
  const projectId = String(body?.projectId || "default");
  const projectName = String(body?.projectName || "codebot-project");
  const files: Array<{ path: string; content: string }> = body?.files || [];
  const customDomain: string = String(body?.customDomain || "").trim();

  if (!["vercel", "netlify", "server"].includes(target)) {
    return j({ error: "Invalid target" }, 400);
  }

  if (!files.length) {
    return j({ error: "No files to deploy. Run a build first." }, 400);
  }

  const id = randomUUID();
  const dbDir = path.join(process.cwd(), ".codebot");
  const dbPath = path.join(dbDir, "deployments.json");
  fs.mkdirSync(dbDir, { recursive: true });

  if (target === "netlify") {
    try {
      const result = await deployToNetlify(files, projectName, customDomain || undefined);
      const existing = fs.existsSync(dbPath) ? JSON.parse(fs.readFileSync(dbPath, "utf8") || "[]") : [];
      existing.unshift({ id, target, projectId, siteId: result.siteId, url: result.url, customDomain: customDomain || null, createdAt: new Date().toISOString() });
      fs.writeFileSync(dbPath, JSON.stringify(existing, null, 2));
      return j({ ok: true, id, url: result.url, target, siteId: result.siteId }, 200);
    } catch (e: any) {
      return j({ error: `Netlify deploy failed: ${e?.message || e}` }, 500);
    }
  }

  if (target === "server") {
    try {
      const result = deployToVM(files, projectName);
      const existing = fs.existsSync(dbPath) ? JSON.parse(fs.readFileSync(dbPath, "utf8") || "[]") : [];
      existing.unshift({ id, target, projectId, url: result.url, deployPath: result.deployPath, customDomain: customDomain || null, createdAt: new Date().toISOString() });
      fs.writeFileSync(dbPath, JSON.stringify(existing, null, 2));
      return j({ ok: true, id, url: result.url, target, deployPath: result.deployPath }, 200);
    } catch (e: any) {
      return j({ error: `Server deploy failed: ${e?.message || e}` }, 500);
    }
  }

  return j({ error: "Vercel deployment not yet configured. Use Netlify or Server." }, 400);
}
