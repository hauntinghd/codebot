import { getPool } from '../db';
import { grantMonthlyAllotment } from '../services/creditsService';
import dotenv from 'dotenv';
dotenv.config();

/**
 * This script finds active subscriptions and grants monthly allotments idempotently.
 * Intended to be run daily via cron; for MVP it's synchronous and simple.
 */
export async function runMonthlyGrant() {
  const pool = getPool();
  const res = await pool.query(`SELECT user_id, plan, current_period_start, current_period_end FROM subscriptions WHERE status = 'ACTIVE' AND plan = 'BASIC_50'`);
  const amount = Number(process.env.BASIC_50_MONTHLY_CBT || 75);
  for (const row of res.rows) {
    const userId = row.user_id;
    const periodStart = new Date(row.current_period_start).toISOString();
    const periodEnd = new Date(row.current_period_end).toISOString();
    try {
      await grantMonthlyAllotment(userId, periodStart, amount, periodEnd);
    } catch (e:any) {
      console.error('grant failed for', userId, e.message);
    }
  }
}

if (require.main === module) {
  runMonthlyGrant().then(()=>process.exit(0)).catch((e)=>{console.error(e);process.exit(1)});
}
