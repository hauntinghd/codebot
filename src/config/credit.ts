// src/config/credit.ts

export const CBT_PER_USD = 500; // 1 CBT = $0.002 (Grok 4.1 Fast)
export const GROK_4_1_FAST_PRICE_PER_1K = 0.002; // $2 per 1M tokens
export const BASIC_50_MONTHLY_CBT = 25000; // $50 / $0.002 = 25,000 CBT
export const PACKS = {
  PACK_20: { priceId: 'price_1SpwQmBL8lRmwao2YObktgqp', amountUsd: 20, cbtGranted: 10000 }, // $20 / $0.002 = 10,000 CBT
  PACK_60: { priceId: 'price_1SpwRBBL8lRmwao2Xf027BLD', amountUsd: 60, cbtGranted: 30000 }, // $60 / $0.002 = 30,000 CBT
  // PACK_200: { priceId: '...', amountUsd: 200, cbtGranted: 100000, comingSoon: true },
};
export const PRO_250_COMING_SOON = true;
