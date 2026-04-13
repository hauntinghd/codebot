import express from 'express';
import { getPackInfo } from '../services/creditService';
import Stripe from 'stripe';
import { purchases, creditLedger } from '../db/schema';
import { db } from '../db/connection';
import { v4 as uuidv4 } from 'uuid';
import { PRO_250_COMING_SOON } from '../config/credit';

const router = express.Router();
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, { apiVersion: '2023-10-16' });

router.post('/credits/checkout', async (req, res) => {
  const { packSku } = req.body;
  if (packSku === 'PACK_200' || PRO_250_COMING_SOON) return res.status(400).json({ error: 'Pack not available' });
  const pack = await getPackInfo(packSku);
  const session = await stripe.checkout.sessions.create({
    payment_method_types: ['card'],
    mode: 'payment',
    line_items: [{ price: pack.priceId, quantity: 1 }],
    success_url: process.env.APP_BASE_URL + '/billing/success',
    cancel_url: process.env.APP_BASE_URL + '/billing/cancel',
    metadata: { user_id: req.user.id, packSku },
  });
  await db.insert(purchases).values({
    id: uuidv4(),
    userId: req.user.id,
    stripeCheckoutSessionId: session.id,
    packSku,
    amountUsd: pack.amountUsd,
    cbtGranted: pack.cbtGranted,
    status: 'PENDING',
    createdAt: new Date(),
  });
  res.json({ url: session.url });
});

export default router;
