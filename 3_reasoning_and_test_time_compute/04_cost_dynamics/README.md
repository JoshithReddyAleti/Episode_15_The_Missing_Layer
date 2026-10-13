# 💸 Cost Dynamics — The 10-100× Multiplier Math

> *You upgraded from GPT-4o to o3. Your inference bill went from $12K to $340K last month.*
>
> *"Yeah, but the answers are better."*
>
> *"Better enough to justify a 28× cost increase?"*
>
> *"...let me check."*

Reasoning models and test-time compute don't just cost more. They cost more in ways that break the cost models you built in [Folder 2](../../2_cost_engineering/README.md). This section is the honest cost math and the break-even analysis that decides whether it's worth it.

---

## The Cost Multiplier Anatomy

A single reasoning-model query costs more than a base-model query along **four dimensions**:

**1. Hidden reasoning tokens.** The model generates 5-20× more tokens than the visible answer. All billed as output tokens.

**2. Higher output token pricing.** Reasoning models are typically priced at premium tiers ($60-75/M output).

**3. Longer effective input.** Many reasoning workflows pack more context (few-shot exemplars, structured problem statements) than base workflows.

**4. Reduced cache benefit.** Reasoning tokens are non-deterministic — the same prompt produces different reasoning traces. Provider prompt caches still work on the input prefix, but reasoning outputs can't be cached across queries.

---

## The Per-Query Cost Table

Approximate 2026 pricing, for one moderately complex analytical query with ~500 tokens of input.

| Approach | Input tok | Output tok (visible) | Reasoning tok (hidden) | Total cost | Latency |
|---|---|---|---|---|---|
| GPT-4o mini, single shot | 500 | 400 | 0 | $0.000315 | ~1s |
| GPT-4o, single shot | 500 | 400 | 0 | $0.00525 | ~2s |
| Claude Sonnet, single shot | 500 | 400 | 0 | $0.0075 | ~2s |
| GPT-4o + best-of-4 + verifier | 2200 | 1800 | 0 | $0.0235 | ~4s parallel |
| GPT-4o + best-of-16 + verifier | 8500 | 7000 | 0 | $0.0913 | ~5s parallel |
| Claude 3.7 extended thinking (light: 2K budget) | 500 | 400 | 2000 | $0.0375 | ~10s |
| Claude 3.7 extended thinking (heavy: 16K budget) | 500 | 400 | 16000 | $0.246 | ~35s |
| DeepSeek-R1 (API) | 500 | 400 | 8000 | $0.0186 | ~15s |
| o1-mini high effort | 500 | 400 | 6000 | $0.0286 | ~15s |
| o1 default | 500 | 400 | 8000 | $0.512 | ~20s |
| o1 high effort | 500 | 400 | 20000 | $1.212 | ~45s |
| o3 default | 500 | 400 | 12000 | $0.752 | ~30s |
| o3 high effort | 500 | 400 | 30000+ | $1.812+ | ~60s+ |

**The spread: from $0.0003 to $1.81+ per query. Six orders of magnitude.**

**Reading this table:**
- Note DeepSeek-R1 as an outlier — very cheap for a reasoning model due to inference efficiency and pricing strategy
- Note that o1-mini high-effort is cheaper than o1 default — mini variants are competitive
- Note that GPT-4o + best-of-16 approaches reasoning-model cost with better latency (parallel)
- Note the latency: reasoning models are DOA for any interactive UX

---

## The Break-Even Formula

Given a base model and a reasoning model:

```
Base attempt cost:     C_b
Reasoning attempt cost: C_r
Base success rate:     S_b
Reasoning success rate: S_r
Escalation cost:       E

Base cost per success:      C_b/S_b + E×(1-S_b)
Reasoning cost per success: C_r/S_r + E×(1-S_r)

Reasoning wins when:
  C_r/S_r + E×(1-S_r) < C_b/S_b + E×(1-S_b)
```

**Rearranging:**
```
Reasoning wins when:
  C_r/S_r - C_b/S_b < E × (S_r - S_b)
```

**The intuition:**
- The extra reasoning cost (over amortized rates) must be less than
- The reduction in escalation cost from higher success rate

**Reasoning wins big when:**
- Success rate delta is large (S_r >> S_b)
- Escalation cost is high (E is large — human review, retry, incorrect action)

**Reasoning loses when:**
- Success rate delta is small (S_r ≈ S_b — task doesn't benefit)
- Escalation cost is low (E is small — errors are cheap to fix)

---

## Worked Example 1: Legal Contract Analysis

**Setup:**
- Task: identify all indemnification clauses in a 40-page contract
- Base (GPT-4o): 5000 tokens in, 1200 tokens out per attempt
- Reasoning (Claude 3.7 with 16K thinking budget): same input, 1200 visible + 16000 thinking

**Costs:**
```
Base: 5000×$2.50/M + 1200×$10/M = $0.0125 + $0.012 = $0.0245
Reasoning: 5000×$3/M + (1200+16000)×$15/M = $0.015 + $0.258 = $0.273
```

**Success rates (measured on golden set):**
- Base: 68% (misses subtle clauses)
- Reasoning: 91%

**Escalation cost:** $50 (paralegal review of missed clauses)

**Cost per success:**
```
Base: $0.0245/0.68 + $50×0.32 = $0.036 + $16 = $16.04
Reasoning: $0.273/0.91 + $50×0.09 = $0.30 + $4.50 = $4.80
```

**Reasoning wins by $11.24 per contract — 70% cost reduction despite 11× per-query cost.**

**Why:** high escalation cost ($50) dominates. Reducing missed clauses is worth much more than the reasoning premium.

**Verdict:** ship reasoning model. Cost savings scale with volume.

---

## Worked Example 2: Customer Support FAQ

**Setup:**
- Task: answer common support questions from KB
- Base (GPT-4o mini): 3000 tokens in (with retrieved KB), 200 tokens out
- Reasoning (o3-mini medium effort): same input, 200 visible + 4000 thinking

**Costs:**
```
Base: 3000×$0.15/M + 200×$0.60/M = $0.00045 + $0.00012 = $0.00057
Reasoning: 3000×$1.10/M + (200+4000)×$4.40/M = $0.0033 + $0.01848 = $0.02178
```

**Success rates:**
- Base: 91%
- Reasoning: 93%

**Escalation cost:** $1.20 (route to human support)

**Cost per success:**
```
Base: $0.00057/0.91 + $1.20×0.09 = $0.00063 + $0.108 = $0.109
Reasoning: $0.02178/0.93 + $1.20×0.07 = $0.02342 + $0.084 = $0.107
```

**Reasoning wins by $0.002 per success — noise level.**

**But** latency: base 1s, reasoning 12s. Support agents wait 12s for AI to think. UX destroyed.

**Verdict:** base model. The tiny cost-per-success advantage doesn't justify the latency penalty. Any product improvement here should come from better retrieval, not reasoning.

---

## Worked Example 3: Autonomous Agent Planner

**Setup:**
- Task: decompose a user goal into a task plan (5-15 sub-tasks)
- Planner runs once per session; execution uses base model repeatedly
- Base (GPT-4o) planner: 3000 tokens in, 800 out
- Reasoning (o3 default) planner: 3000 in, 800 visible + 12000 thinking

**Costs (planner call only):**
```
Base: 3000×$2.50/M + 800×$10/M = $0.0075 + $0.008 = $0.0155
Reasoning: 3000×$15/M + (800+12000)×$60/M = $0.045 + $0.768 = $0.813
```

**Success rate of the whole task:**
- Base planner: 55% (bad plans cascade to bad execution)
- Reasoning planner: 82% (much better decomposition)

**Escalation cost:** $30 (user gives up, or task fails visibly, or manual re-execution)

**But** — the reasoning planner call is only 1 of ~10 LLM calls in the session. Execution is base model regardless.

**Per-session cost:**
```
Base session: $0.0155 (planner) + 9×$0.02 (execution) = $0.20
Reasoning session: $0.813 (planner) + 9×$0.02 (execution) = $0.99
```

**Cost per successful session:**
```
Base: $0.20/0.55 + $30×0.45 = $0.36 + $13.5 = $13.86
Reasoning: $0.99/0.82 + $30×0.18 = $1.21 + $5.4 = $6.61
```

**Reasoning wins by $7.25 per successful session — 52% reduction.**

**Verdict:** ship reasoning planner. Execution stays base. Hybrid win.

---

## The Cache Penalty

**Reasoning models integrate poorly with prompt caching.**

**Why:**
- Reasoning tokens are non-deterministic per generation
- Provider prompt caches store the *prefix* only; reasoning appears in output
- Same input prompt → different reasoning trace → different KV state
- Cache hit rates that were 60% on base models drop to near-zero on reasoning outputs

**But:**
- Input prefix caching still works — system prompt + few-shot are still cacheable
- Semantic cache still works on user query
- What you lose is *response-level* caching (very common in RAG)

**Practical impact:**
- Base model with 60% cache hit rate → effective cost = 40% of raw cost
- Reasoning model with 5% cache hit rate → effective cost = 95% of raw cost
- The cache discount that made base models affordable at scale doesn't apply to reasoning

**Design consequence:** don't route to reasoning models by default. Use them for specific tasks. Keep cache-friendly workloads on base models.

---

## Latency Cost — The Non-Financial Cost

A 30-second reasoning response is not just $0.75. It's also:

- **Session state maintained for 30s per user.** At 10K concurrent users, that's real infrastructure.
- **Users leaving.** In interactive UX, latency > 3s causes measurable dropoff.
- **Perceived unreliability.** Long delays feel like the system is broken, even when it works.
- **Compounding in agents.** A 10-step agent with 30s reasoning per step = 5-minute task. Users don't wait.

**Rule of thumb: multiply LLM cost by 1.5-3× to account for latency-driven user cost when in interactive workflows.**

---

## Governance Implications

Reasoning models break several assumptions from [Folder 2 Cost Governance](../../2_cost_engineering/05_cost_at_scale/README.md):

**1. Per-query cost variance is huge.**
- Base model: P50 and P99 within 2×
- Reasoning model: P50 to P99 can be 5-10× (depending on how much reasoning triggered)

**2. Budget forecasting is harder.**
- Reasoning token counts vary widely by task
- Hard to project month-end spend without historical data per feature

**3. Runaway detection needs new thresholds.**
- Base model runaway: cost > 10× baseline
- Reasoning model runaway: cost > 100× baseline (harder to distinguish from legitimate hard problem)

**Recommended governance additions when reasoning is in the mix:**
- **Per-feature reasoning quotas:** cap how many reasoning queries per user per day
- **Reasoning tier accounting:** track cost separately for reasoning vs base traffic
- **Latency SLA per tier:** users on interactive features never get routed to slow tiers
- **Reasoning effort caps:** default to low or medium effort; require explicit user consent for high effort in cost-sensitive contexts

---

## The Provider Pricing Reality (2026)

**Anthropic:**
- Claude 3.7 Sonnet extended thinking: input $3/M, output $15/M (includes thinking)
- Budget-configurable — you set max thinking tokens per request
- Prompt caching applies to input prefix

**OpenAI:**
- o1 / o3 / o4 tiers: input $15/M, output $60/M (includes reasoning)
- reasoning_effort parameter: low/medium/high
- Cache discount on prefix; reasoning tokens uncached

**Google:**
- Gemini 2.5 Flash Thinking: input $0.15/M, output $3.50/M
- Gemini 2.5 Pro Thinking: input $1.25/M, output $10/M
- thinking_budget parameter
- Explicit caching API

**DeepSeek:**
- R1 API: input $0.55/M, output $2.19/M — dramatically cheaper than Western providers
- Open weights available for self-hosting
- Full reasoning trace exposed

**Choose provider based on:**
- Cost sensitivity → DeepSeek-R1 (very cheap) or Gemini Flash Thinking (cheap-ish)
- Latency sensitivity → mini-tier reasoning (o1-mini, o3-mini, Gemini Flash Thinking)
- Quality frontier → o3, Claude Opus thinking, o4 (as available)
- Enterprise compliance → Anthropic (contract terms) or Bedrock (AWS integration)
- Full inspection needed → visible-reasoning models (Claude, DeepSeek, Gemini)

---

## Files In This Folder

| File | Concept |
|---|---|
| [`per_query_cost_table.py`](per_query_cost_table.py) | Cost calculator for all tiers at reference workloads |
| [`break_even_analysis.py`](break_even_analysis.py) | Reasoning vs base cost-per-success calculator |
| [`cache_penalty.py`](cache_penalty.py) | Modeling cache degradation on reasoning routes |
| [`latency_cost.py`](latency_cost.py) | Non-financial cost of long response times |
| [`reasoning_governance.py`](reasoning_governance.py) | Per-tier quotas and budget tracking |

---

## The Staff Interview Question

*"You're proposing a reasoning-model feature. Walk the CFO through the cost."*

**The wrong answer:** "It's about 20× more expensive per query but users get better answers."

**The right answer:**
*"Two views. Per-query cost, and cost per successful task. Per-query, reasoning is 10-100× base — the exact multiple depends on model tier, reasoning effort, and how much hidden thinking the model does. Doesn't matter on its own; matters compared to success rate. Cost per successful task is the real comparison. If reasoning takes success rate from 68% to 91% on a task with $50 escalation cost — we go from $16 per success to $4.80 per success. That's a 70% cost reduction *despite* 11× per-query cost. If reasoning takes success rate from 91% to 93% on a task with $1 escalation cost — the delta is noise and the latency penalty kills UX. Same technology, different economics. For this proposal, the task is X, the escalation cost is Y, and the projected success rate improvement is Z. That gives cost per successful task of A with reasoning vs B without. At our projected volume, monthly cost is C vs D. And we've built in reasoning-tier governance: per-user quotas, tier accounting, effort caps. Any single-feature runaway is caught within 60 seconds. Here's the model."*

That's a CFO conversation.

---

*Previous: [← Test-Time Compute Patterns](../03_test_time_compute_patterns/README.md) · Return to [folder README](../README.md) · Next: [Verifier Patterns →](../05_verifier_patterns/README.md)*
