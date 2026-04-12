import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export const runtime = "nodejs";

const STRIPE_SECRET = process.env.STRIPE_SECRET_KEY || "";
const BASE_URL = process.env.NEXT_PUBLIC_APP_URL || "https://chatbot.nyptidindustries.com";
const DB_DIR = path.join(process.cwd(), ".codebot");
const CONNECT_DB = path.join(DB_DIR, "stripe-connects.json");

function j(data: any, status = 200) {
  return NextResponse.json(data, { status });
}

function readConnections(): Record<string, any> {
  fs.mkdirSync(DB_DIR, { recursive: true });
  if (!fs.existsSync(CONNECT_DB)) return {};
  try { return JSON.parse(fs.readFileSync(CONNECT_DB, "utf8")); } catch { return {}; }
}

function saveConnections(data: Record<string, any>) {
  fs.mkdirSync(DB_DIR, { recursive: true });
  fs.writeFileSync(CONNECT_DB, JSON.stringify(data, null, 2));
}

export async function GET(req: Request) {
  const url = new URL(req.url);
  const action = url.searchParams.get("action");
  const userId = url.searchParams.get("userId") || "default";

  if (action === "status") {
    const connections = readConnections();
    const conn = connections[userId];
    if (conn?.stripe_user_id) {
      return j({ connected: true, stripeAccountId: conn.stripe_user_id, livemode: conn.livemode });
    }
    return j({ connected: false });
  }

  if (action === "connect") {
    const clientId = process.env.STRIPE_CONNECT_CLIENT_ID || "";
    if (!clientId) {
      return j({ error: "Stripe Connect client ID not configured. Set STRIPE_CONNECT_CLIENT_ID." }, 500);
    }
    const redirectUri = `${BASE_URL}/codebot/api/stripe-connect?action=callback`;
    const authorizeUrl = `https://connect.stripe.com/oauth/authorize?response_type=code&client_id=${clientId}&scope=read_write&redirect_uri=${encodeURIComponent(redirectUri)}&state=${encodeURIComponent(userId)}`;
    return NextResponse.redirect(authorizeUrl);
  }

  if (action === "callback") {
    const code = url.searchParams.get("code");
    const state = url.searchParams.get("state") || userId;

    if (!code) {
      const error = url.searchParams.get("error_description") || "Authorization cancelled";
      return NextResponse.redirect(`${BASE_URL}/codebot/settings?stripe_error=${encodeURIComponent(error)}`);
    }

    try {
      const tokenRes = await fetch("https://connect.stripe.com/oauth/token", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          grant_type: "authorization_code",
          code,
          client_secret: STRIPE_SECRET,
        }),
      });

      if (!tokenRes.ok) {
        const err = await tokenRes.text();
        return NextResponse.redirect(`${BASE_URL}/codebot/settings?stripe_error=${encodeURIComponent(err)}`);
      }

      const tokenData = await tokenRes.json();
      const connections = readConnections();
      connections[state] = {
        stripe_user_id: tokenData.stripe_user_id,
        access_token: tokenData.access_token,
        livemode: tokenData.livemode,
        connected_at: new Date().toISOString(),
      };
      saveConnections(connections);

      return NextResponse.redirect(`${BASE_URL}/codebot/settings?stripe_connected=true`);
    } catch (e: any) {
      return NextResponse.redirect(`${BASE_URL}/codebot/settings?stripe_error=${encodeURIComponent(e?.message || "Unknown error")}`);
    }
  }

  if (action === "disconnect") {
    const connections = readConnections();
    delete connections[userId];
    saveConnections(connections);
    return j({ ok: true, connected: false });
  }

  if (action === "products") {
    const connections = readConnections();
    const conn = connections[userId];
    if (!conn?.stripe_user_id) {
      return j({ error: "No Stripe account connected" }, 400);
    }

    try {
      const key = conn.access_token || STRIPE_SECRET;
      const productsRes = await fetch(
        `https://api.stripe.com/v1/products?active=true&limit=20`,
        {
          headers: {
            Authorization: `Bearer ${key}`,
            "Stripe-Account": conn.stripe_user_id,
          },
        }
      );

      if (!productsRes.ok) {
        return j({ error: `Failed to fetch products: ${productsRes.status}` }, 500);
      }

      const productsData = await productsRes.json();
      const products = (productsData.data || []).map((p: any) => ({
        id: p.id,
        name: p.name,
        description: p.description,
        images: p.images,
        default_price: p.default_price,
      }));

      return j({ products });
    } catch (e: any) {
      return j({ error: e?.message || "Failed to fetch products" }, 500);
    }
  }

  return j({ error: "Invalid action" }, 400);
}
