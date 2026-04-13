import express from 'express';
import { getAvailableCbt, getLedger, grantMonthlyAllotment } from '../services/creditsService';
import { migrate } from '../db';
import fs from 'fs';
import path from 'path';

const router = express.Router();

// simple middleware assumes req.user.id exists. For demo, accept header X-User-Id
router.use((req: any, _res, next) => {
  if (!req.user) {
    const uid = req.header('X-User-Id');
    if (uid) req.user = { id: uid };
  }
  next();
});

function monthPeriodStartUtc(d = new Date()) {
  // First day of month, 00:00:00 UTC. This is stable + idempotent for monthly grants.
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1, 0, 0, 0, 0)).toISOString();
}

function nextMonthPeriodStartUtc(d = new Date()) {
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1, 0, 0, 0, 0)).toISOString();
}

// IMPORTANT: Keep this mapping explicit.
// Your $50 plan must grant 25,000 CBT (and CBT == tokens because CBT_PROVIDER_TOKEN_RATIO=1).
function monthlyCbtForPlan(planRaw: any): number {
  const plan = String(planRaw || '').trim().toLowerCase();

  // Treat these as the "$50 tier" for now
  if (plan === 'basic' || plan === 'plus' || plan === 'pioneer' || plan === '50') {
    return Number(process.env.BASIC_50_MONTHLY_CBT || 25000);
  }

  // Future tiers (optional envs, safe defaults)
  if (plan === 'pro' || plan === 'voyager' || plan === '250') {
    return Number(process.env.PRO_250_MONTHLY_CBT || 75000);
  }

  return 0;
}

router.get('/balance', async (req: any, res) => {
  const userId = req.user && req.user.id;
  if (!userId) return res.status(401).json({ error: 'unauthenticated' });

  const availableCbt = await getAvailableCbt(userId);

  // For demo, monthly vs purchased split not tracked separately in aggregation; compute approximation
  const ledger = await getLedger(userId, 1000);
  const monthly = ledger
    .filter((r: any) => r.source === 'MONTHLY_ALLOTMENT' && r.expires_at && new Date(r.expires_at) > new Date())
    .reduce((s: any, r: any) => s + Number(r.amount_cbt || 0), 0);

  const purchased = ledger
    .filter((r: any) => r.source === 'PURCHASE')
    .reduce((s: any, r: any) => s + Number(r.amount_cbt || 0), 0);

  res.json({ availableCbt, monthlyCbtRemaining: monthly, purchasedCbtRemaining: purchased });
});

router.get('/ledger', async (req: any, res) => {
  const userId = req.user && req.user.id;
  if (!userId) return res.status(401).json({ error: 'unauthenticated' });
  const limit = Number(req.query.limit || 50);
  const ledger = await getLedger(userId, limit);
  res.json({ ledger });
});

// migration endpoint (admin only) to run SQL migration file
router.post('/migrate', async (_req: any, res) => {
  const sqlPath = path.join(__dirname, '../db/migrations/001_init.sql');
  const sql = fs.readFileSync(sqlPath, 'utf8');
  try {
    await migrate(sql);
    res.json({ ok: true });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

/**
 * Ensure monthly allotment exists for the current month.
 * This is the route Python (or frontend) can call once on login/session start.
 *
 * Body: { plan?: string, periodStart?: string, periodEnd?: string }
 * - plan can be provided by caller; otherwise we default to env BASIC_50_MONTHLY_CBT if plan omitted.
 */
router.post('/ensure-monthly', async (req: any, res) => {
  const userId = req.user && req.user.id;
  if (!userId) return res.status(401).json({ error: 'unauthenticated' });

  // Caller may pass plan; if not, we assume "$50 plan" only for now.
  const plan = req.body?.plan ?? 'basic';
  const amount = monthlyCbtForPlan(plan);

  if (!amount || amount <= 0) {
    return res.json({ ok: true, granted: false, reason: 'no_monthly_allotment_for_plan', availableCbt: await getAvailableCbt(userId) });
  }

  const periodStart = req.body?.periodStart || monthPeriodStartUtc();
  const periodEnd = req.body?.periodEnd || nextMonthPeriodStartUtc();

  try {
    const out = await grantMonthlyAllotment(userId, periodStart, amount, periodEnd);
    const availableCbt = await getAvailableCbt(userId);
    return res.json({ ok: true, ...out, amount, periodStart, periodEnd, availableCbt });
  } catch (e: any) {
    return res.status(500).json({ error: e.message || 'error' });
  }
});

// grant monthly allotment (for testing/admin): body { periodStart, periodEnd }
router.post('/admin/grant-monthly', async (req: any, res) => {
  const userId = req.user && req.user.id;
  if (!userId) return res.status(401).json({ error: 'unauthenticated' });
  const periodStart = req.body.periodStart || monthPeriodStartUtc();
  const periodEnd = req.body.periodEnd || nextMonthPeriodStartUtc();
  const amount = Number(process.env.BASIC_50_MONTHLY_CBT || 25000);
  try {
    const out = await grantMonthlyAllotment(userId, periodStart, amount, periodEnd);
    res.json({ ok: true, ...out, amount, periodStart, periodEnd });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

export default router;
