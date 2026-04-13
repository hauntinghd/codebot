import express from 'express';
import dotenv from 'dotenv';
import pino from 'pino';
import creditsRouter from './routes/credits';
import billingRouter from './routes/billing';
import aiRouter from './routes/ai';
import { initDbPool } from './db';

dotenv.config();
const log = pino();

const app = express();
app.use((req, res, next) => {
  if (req.path.includes('/stripe/webhook')) return next();
  express.json()(req, res, next);
});

initDbPool(process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/codebot')
  .then(() => log.info('DB pool initialized'))
  .catch((e) => { log.error(e); process.exit(1); });

app.use('/api/credits', creditsRouter);
app.use('/api/billing', billingRouter);
app.use('/api/ai', aiRouter);

const port = Number(process.env.PORT || 4001);
app.listen(port, () => log.info(`Credit service listening on ${port}`));

export default app;
