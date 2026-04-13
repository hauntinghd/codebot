import express from 'express';
import { chargeCredits, getAvailableCbt } from '../services/creditsService';
import fetch from 'node-fetch';

const router = express.Router();

// Attach user from header for now (service-to-service auth)
router.use((req: any, _res, next) => {
  if (!req.user) {
    const uid = req.header('X-User-Id');
    if (uid) req.user = { id: uid };
  }
  next();
});

// ---- Helpers ----
function providerCostUsdForTokens(tokensIn: number, tokensOut: number) {
  // Conservative Grok fast pricing placeholder (adjust to your real pricing)
  const per1k_in = 0.0005;
  const per1k_out = 0.002;
  return ((tokensIn / 1000) * per1k_in) + ((tokensOut / 1000) * per1k_out);
}

function normalizeBase(url: string) {
  return url.replace(/\/+$/, '');
}

function getXaiConfig() {
  const apiKey = (process.env.XAI_API_KEY || process.env.OPENAI_API_KEY || '').trim();
  const base =
    (process.env.XAI_API_BASE_URL || process.env.XAI_BASE_URL || 'https://api.x.ai/v1').trim();
  const model = (process.env.XAI_MODEL || 'grok-4-1-fast').trim();

  return {
    apiKey,
    baseUrl: normalizeBase(base),
    model,
  };
}

// xAI/OpenAI-compatible response parsing
function extractText(json: any): string {
  // chat/completions style
  if (json?.choices?.[0]?.message?.content) return String(json.choices[0].message.content);
  if (json?.choices?.[0]?.text) return String(json.choices[0].text);

  // responses style (best effort)
  if (typeof json?.output_text === 'string') return json.output_text;
  if (Array.isArray(json?.output)) {
    for (const item of json.output) {
      if (item?.type === 'message' && Array.isArray(item?.content)) {
        const textPart = item.content.find((c: any) => c?.type === 'output_text' && c?.text);
        if (textPart?.text) return String(textPart.text);
      }
    }
  }
  return '';
}

function extractUsage(json: any) {
  // chat/completions style
  const usage = json?.usage || {};
  const inTokens = Number(usage.prompt_tokens || usage.input_tokens || 0);
  const outTokens = Number(usage.completion_tokens || usage.output_tokens || 0);
  return { inTokens, outTokens };
}

// ---- Routes ----

// POST /api/ai/plan (NORMAL_GENERATION)
router.post('/plan', async (req: any, res) => {
  const userId = req.user?.id;
  if (!userId) return res.status(401).json({ error: 'unauthenticated' });

  try {
    const prompt = String(req.body?.prompt || '');
    const maxTokens = Number(req.body?.max_tokens || 512);
    const temperature = Number(req.body?.temperature ?? 0.2);

    // Estimate CBT usage before calling provider (simple guard)
    const estimatedIn = Math.ceil(prompt.length / 4);
    const estimatedOut = maxTokens;
    const ratio = Number(process.env.CBT_PROVIDER_TOKEN_RATIO || 1000);
    const estimatedCbt = Math.max(1, Math.ceil((estimatedIn + estimatedOut) / ratio));

    const available = await getAvailableCbt(userId);
    if (available < estimatedCbt) {
      const err: any = new Error('Insufficient CBT balance (estimated)');
      err.status = 402;
      throw err;
    }

    const { apiKey, baseUrl, model } = getXaiConfig();
    if (!apiKey) return res.status(500).json({ error: 'XAI_API_KEY not configured' });

    const body = {
      model,
      messages: [
        {
          role: 'system',
          content:
            'You are CodeBot. Answer concisely. Provide code examples when relevant.',
        },
        { role: 'user', content: prompt },
      ],
      max_tokens: maxTokens,
      temperature,
    };

    // Use /chat/completions for xAI base
    const url = `${baseUrl}/chat/completions`;

    const providerResp = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify(body),
    });

    const txt = await providerResp.text();
    let json: any;
    try {
      json = JSON.parse(txt);
    } catch {
      json = txt;
    }

    if (!providerResp.ok) {
      return res.status(502).json({ error: 'Provider error', details: json });
    }

    const text = extractText(json);
    const usage = extractUsage(json);
    const inTokens = usage.inTokens || estimatedIn;
    const outTokens = usage.outTokens || 0;
    const providerCost = providerCostUsdForTokens(inTokens, outTokens);

    const charge = await chargeCredits(
      userId,
      'NORMAL_GENERATION',
      req.body?.requestId || `req-${Date.now()}`,
      inTokens,
      outTokens,
      providerCost,
    );

    return res.json({ ok: true, text, tokens: { in: inTokens, out: outTokens }, charge });
  } catch (e: any) {
    const status = e.status || 500;
    return res.status(status).json({ error: e.message || 'error' });
  }
});

// POST /api/ai/code (ARCHITECTURE_MODE)
router.post('/code', async (req: any, res) => {
  const userId = req.user?.id;
  if (!userId) return res.status(401).json({ error: 'unauthenticated' });

  try {
    const prompt = String(req.body?.prompt || '');
    const maxTokens = Number(req.body?.max_tokens || 1024);
    const temperature = Number(req.body?.temperature ?? 0.2);

    const estimatedIn = Math.ceil(prompt.length / 4);
    const estimatedOut = maxTokens;
    const ratio = Number(process.env.CBT_PROVIDER_TOKEN_RATIO || 1000);
    const estimatedCbt = Math.max(1, Math.ceil((estimatedIn + estimatedOut) / ratio));

    const available = await getAvailableCbt(userId);
    if (available < estimatedCbt) {
      const err: any = new Error('Insufficient CBT balance (estimated)');
      err.status = 402;
      throw err;
    }

    const { apiKey, baseUrl, model } = getXaiConfig();
    if (!apiKey) return res.status(500).json({ error: 'XAI_API_KEY not configured' });

    const body = {
      model,
      messages: [
        {
          role: 'system',
          content:
            'You are CodeBot. Provide code-focused answers with correct, runnable code.',
        },
        { role: 'user', content: prompt },
      ],
      max_tokens: maxTokens,
      temperature,
    };

    const url = `${baseUrl}/chat/completions`;

    const providerResp = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify(body),
    });

    const txt = await providerResp.text();
    let json: any;
    try {
      json = JSON.parse(txt);
    } catch {
      json = txt;
    }

    if (!providerResp.ok) {
      return res.status(502).json({ error: 'Provider error', details: json });
    }

    const text = extractText(json);
    const usage = extractUsage(json);
    const inTokens = usage.inTokens || estimatedIn;
    const outTokens = usage.outTokens || 0;
    const providerCost = providerCostUsdForTokens(inTokens, outTokens);

    const charge = await chargeCredits(
      userId,
      'ARCHITECTURE_MODE',
      req.body?.requestId || `req-${Date.now()}`,
      inTokens,
      outTokens,
      providerCost,
    );

    return res.json({ ok: true, text, tokens: { in: inTokens, out: outTokens }, charge });
  } catch (e: any) {
    const status = e.status || 500;
    return res.status(status).json({ error: e.message || 'error' });
  }
});

router.post('/charge', async (req: any, res) => {
  const userId = req.user?.id;
  if (!userId) return res.status(401).json({ error: 'unauthenticated' });

  const { feature, requestId, providerTokensIn, providerTokensOut, providerCostUsdEstimate } = req.body;
  try {
    const out = await chargeCredits(
      userId,
      feature,
      requestId,
      Number(providerTokensIn || 0),
      Number(providerTokensOut || 0),
      Number(providerCostUsdEstimate || 0),
    );
    return res.json(out);
  } catch (e: any) {
    const status = e.status || 500;
    return res.status(status).json({ error: e.message || 'error' });
  }
});

router.get('/balance', async (req: any, res) => {
  const userId = req.user?.id;
  if (!userId) return res.status(401).json({ error: 'unauthenticated' });
  const bal = await getAvailableCbt(userId);
  res.json({ availableCbt: bal });
});

export default router;
