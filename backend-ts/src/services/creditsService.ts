import { getPool } from '../db';
import { v4 as uuidv4 } from 'uuid';
import pino from 'pino';
const log = pino();

const FEATURE_COSTS: Record<string, number> = {
  NORMAL_GENERATION: Number(process.env.FEATURE_COST_NORMAL || 1),
  ARCHITECTURE_MODE: Number(process.env.FEATURE_COST_ARCH || 5),
  BUILD_PROJECT: Number(process.env.FEATURE_COST_BUILD || 8),
};

const PROVIDER_THRESHOLD = Number(process.env.PROVIDER_BALANCE_THRESHOLD_USD || 7);

// Simple in-memory provider balance for MVP (mockable)
let providerBalanceUsd = Number(process.env.XAI_BALANCE_USD || 100);

export function getProviderBalanceUsd() {
  return providerBalanceUsd;
}

export function deductProviderBalanceUsd(amount: number) {
  providerBalanceUsd = Math.max(0, providerBalanceUsd - amount);
}

export async function getAvailableCbt(userId: string) {
  const pool = getPool();
  const res = await pool.query(
    `SELECT COALESCE(SUM(amount_cbt),0) as total FROM credit_ledger WHERE user_id = $1 AND (expires_at IS NULL OR expires_at > now())`,
    [userId]
  );
  return Number(res.rows[0].total || 0);
}

export async function getProviderBalance() {
  return getProviderBalanceUsd();
}

export async function chargeCredits(
  userId: string,
  feature: 'NORMAL_GENERATION' | 'ARCHITECTURE_MODE' | 'BUILD_PROJECT',
  requestId: string,
  providerTokensIn: number,
  providerTokensOut: number,
  providerCostUsdEstimate: number
) {
  const pool = getPool();

  // Compute CBT cost exactly from provider tokens according to env ratio
  const ratio = Number(process.env.CBT_PROVIDER_TOKEN_RATIO || 1000);
  const totalTokens = Number(providerTokensIn || 0) + Number(providerTokensOut || 0);
  const cbtCost = Math.max(1, Math.ceil(totalTokens / ratio));

  // Provider balance check
  if (getProviderBalanceUsd() < PROVIDER_THRESHOLD) {
    // Allow planning (NORMAL_GENERATION) but block code execution features
    if (feature !== 'NORMAL_GENERATION') {
      const err: any = new Error('Provider balance low: code execution disabled');
      err.status = 503;
      throw err;
    }
  }

  // Transaction + advisory lock to prevent concurrent overspend
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    // acquire advisory lock per user (hash text)
    await client.query("SELECT pg_advisory_xact_lock(hashtext($1))", [userId]);

    const balRes = await client.query(
      `SELECT COALESCE(SUM(amount_cbt),0) as total FROM credit_ledger WHERE user_id = $1 AND (expires_at IS NULL OR expires_at > now())`,
      [userId]
    );
    const available = Number(balRes.rows[0].total || 0);
    if (available < cbtCost) {
      await client.query('ROLLBACK');
      const err: any = new Error('Insufficient CBT balance');
      err.status = 402;
      throw err;
    }

    // Insert usage ledger
    await client.query(
      `INSERT INTO credit_ledger (id, user_id, source, amount_cbt, expires_at, metadata) VALUES ($1,$2,$3,$4,$5,$6)`,
      [uuidv4(), userId, 'USAGE', -cbtCost, null, JSON.stringify({ feature, requestId, providerTokensIn, providerTokensOut, providerCostEstimateUsd: providerCostUsdEstimate })]
    );

    // Deduct provider balance estimate
    deductProviderBalanceUsd(providerCostUsdEstimate);

    await client.query('COMMIT');
    return { charged: cbtCost, remaining: available - cbtCost };
  } catch (e) {
    try { await client.query('ROLLBACK'); } catch (_) {}
    throw e;
  } finally {
    client.release();
  }
}

export async function grantMonthlyAllotment(userId: string, periodStart: string, amount:number, periodEndIso?: string) {
  const pool = getPool();
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    // ensure idempotent: attempt insert into monthly_grants
    const up = await client.query(
      `INSERT INTO monthly_grants (user_id, period_start, source) VALUES ($1,$2,$3) ON CONFLICT (user_id, period_start, source) DO NOTHING RETURNING user_id`,
      [userId, periodStart, 'MONTHLY_ALLOTMENT']
    );
    if (up.rowCount === 0) {
      await client.query('ROLLBACK');
      return { granted: false };
    }

    const expiresAt = periodEndIso || null;
    await client.query(
      `INSERT INTO credit_ledger (id, user_id, source, amount_cbt, expires_at, metadata) VALUES ($1,$2,$3,$4,$5,$6)`,
      [uuidv4(), userId, 'MONTHLY_ALLOTMENT', amount, expiresAt, JSON.stringify({ periodStart })]
    );
    await client.query('COMMIT');
    return { granted: true };
  } catch (e) {
    try { await client.query('ROLLBACK'); } catch (_) {}
    throw e;
  } finally { client.release(); }
}

export async function grantPurchase(userId: string, purchaseId: string, cbtAmount: number, metadata: any) {
  const pool = getPool();
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    // idempotent: check if we've already inserted linked to purchaseId
    const chk = await client.query(`SELECT 1 FROM credit_ledger WHERE metadata->>'purchase_id' = $1 LIMIT 1`, [purchaseId]);
    if ((chk.rowCount || 0) > 0) { await client.query('ROLLBACK'); return { granted: false } }

    await client.query(
      `INSERT INTO credit_ledger (id, user_id, source, amount_cbt, expires_at, metadata) VALUES ($1,$2,$3,$4,$5,$6)`,
      [uuidv4(), userId, 'PURCHASE', cbtAmount, null, JSON.stringify({ ...metadata, purchase_id: purchaseId })]
    );
    await client.query('COMMIT');
    return { granted: true };
  } catch (e) {
    try { await client.query('ROLLBACK'); } catch (_) {}
    throw e;
  } finally { client.release(); }
}

export async function getLedger(userId: string, limit = 50) {
  const pool = getPool();
  const res = await pool.query(`SELECT * FROM credit_ledger WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2`, [userId, limit]);
  return res.rows;
}
