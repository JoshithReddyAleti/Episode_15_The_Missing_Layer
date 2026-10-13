# 🧭 Reasoning & Test-Time Compute Decision Framework

Drop this into your design doc for any feature considering reasoning models or test-time compute scaling.

## Step 1: Is This A Reasoning-Friendly Task?

Check the task category:

| Category | Verdict |
|---|---|
| Multi-step math, formal logic | **Yes** — reasoning wins |
| Competitive coding, algorithm design | **Yes** — reasoning wins |
| Root-cause debugging | **Yes** — reasoning wins |
| Multi-hop research synthesis | **Yes if budget** — reasoning helps but marginally |
| Boilerplate code, format tasks | **No** — use base model |
| Simple factual QA | **No** — use base model |
| Creative writing, dialogue | **No, or actively worse** — base model |
| Real-time interactive UX | **No** — latency kills it |

**If no**, stop. Use base model with prompt engineering and cache stack.

## Step 2: Do You Have A Verifier?

| Signal available | Verifier class | Test-time compute viable? |
|---|---|---|
| Unit tests, symbolic check, schema | Formal | Yes, scales beautifully |
| Task-specific validator (parse, compile, format) | Task-specific | Yes, use as pre-filter |
| LLM-judge on structured task | Class 3 | Yes but tune carefully |
| LLM-judge on subjective task | Class 4 | Limited, plateaus fast |
| Nothing | None | Single-shot only |

**If no verifier**, single-shot reasoning model is your only test-time compute option.

## Step 3: What's Your Latency Budget?

| Budget | Options |
|---|---|
| < 500ms | Base model, aggressive cache. No reasoning. |
| 1-5s | Base + BoN parallel, or mini reasoning (Gemini Flash Thinking, o3-mini low effort) |
| 5-30s | Reasoning models in play (Claude 3.7, o1-mini, DeepSeek-R1) |
| 30-120s | Full reasoning at medium/high effort (o1, o3, Claude Opus thinking) |
| Minutes+ | Tree search, verifier ensembles, high-effort reasoning + BoN |

## Step 4: What Compute Ladder Rung?

Climb until quality is sufficient. Stop when marginal quality no longer justifies marginal cost.

| Rung | Approach | Multiplier vs base |
|---|---|---|
| 1 | Base model, single shot | 1× |
| 2 | Base + prompt engineering | 1× |
| 3 | Base + BoN(4) + cheap verifier | 4-5× |
| 4 | Base + BoN(16) + strong verifier | 16-20× |
| 5 | Base + BoN(8) + verifier ensemble | 25-30× |
| 6 | Reasoning model, low effort | 20-40× |
| 7 | Reasoning model, medium/high effort | 50-200× |
| 8 | Reasoning + BoN + verifier | 200-800× |

## Step 5: How Do You Govern The Cost?

- **Per-user reasoning quota** (daily reasoning-tier query cap)
- **Per-feature reasoning budget** (monthly cost cap on reasoning tier)
- **Reasoning effort default** (low/medium/high per feature)
- **Cost alerting** at 10× baseline for reasoning-tier queries
- **Cost accounting** separate for reasoning vs base traffic

## Combined Decision — Worked Example

**Legal contract clause identifier:**

- Category: multi-step analysis with high stakes → reasoning-friendly
- Verifier: LLM-judge on structured clause extraction (Class 3, ~85% accuracy)
- Latency budget: 30-60s (users OK to wait for legal analysis)
- Chosen rung: 6 (Claude 3.7 Sonnet extended thinking, 16K budget)
- Governance: reasoning-tier quota (50 contracts/user/day), monthly budget cap $5K per firm, cost alert at 3× baseline

**Result:** cost per successful clause identification: $4.80 (vs $16 with base model). Reasoning wins because escalation cost is high ($50 paralegal review).

**Consumer chatbot for shipping FAQ:**

- Category: simple factual QA → NOT reasoning-friendly
- Verifier: trivial (does answer mention shipping?)
- Latency budget: < 1s
- Chosen rung: 1 (base model with cache stack)
- Reasoning: never route here

**Result:** cost per query $0.00057. Cache hit rate 55%. Reasoning would 100× the cost with no measurable quality gain.
