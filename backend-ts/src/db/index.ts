import { Pool } from 'pg';
import pino from 'pino';
const log = pino();

let pool: Pool | null = null;

export async function initDbPool(connectionString: string) {
  if (pool) return pool;
  pool = new Pool({ connectionString });
  // test
  await pool.query('SELECT 1');
  return pool;
}

export function getPool(): Pool {
  if (!pool) throw new Error('DB pool not initialized');
  return pool;
}

export async function migrate(sql: string) {
  const p = getPool();
  await p.query('BEGIN');
  try {
    await p.query(sql);
    await p.query('COMMIT');
  } catch (e) {
    await p.query('ROLLBACK');
    log.error(e);
    throw e;
  }
}
