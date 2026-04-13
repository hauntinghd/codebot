import express from "express";
import Stripe from "stripe";
import dotenv from "dotenv";
import { getPool } from "../db";
import { grantPurchase } from "../services/creditsService";
import { v4 as uuidv4 } from "uuid";

dotenv.config();

const router = express.Router();

/**
 * Demo auth middleware:
 * Accepts X-User-Id header and populates req.user.
 */
router.use((req, _res, next) => {
  if (!req.user) {
    const uid = req.header("X-User-Id") || req.header("x-user-id");
    if (uid) req.user = { id: uid } as any;
  }
  next();
});

function requireUserId(req: any, res: express.Response): string | null {
  const userId = req.user && req.user.id;
  if (!userId) {
    res.status(401).json({ error: "unauthenticated" });
    return null;
  }
  return String(userId);
}

/**
 * Stripe initialization:
 * - stripe@11 requires constructor(apiKey, config) where config includes apiVersion.
 * - DO NOT use 2024-11-15 (you already proved that breaks at runtime).
 * - 2023-10-16 is a stable, widely-supported Stripe API version.
 *
 * NOTE: Keep this isolated to the credits service. If you later upgrade Stripe,
 * update this apiVersion to match Stripe's supported "LatestApiVersion".
 */
let stripeClient: Stripe | null = null;

function getStripeOrNull(): Stripe | null {
  if (stripeClient) return stripeClient;

  const key = (process.env.STRIPE_SECRET_KEY || "").trim();
  if (!key) return null;

  stripeClient = new Stripe(
    key,
    {
      apiVersion: "2023-10-16",
      // leave other settings default; don't fight typings with extras
    } as any
  ) as any;

  return stripeClient;
}

const CREDIT_TIERS: Record<number, { priceId: string; priceUsd: number; cbt: number; label: string }> = {
  500:  { priceId: "price_1T2jazBL8lRmwao27DRVcEzX", priceUsd: 7.50,  cbt: 500,  label: "500 CodeBot Credits" },
  2000: { priceId: "price_1T2jbMBL8lRmwao2fRFTEwOj", priceUsd: 28,    cbt: 2000, label: "2,000 CodeBot Credits" },
  5000: { priceId: "price_1T2jbeBL8lRmwao2E1hoyfP7", priceUsd: 60,    cbt: 5000, label: "5,000 CodeBot Credits" },
};

const PACKS: Record<string, { priceUsd: number; cbt: number }> = {
  PACK_20: { priceUsd: 20, cbt: 60 },
  PACK_60: { priceUsd: 60, cbt: 220 },
};

async function ensureStripeCustomersTable() {
  const pool = getPool();
  await pool.query(`
    CREATE TABLE IF NOT EXISTS stripe_customers (
      user_id TEXT PRIMARY KEY,
      stripe_customer_id TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
  `);
}

/**
 * purchases table assumptions (based on your comments/flow):
 * - purchases.id is UUID PRIMARY KEY
 * - purchases.stripe_checkout_session_id is used for idempotency
 * If stripe_checkout_session_id is NOT unique in DB, we still do app-level idempotency.
 */
async function ensurePurchasesIndexIfNeeded() {
  // Optional: only do this if you want hard guarantees at DB level.
  // Leaving this as a no-op by default to avoid surprising schema changes.
  return;
}

async function getOrCreateStripeCustomerId(userId: string, stripe: Stripe): Promise<string> {
  const pool = getPool();

  await ensureStripeCustomersTable();

  const existing = await pool.query(
    `SELECT stripe_customer_id FROM stripe_customers WHERE user_id = $1 LIMIT 1`,
    [userId]
  );

  if (existing.rowCount && existing.rows[0]?.stripe_customer_id) {
    return String(existing.rows[0].stripe_customer_id);
  }

  const customer = await stripe.customers.create({
    metadata: { user_id: userId, app: "codebot" },
  });

  const cid = String(customer.id);

  await pool.query(
    `INSERT INTO stripe_customers (user_id, stripe_customer_id)
     VALUES ($1,$2)
     ON CONFLICT (user_id)
     DO UPDATE SET stripe_customer_id = EXCLUDED.stripe_customer_id, updated_at = now()`,
    [userId, cid]
  );

  return cid;
}

/**
 * Billing Portal
 * GET/POST /api/billing/portal
 * Returns { url }
 */
async function handlePortal(req: any, res: express.Response) {
  const userId = requireUserId(req, res);
  if (!userId) return;

  const stripe = getStripeOrNull();
  if (!stripe) return res.status(500).json({ error: "stripe_not_configured" });

  const baseUrl = (process.env.APP_BASE_URL || "").trim();
  const basePath = (process.env.APP_BASE_PATH || "").trim(); // optional
  if (!baseUrl) return res.status(500).json({ error: "app_base_url_not_configured" });

  const returnUrl = `${baseUrl}${basePath}/account`;

  try {
    const customerId = await getOrCreateStripeCustomerId(userId, stripe);
    const session = await stripe.billingPortal.sessions.create({
      customer: customerId,
      return_url: returnUrl,
    });
    return res.json({ url: session.url });
  } catch (e: any) {
    console.error("[billing/portal] Stripe error:", e?.type, e?.message, e?.raw?.message);
    const msg = e?.raw?.message || e?.message || "portal_error";
    return res.status(500).json({ error: msg });
  }
}

router.get("/portal", handlePortal);
router.post("/portal", express.json(), handlePortal);

/**
 * Create a Checkout Session for CBT packs
 * POST /api/billing/credits/checkout
 * Body: { packSku: "PACK_20" }
 *
 * IMPORTANT:
 * - purchases.id is UUID in your DB, so we generate uuidv4()
 * - stripe session id goes into purchases.stripe_checkout_session_id
 */
router.post("/credits/checkout", express.json(), async (req: any, res) => {
  const userId = requireUserId(req, res);
  if (!userId) return;

  const stripe = getStripeOrNull();
  if (!stripe) return res.status(500).json({ error: "stripe_not_configured" });

  const credits = Number(req.body?.credits);
  const tier = CREDIT_TIERS[credits];

  const packSku = String(req.body?.packSku || "");
  const legacyPack = PACKS[packSku];

  const resolvedPack = tier
    ? { priceUsd: tier.priceUsd, cbt: tier.cbt, sku: `CREDITS_${credits}`, label: tier.label }
    : legacyPack
    ? { priceUsd: legacyPack.priceUsd, cbt: legacyPack.cbt, sku: packSku, label: packSku }
    : null;

  if (!resolvedPack) return res.status(400).json({ error: "invalid_credit_tier" });

  const baseUrl = (process.env.APP_BASE_URL || "").trim();
  const basePath = (process.env.APP_BASE_PATH || "").trim();
  if (!baseUrl) return res.status(500).json({ error: "app_base_url_not_configured" });

  try {
    await ensurePurchasesIndexIfNeeded();

    const customerId = await getOrCreateStripeCustomerId(userId, stripe);

    const lineItem = tier?.priceId
      ? { price: tier.priceId, quantity: 1 }
      : {
          price_data: {
            currency: "usd",
            product_data: {
              name: resolvedPack.label,
              description: `${resolvedPack.cbt.toLocaleString()} credits for CodeBot™. Added instantly. Never expires.`,
            },
            unit_amount: Math.round(resolvedPack.priceUsd * 100),
          },
          quantity: 1,
        };

    const sessionParams: any = {
      customer: customerId,
      payment_method_types: ["card"],
      mode: "payment",
      line_items: [lineItem],
      success_url: `${baseUrl}${basePath}/account?checkout=success`,
      cancel_url: `${baseUrl}${basePath}/account/upgrade`,
      metadata: { user_id: userId, pack_sku: resolvedPack.sku, cbt: String(resolvedPack.cbt) },
      custom_text: {
        submit: { message: `You're purchasing ${resolvedPack.cbt.toLocaleString()} CodeBot™ credits. Credits are added instantly and never expire.` },
      },
      allow_promotion_codes: true,
    };

    const session = await stripe.checkout.sessions.create(sessionParams);

    const pool = getPool();

    const existing = await pool.query(
      `SELECT id FROM purchases WHERE stripe_checkout_session_id = $1 LIMIT 1`,
      [session.id]
    );

    if (existing.rowCount === 0) {
      const purchaseId = uuidv4();
      const amountUsdInt = Math.round(resolvedPack.priceUsd);
      await pool.query(
        `INSERT INTO purchases (id, user_id, pack_sku, amount_usd, cbt_granted, stripe_checkout_session_id, status) VALUES ($1,$2,$3,$4,$5,$6,$7)`,
        [purchaseId, userId, resolvedPack.sku, amountUsdInt, resolvedPack.cbt, session.id, "PENDING"]
      );
    }

    return res.json({ url: session.url });
  } catch (e: any) {
    console.error("[billing/credits/checkout] Stripe error:", e?.type, e?.message, e?.raw?.message);
    return res.status(500).json({ error: e?.message || "checkout_error" });
  }
});

/**
 * Stripe Webhook
 * POST /api/billing/stripe/webhook
 *
 * CRITICAL: raw body must be used for signature verification.
 * If your server has app.use(express.json()) globally, it can break this route.
 * We defensively support both Buffer and non-Buffer bodies.
 */
router.post("/stripe/webhook", express.raw({ type: "application/json" }), async (req: any, res) => {
  const stripe = getStripeOrNull();
  if (!stripe) return res.status(500).send("stripe_not_configured");

  const sig = req.headers["stripe-signature"] as string | undefined;
  const webhookSecret = (process.env.STRIPE_WEBHOOK_SECRET || "").trim();
  if (!webhookSecret) return res.status(400).send("webhook secret not configured");

  let event: Stripe.Event;

  try {
    const rawBody: Buffer = Buffer.isBuffer(req.body)
      ? (req.body as Buffer)
      : Buffer.from(typeof req.body === "string" ? req.body : JSON.stringify(req.body));

    event = stripe.webhooks.constructEvent(rawBody, sig || "", webhookSecret);
  } catch (err: any) {
    return res.status(400).send(`Webhook Error: ${err.message}`);
  }

  const pool = getPool();

  try {
    if (event.type === "checkout.session.completed") {
      const sess = event.data.object as Stripe.Checkout.Session;
      const sessionId = String(sess.id);

      // Find purchase by session id (idempotency anchor)
      const r = await pool.query(
        `SELECT * FROM purchases WHERE stripe_checkout_session_id = $1 LIMIT 1`,
        [sessionId]
      );

      if (r.rowCount === 0) {
        const uid = (sess.metadata && (sess.metadata as any).user_id) || null;
        const packSku = (sess.metadata && (sess.metadata as any).pack_sku) || null;
        const metaCbt = Number((sess.metadata as any)?.cbt || 0);
        if (!uid || !packSku) return res.status(200).send("no purchase metadata");

        const legacyPack = PACKS[String(packSku)];
        const creditNum = parseInt(String(packSku).replace("CREDITS_", ""), 10);
        const tier = CREDIT_TIERS[creditNum];

        const resolvedCbt = tier ? tier.cbt : legacyPack ? legacyPack.cbt : metaCbt;
        const resolvedPrice = tier ? tier.priceUsd : legacyPack ? legacyPack.priceUsd : 0;
        if (!resolvedCbt) return res.status(200).send("unknown pack");

        const purchaseId = uuidv4();
        const amountUsdInt = Math.round(Number(resolvedPrice));
        await pool.query(
          `INSERT INTO purchases (id,user_id,pack_sku,amount_usd,cbt_granted,stripe_checkout_session_id,status) VALUES ($1,$2,$3,$4,$5,$6,$7)`,
          [purchaseId, uid, packSku, amountUsdInt, resolvedCbt, sessionId, "PENDING"]
        );
      }

      const purchaseRow = (
        await pool.query(
          `SELECT * FROM purchases WHERE stripe_checkout_session_id = $1 LIMIT 1`,
          [sessionId]
        )
      ).rows[0];

      if (!purchaseRow) return res.status(200).send("purchase_missing");

      if (purchaseRow.status === "PAID") return res.status(200).send("already processed");

      await pool.query(
        `UPDATE purchases SET status = 'PAID' WHERE stripe_checkout_session_id = $1`,
        [sessionId]
      );

      // purchaseRow.id is UUID => creditsService idempotency works
      await grantPurchase(purchaseRow.user_id, purchaseRow.id, purchaseRow.cbt_granted, {
        stripe_session_id: sessionId,
        pack_sku: purchaseRow.pack_sku,
      });

      return res.status(200).send("ok");
    }

    return res.status(200).send("ignored");
  } catch (e: any) {
    console.error("webhook error", e);
    return res.status(500).send("server error");
  }
});

export default router;
