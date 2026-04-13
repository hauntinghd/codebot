# CodeBot Token (CBT) Pricing Reference

**Purpose:** Mathematically correct CBT deduction per provider/model. All prices per **1 million tokens** unless noted.  
**Source:** Official docs (xAI, OpenAI, Anthropic) — Feb 2025.

---

## 1. Provider Pricing (per 1M tokens)

### xAI (Grok) — Cheapest for CodeBot

| Model | Input | Output | Cached Input | Best For |
|-------|-------|--------|--------------|----------|
| **grok-4-1-fast-reasoning** | $0.20 | $0.50 | $0.05 | Router, Engineer (default) |
| **grok-4-1-fast-non-reasoning** | $0.20 | $0.50 | $0.05 | Faster, no reasoning tokens |
| **grok-4-fast-reasoning** | $0.20 | $0.50 | $0.05 | Same as above |
| **grok-4-fast-non-reasoning** | $0.20 | $0.50 | $0.05 | Same as above |
| **grok-code-fast-1** | $0.20 | $1.50 | $0.02 | Code-specific (higher output cost) |
| **grok-3-mini** | $0.30 | $0.50 | $0.07 | Fallback |
| **grok-3** | $3.00 | $15.00 | $0.75 | Premium |
| **grok-4-0709** | $3.00 | $15.00 | $0.75 | Premium |

**Blended cost (typical 1:1 input/output):** ~$0.35 per 1M tokens for fast models.

---

### OpenAI (GPT)

| Model | Input | Output | Cached Input | Best For |
|-------|-------|--------|--------------|----------|
| **GPT-5.2** | $1.75 | $14.00 | $0.175 | Best coding (flagship) |
| **GPT-5 mini** | $0.25 | $2.00 | $0.025 | Cheap, fast |
| **GPT-4.1** | $3.00 | $12.00 | $0.75 | Fine-tune / legacy |
| **GPT-4.1 mini** | $0.80 | $3.20 | $0.20 | Budget |
| **GPT-4.1 nano** | $0.20 | $0.80 | $0.05 | Cheapest |
| **GPT-4o** | $2.50 | $10.00 | $1.25 | Multimodal |
| **gpt-realtime** | $4.00 | $16.00 | $0.40 | Realtime |
| **gpt-realtime-mini** | $0.60 | $2.40 | $0.06 | Realtime cheap |

**Blended cost (1:1):** GPT-5.2 ~$7.88/1M, GPT-5 mini ~$1.13/1M, GPT-4.1 nano ~$0.50/1M.

---

### Anthropic (Claude)

| Model | Input | Output | Cache Read | Best For |
|-------|-------|--------|------------|----------|
| **Claude Opus 4.6** | $5.00 | $25.00 | $0.50 | Best quality |
| **Claude Opus 4.5** | $5.00 | $25.00 | $0.50 | Same |
| **Claude Opus 4.1** | $15.00 | $75.00 | $1.50 | Premium |
| **Claude Sonnet 4.6** | $3.00 | $15.00 | $0.30 | Coding sweet spot |
| **Claude Sonnet 4.5** | $3.00 | $15.00 | $0.30 | Same |
| **Claude Sonnet 4** | $3.00 | $15.00 | $0.30 | Same |
| **Claude Haiku 4.5** | $1.00 | $5.00 | $0.10 | Budget |
| **Claude Haiku 3.5** | $0.80 | $4.00 | $0.08 | Cheapest |
| **Claude Haiku 3** | $0.25 | $1.25 | $0.03 | Ultra cheap |

**Blended cost (1:1):** Opus 4.6 ~$15/1M, Sonnet 4.6 ~$9/1M, Haiku 3 ~$0.75/1M.

---

## 2. Cost Comparison (1M tokens, 1:1 input/output blend)

| Provider | Model | Cost/1M tokens |
|----------|-------|----------------|
| xAI | grok-4-1-fast-reasoning | **$0.35** |
| xAI | grok-code-fast-1 | $0.85 |
| OpenAI | GPT-4.1 nano | $0.50 |
| OpenAI | GPT-5 mini | $1.13 |
| Anthropic | Claude Haiku 3 | $0.75 |
| OpenAI | GPT-4.1 mini | $2.00 |
| Anthropic | Claude Haiku 4.5 | $3.00 |
| OpenAI | GPT-4o | $6.25 |
| Anthropic | Claude Sonnet 4.6 | $9.00 |
| OpenAI | GPT-5.2 | $7.88 |
| Anthropic | Claude Opus 4.6 | $15.00 |
| xAI | grok-3 | $9.00 |

**xAI Grok fast is ~20–40x cheaper than Claude Opus and ~5–20x cheaper than GPT-5.2.**

---

## 3. CBT Formula (Provider-Aware)

**User-facing:** 1 CBT = $0.002 (from `CBT_PER_USD = 500` → $1 = 500 CBT).

**Provider cost (USD):**
```
cost_usd = (input_tokens / 1_000_000) * input_per_1M + (output_tokens / 1_000_000) * output_per_1M
```

**CBT to charge (with margin):**
```
cbt_charge = ceil(cost_usd / cbt_per_usd)   # cbt_per_usd = 0.002
# Add margin: cbt_charge = ceil(cost_usd / cbt_per_usd * (1 + margin))
# e.g. 25% margin: cbt_charge = ceil(cost_usd / 0.0016)  # effective $0.0016 per CBT to you
```

**Per-model lookup:** Store `(input_per_1M, output_per_1M)` per model ID; compute `cost_usd` from actual `input_tokens` and `output_tokens` returned by the API.

---

## 4. Recommended Config Structure

```python
# backend/config.py or dedicated pricing module
MODEL_PRICING_PER_1M = {
    # xAI
    "grok-4-1-fast-reasoning": {"input": 0.20, "output": 0.50},
    "grok-4-1-fast-non-reasoning": {"input": 0.20, "output": 0.50},
    "grok-4-fast-reasoning": {"input": 0.20, "output": 0.50},
    "grok-4-fast-non-reasoning": {"input": 0.20, "output": 0.50},
    "grok-code-fast-1": {"input": 0.20, "output": 1.50},
    "grok-3-mini": {"input": 0.30, "output": 0.50},
    "grok-3": {"input": 3.00, "output": 15.00},
    # OpenAI
    "gpt-5.2": {"input": 1.75, "output": 14.00},
    "gpt-5-mini": {"input": 0.25, "output": 2.00},
    "gpt-4.1": {"input": 3.00, "output": 12.00},
    "gpt-4.1-mini": {"input": 0.80, "output": 3.20},
    "gpt-4.1-nano": {"input": 0.20, "output": 0.80},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    # Anthropic
    "claude-opus-4.6": {"input": 5.00, "output": 25.00},
    "claude-sonnet-4.6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4.5": {"input": 1.00, "output": 5.00},
    "claude-haiku-3.5": {"input": 0.80, "output": 4.00},
    "claude-haiku-3": {"input": 0.25, "output": 1.25},
}

CBT_PER_USD = 500  # 1 CBT = $0.002
CBT_MARGIN = 0.25  # 25% markup

def cost_usd_for_model(model_id: str, input_tokens: int, output_tokens: int) -> float:
    p = MODEL_PRICING_PER_1M.get(model_id) or MODEL_PRICING_PER_1M.get("grok-4-1-fast-reasoning")
    return (input_tokens / 1e6) * p["input"] + (output_tokens / 1e6) * p["output"]

def cbt_to_charge(model_id: str, input_tokens: int, output_tokens: int) -> int:
    cost = cost_usd_for_model(model_id, input_tokens, output_tokens)
    cbt_per_usd = CBT_PER_USD * (1 - CBT_MARGIN)  # effective cost to you
    return max(1, int(cost * cbt_per_usd) + (1 if cost * cbt_per_usd % 1 else 0))
```

---

## 5. Multi-Layer Cost (Router + Engineer + Auditor + Corrector)

CodeBot runs 4–5 layers. Each has its own model and token count:

| Layer | Typical Model | Est. Tokens (in/out) | Est. Cost |
|-------|---------------|---------------------|-----------|
| Router | grok-4-1-fast | 500 / 300 | ~$0.0003 |
| Engineer | grok-4-1-fast or user's | 2000 / 1500 | ~$0.001 |
| Auditor | same as Engineer | 1500 / 500 | ~$0.0006 |
| Corrector | (optional LLM or rules) | 0 or 200/100 | ~$0.0001 |

**Total per request (Grok):** ~$0.002–0.003. At 1 CBT = $0.002, that’s **1–2 CBT per request** at cost. With 25% margin: **2–3 CBT**.

---

## 6. Implementation Checklist

- [ ] Add `MODEL_PRICING_PER_1M` (or equivalent) keyed by model ID
- [ ] Compute `cost_usd` from real `input_tokens` + `output_tokens` from each API response
- [ ] Sum cost across Router, Engineer, Auditor (and Corrector if LLM-based)
- [ ] Map model ID from `provider_resolver` / response metadata
- [ ] Charge CBT = `ceil(cost_usd * CBT_PER_USD * (1 + margin))`
- [ ] Fallback to `grok-4-1-fast-reasoning` pricing if model unknown
- [ ] Revisit pricing quarterly (providers change often)

---

## 7. Source URLs

- xAI: https://docs.x.ai/docs/models  
- OpenAI: https://openai.com/api/pricing, https://platform.openai.com/docs/pricing  
- Anthropic: https://docs.anthropic.com/en/docs/about-claude/pricing  
