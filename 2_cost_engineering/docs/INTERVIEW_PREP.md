# 🎯 Interview Prep — Cost Engineering

Cost questions come in three flavors at staff-level. This doc maps common questions to the right sections.

## The Universal Opener

For any "how would you keep costs down" question:

*"Cost engineering is a discipline, not an optimization. Five levers, in priority order: unit economics measurement first — you can't optimize what you don't measure. Cache stack — three layers, 50-70% reduction typical. Model routing — another 40-60% on remaining traffic. Provider economics — hybrid pattern with provider API primary. Governance layer — per-tenant budgets, anomaly detection, forecasting. Let me walk through each in the context of your problem."*

## Question Bank

### "How much does this feature cost per user?"

**Lean on:** Unit Economics.

**Structure:** decompose into tasks per user × cost per successful task. Cost per success decomposes further. Name every term. Identify dominant lever.

### "Our LLM bill just tripled. Debug it."

**Lean on:** Cost at Scale (observability), Cache Hierarchy (regressions), Model Routing (escalation shifts).

**Three most likely causes:**
1. Success rate regression → escalation cost dominates
2. Cache hit rate collapse (prompt update invalidated cache)
3. Router misbehavior (escalating too often)

**Answer:** "Pull cost per successful task by feature over 30 days, cache hit rates by prompt version, router escalation rates by input source. That narrows it in an hour."

### "How would you cut LLM inference cost by 50%?"

**Lean on:** Cache Hierarchy + Model Routing.

**Structure:**
1. Cache stack (50-60% reduction)
2. Model routing (40-60% of remaining)
3. Prompt optimization (15-25% of remaining)

Combined: 70-80% reduction realistic if starting unoptimized.

### "When would you self-host instead of using an API?"

**Lean on:** Provider Economics.

**Three conditions must hold:** sustained load, API limitations, ops team. Break-even math around 15-30M tok/hr for 70B models.

Even at scale, hybrid is more common than pure self-hosting.

### "How do you keep costs from surprising your CFO?"

**Lean on:** Cost at Scale (governance).

**Four layers:** budgets, runaway detection, forecasting, observability. End-of-month projection accuracy within 10% is the target.

### "Design cost accounting for a multi-tenant LLM SaaS."

**Lean on:** Cost at Scale + Multi-Tenancy (from Folder 1).

**Structure:**
- Cost event schema (every LLM call emits full context)
- Per-tenant real-time spend tracking (Redis + persistent DB)
- Budget enforcement in BFF pre-flight
- Reconciliation to provider invoices monthly
- Cost dashboards per tenant, per feature, per user

### "What's cost per successful task?"

**Lean on:** Unit Economics.

**Formula:** (variable cost / success rate) + escalation cost × (1 - success rate) + fixed cost per task.

**Why it matters:** it's the number that determines business viability. Not cost per API call.

### "How do provider prompt caches work?"

**Lean on:** Cache Hierarchy.

**Structure:**
- Anthropic: 90% discount on cached prefix, 5-min TTL, explicit cache_control markers
- OpenAI: 50% discount on cached prefix, automatic, 5-10 min TTL
- Gemini: 75% discount, explicit API

**Design implication:** system prompt + few-shot first (stable prefix), user query last (variable).

### "How would you route between models?"

**Lean on:** Model Routing.

**Four patterns:** rule-based, classifier-based, cascade, learned. Cascade wins when cheap-model success rate > cheap/expensive cost ratio. Always requires golden eval set for quality monitoring.

## The Framework To Remember

Every cost engineering question maps to one of:

1. **Unit economics** — cost per success measurement
2. **Cache hierarchy** — three layers
3. **Model routing** — small-first, escalate when needed
4. **Provider economics** — API vs self-host vs hybrid
5. **Cost at scale** — budgets, anomalies, forecasting, observability

Show that you know these five and interviewers know you've thought about production cost.
