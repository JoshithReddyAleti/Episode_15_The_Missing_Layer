# 💰 Cost Engineering — The Discipline Nobody Prepares For

> *Every enterprise AI project I've killed died on unit economics. Not on quality. Not on integration. Not on data. On the moment someone did the math and said "we cannot afford to serve this at scale."*
>
> *This is the section that would have saved those projects.*

Cost is not a metric you optimize after launch. It's an architectural discipline you design *for* from day one.

Miss this and here's what happens:

- Your demo cost $50 to build. Your production system costs $500K/month.
- Your P95 user query is $0.02. Your P99 is $2.40 because the LLM burned through max_tokens with tool calls.
- Your CEO asks "how much does one customer cost us?" and your answer is a shrug.
- Your CFO learns you're paying 12× more than a competitor doing the same thing and starts asking uncomfortable questions.
- Your product manager wants to add a feature. The feature 3× your inference bill. Nobody caught it before shipping.

This folder is the toolkit that prevents all of that.

---

## 🎯 What This Folder Is About

Five disciplines that together make cost a first-class engineering concern:

1. **Unit Economics** — Cost per completed task, not cost per API call
2. **Cache Hierarchy** — Semantic cache, prompt cache, KV cache — 40-90% cost reduction if you stack them right
3. **Model Routing** — Small model default, escalate to large when needed — the single highest-ROI cost pattern
4. **Provider Economics** — Buy vs build math, when self-hosting flips the equation, real 2026 pricing
5. **Cost at Scale** — Per-tenant budgets, alerts, forecasting, cost observability

Master these and cost becomes a lever you *pull*, not a wall you *hit*.

---

## 📁 What's In This Folder

| Section | What It Covers | When You Need It |
|---|---|---|
| [`01_unit_economics/`](01_unit_economics/) | Cost per successful task · journey math · marginal vs allocated · CAC/LTV in AI | Before you set pricing · before board conversations |
| [`02_cache_hierarchy/`](02_cache_hierarchy/) | Semantic cache · prompt cache (provider-side) · KV cache · cache invalidation · hit rate tuning | Every production LLM app |
| [`03_model_routing/`](03_model_routing/) | Small→large escalation · router as classifier · quality/cost frontier · router evaluation | Any product with variable query complexity |
| [`04_provider_economics/`](04_provider_economics/) | Real 2026 pricing tables · vLLM/TGI throughput math · break-even for self-hosting · reserved vs spot | Any decision about model provider |
| [`05_cost_at_scale/`](05_cost_at_scale/) | Per-tenant budgets · runaway detection · forecasting · cost dashboards · unit economics reporting | Any multi-tenant SaaS · any enterprise deployment |

---

## 🧮 The Mental Model Shift

The most important idea in this entire folder:

**Wrong question:** *"How much does each LLM call cost?"*
**Right question:** *"How much does completing one user task cost?"*

**Wrong question:** *"What's our token consumption this month?"*
**Right question:** *"What's our cost per active user? Per completed task? Per successful outcome?"*

**Wrong question:** *"Can we afford the LLM bill?"*
**Right question:** *"Is our unit contribution margin positive at current scale, and does it improve or degrade as we grow?"*

Every LLM app is a business. Every business needs unit economics. Every unit economic in an LLM app decomposes into: cost per LLM call × calls per task × task attempts per successful outcome × cost of successful outcome vs revenue.

If you don't know these numbers for your product, you don't know your product.

---

## 💸 The Five Cost Layers of an LLM Product

Every LLM app pays for infrastructure at five layers. Optimize the wrong one and you save pennies while overspending dollars.

**Layer 1: Inference cost.** The provider bill. Most visible, most obsessed-over.

**Layer 2: Embedding + retrieval cost.** Every RAG query hits an embedding model AND a vector DB. Small numbers per query, but they add up at scale.

**Layer 3: Storage cost.** Vector DB storage, conversation history, cache backends, audit logs. Grows monotonically unless you actively manage it.

**Layer 4: Compute + platform cost.** Your BFF servers, streaming infrastructure, orchestration. Fixed overhead + scales with concurrency.

**Layer 5: Human cost.** Human-in-the-loop review, red team hours, prompt engineering, evaluation. The most expensive layer nobody puts on the finance spreadsheet.

**Where teams focus vs where the money actually goes:**

| Layer | Team obsession | Actual $ share (typical B2B RAG) |
|---|---|---|
| Inference | 90% | 50-70% |
| Embedding + retrieval | 5% | 10-20% |
| Storage | 2% | 5-10% |
| Compute / platform | 3% | 10-20% |
| Human | 0% | 5-20%+ |

**The insight:** teams over-optimize inference and under-invest in the other four. The other four are often where the leverage is.

---

## 📊 The 2026 Cost Landscape (Approximate)

**Provider inference pricing (per million tokens, ballpark 2026):**

| Model | Input | Output | Best for |
|---|---|---|---|
| GPT-4o mini | $0.15 | $0.60 | Cheap default; classification; simple tasks |
| Claude Haiku | $0.25 | $1.25 | Cheap default; fast responses |
| Gemini 2.0 Flash | $0.10 | $0.40 | Cheapest capable model |
| DeepSeek-V3 | $0.14 | $0.28 | Very cheap for reasoning-lite tasks |
| GPT-4o | $2.50 | $10.00 | Balanced quality/cost |
| Claude Sonnet | $3.00 | $15.00 | Strong reasoning; agent workflows |
| Gemini 2.5 Pro | $1.25 | $5.00 | Long context (2M) |
| Claude Opus | $15.00 | $75.00 | Highest quality |
| o1 / o3 | $15.00 | $60.00+ | Reasoning-heavy tasks |

**Prompt caching (2026, provider-side):**

- **Anthropic:** ~90% discount on cached input tokens (5-minute TTL, extendable).
- **OpenAI:** ~50% discount on cached input tokens (automatic; 5-10 min TTL).
- **Gemini:** ~75% discount on cached input tokens (explicit caching API).

**Self-hosting rough baseline (2026):**

- H100 80GB on AWS: ~$4-5/hr on-demand, ~$2-3/hr reserved
- vLLM throughput (Llama 3 70B on 2× H100): ~5000-8000 output tok/s aggregate
- Break-even vs GPT-4o: ~15-30M tokens/hour sustained load

**Numbers to memorize:**

- **1 second of an LLM response** ≈ 30-50 tokens
- **1 typical chat turn** ≈ 500-2000 tokens (system prompt + user + assistant)
- **1 RAG query** ≈ 2000-8000 tokens (retrieved context is 60-80% of the tokens)
- **1 agent task with 5 tool calls** ≈ 15,000-50,000 tokens
- **1M queries at 3K tokens each on GPT-4o** ≈ $30,000 with no caching

---

## 🏗️ The Cost Architecture Diagram

```
                    User request
                          │
                          ▼
              ┌───────────────────────┐
              │       BFF Layer        │
              │                        │
              │  ┌──────────────────┐  │
   Layer 1 -> │  │ Response cache   │◄─┼── HIT (~5-15% typical)
              │  └──────────────────┘  │
              │           │            │
              │           ▼            │
              │  ┌──────────────────┐  │
   Layer 2 -> │  │ Semantic cache   │◄─┼── HIT (~10-30% typical)
              │  └──────────────────┘  │
              │           │            │
              │           ▼            │
              │  ┌──────────────────┐  │
   Layer 3 -> │  │ Router (classifier) │
              │  └──────────────────┘  │
              │           │            │
              │     ┌─────┼─────┐      │
              │     ▼           ▼      │
              │  small       large     │
              │  model       model     │
              │     │           │      │
              │     ▼           ▼      │
              │  ┌─────────────────┐   │
   Layer 4 -> │  │ Provider prompt │◄──┼── 50-90% discount on cached prefix
              │  │ cache           │   │
              │  └─────────────────┘   │
              └───────────────────────┘
                          │
                          ▼
                       Response
```

Every layer either eliminates a call or reduces its cost. Stack them and you can achieve **60-80% cost reduction** vs a naive architecture.

---

## 🎯 The Unit Economic Formula

For any LLM feature, cost per successful task is:

```
cost_per_success = (cost_per_llm_call × calls_per_task_attempt)
                 × (1 / success_rate)
                 + fixed_costs_per_task
```

**Worked example — Customer support copilot:**

- Cost per LLM call (with caching, routing): $0.008
- Calls per task attempt: 4 (initial + 2 tool calls + 1 final response)
- Success rate: 75% (25% of tickets require escalation to human)
- Fixed costs per task: $0.002 (retrieval, storage, observability)

```
cost_per_success = ($0.008 × 4) × (1/0.75) + $0.002
                = $0.032 × 1.333 + $0.002
                = $0.045
```

**Now the business question:**
- Revenue per ticket resolved: $2.50 (savings vs human agent)
- Contribution margin: $2.50 - $0.045 = $2.455
- **Marginal profit: 98%**

Great business.

**Change one variable — success rate drops to 50%:**

```
cost_per_success = $0.032 × 2.0 + $0.002 = $0.066
```

Still fine. But now factor in escalation cost:

```
cost_per_success = $0.032 × 2.0 + $0.002 + (0.5 × $8_human_cost)
                = $0.066 + $4.00
                = $4.07
```

**Contribution margin: -$1.57.**

You are now paying customers to use your product.

**This is what "cost engineering" actually is:** understanding these formulas well enough to know which variable to move to fix the economics.

---

## 🧠 The Interview Angle

Staff-level cost questions come in three flavors:

**"How much would this cost at scale?"**

The wrong answer estimates only inference cost.

The right answer computes cost per successful task at three volume points: 10K/day, 1M/day, 100M/day. Includes cache hit rate ramp, model routing effectiveness, storage growth, and human review costs. Shows the crossover point where self-hosting flips the math.

**"Our LLM bill just tripled. Debug it."**

The wrong answer: "Let me look at the logs."

The right answer:

*"Three most likely causes. First — did success rate degrade? A drop from 80% to 50% success doubles cost per successful task without changing raw usage. Second — did cache hit rate degrade? A prompt change invalidates the provider prompt cache and can wipe out a 50% discount overnight. Third — did an upstream integration start sending malformed queries that cause the router to escalate to the expensive model?  Let me pull cost per successful task by product feature over the last 30 days, cache hit rates by prompt version, and router escalation rates by input source. That'll narrow it in an hour."*

**"When would you self-host instead of using an API?"**

The wrong answer: "When it's cheaper."

The right answer:

*"Three conditions must all hold. One: sustained load high enough to keep GPUs > 50% utilized 24/7 — usually 15-30M tokens/hour for a 70B model. Below that, provider APIs win. Two: latency requirements the API can't meet, or model customization the API doesn't offer. Three: an operations team that can actually run GPU inference in production, including the incidents. If any of those three fail, provider APIs are the right call. And even when you self-host, you usually keep a provider API as fallback for burst capacity and disaster recovery — hybrid is more common than pure self-hosting."*

---

## 🔗 What This Folder Connects To

- **Depends on:** Ep 12 (Inference & Model Serving), Ep 14 (A/B Testing for cost measurement)
- **Bridges to:** Folder 3 (Reasoning Models — 10-100× cost multiplier)
- **Deep dive references:** Anthropic prompt caching docs, OpenAI prompt caching docs, vLLM performance benchmarks

---

## 📚 How To Read This Folder

**If you have 90 minutes:** Read this README + [`01_unit_economics/`](01_unit_economics/README.md) + [`03_model_routing/`](03_model_routing/README.md). That's the 80/20.

**If you have a weekend:** Read all 5 sub-READMEs and run [`code_examples/`](code_examples/). That's operational fluency.

**If you're prepping for a staff interview:** Read [`docs/INTERVIEW_PREP.md`](docs/INTERVIEW_PREP.md) — every "how would you keep costs down" question mapped to the right answer.

**If you're actually building this at work:** Read [`docs/DECISION_FRAMEWORK.md`](docs/DECISION_FRAMEWORK.md) and [`docs/COST_MODEL_TEMPLATE.md`](docs/COST_MODEL_TEMPLATE.md) — drop them into your design docs.

---

*Return to [Episode 15 main README](../README.md) · Previous: [← LLM Application Architecture Patterns](../1_llm_application_architecture_patterns/) · Next folder: [Reasoning Models →](../3_reasoning_models/)*
