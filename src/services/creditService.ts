import { db } from '../db/connection';
import { creditLedger, subscriptions, purchases } from '../db/schema';
import { eq, and } from 'drizzle-orm';
import { v4 as uuidv4 } from 'uuid';
import { BASIC_50_MONTHLY_CBT, PACKS } from '../config/credit';

export async function getCreditBalance(userId: string) {
  const now = new Date();
  const rows = await db.select().from(creditLedger).where(eq(creditLedger.userId, userId));
  let availableCbt = 0, monthlyCbt = 0, purchasedCbt = 0;
  for (const row of rows) {
    if (row.amountCbt > 0 && row.source === 'MONTHLY_ALLOTMENT' && (!row.expiresAt || row.expiresAt > now)) {
      monthlyCbt += row.amountCbt;
      availableCbt += row.amountCbt;
    } else if (row.amountCbt > 0 && row.source === 'PURCHASE') {
      purchasedCbt += row.amountCbt;
      availableCbt += row.amountCbt;
    } else if (row.amountCbt < 0 && (!row.expiresAt || row.expiresAt > now)) {
      availableCbt += row.amountCbt;
    }
  }
  return { availableCbt, monthlyCbtRemaining: monthlyCbt, purchasedCbtRemaining: purchasedCbt };
}

export async function grantMonthlyAllotment(userId: string, periodStart: Date, periodEnd: Date) {
  const existing = await db.select().from(creditLedger)
    .where(and(
      eq(creditLedger.userId, userId),
      eq(creditLedger.source, 'MONTHLY_ALLOTMENT'),
      eq(creditLedger.metadata, { periodStart: periodStart.toISOString() })
    ));
  if (existing.length > 0) return;
  await db.insert(creditLedger).values({
    id: uuidv4(),
    userId,
    source: 'MONTHLY_ALLOTMENT',
    amountCbt: BASIC_50_MONTHLY_CBT,
    expiresAt: periodEnd,
    metadata: { periodStart: periodStart.toISOString() },
    createdAt: new Date(),
  });
}

export async function getPackInfo(packSku: string) {
  if (!(packSku in PACKS)) throw new Error('Invalid packSku');
  return PACKS[packSku as keyof typeof PACKS];
}
