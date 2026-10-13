# 🧭 Cost Engineering Decision Framework

Answer these in order for any LLM feature.

## Step 1: Define The Unit Economic

**Question:** what is one "success" for this feature?

- Assistant: a satisfying answer
- Copilot: an accepted suggestion
- Agent-first: a completed task
- Workflow-first: a correctly classified output

**Then compute:** cost per success = (variable cost / success rate) + escalation cost × (1 - success rate) + fixed per task.

**Decision output:** know your unit economic before writing code.

## Step 2: Choose Cache Strategy

**Question:** which caches make sense for this feature?

| If... | Then... |
|---|---|
| Structured queries with limited variance | Exact response cache |
| Free-form queries in a narrow domain | Semantic cache (threshold 0.93-0.97) |
| Any product with stable system prompt | Provider prompt cache (structure prefix first) |
| Long conversations | Session KV cache or Anthropic prompt cache |
| Sensitive/personalized data | Skip semantic cache; scope exact to user |

**Decision output:** cache stack for this feature.

## Step 3: Choose Model Routing Strategy

**Question:** does this feature benefit from routing?

| If... | Then... |
|---|---|
| Uniform query complexity | Single model, no routing needed |
| Mixed complexity, high volume | Classifier or cascade router |
| Simple queries dominate | Cascade with cheap default |
| Very high scale (10M+/day) | Learned router with batch decisions |
| Cost-critical, quality-flexible | Cascade with tight validation |

**Decision output:** routing pattern + models involved.

## Step 4: Choose Provider Strategy

**Question:** should we self-host, use provider APIs, or hybrid?

All three must be true for self-hosting:
- Sustained load > 15-30M tok/hr equivalent
- Provider APIs don't meet requirements (latency, custom model, data residency)
- Ops team exists or is being built

Otherwise: **provider API.**

For serious production: **hybrid** — provider API primary, self-host for specialized sustained workloads.

**Decision output:** provider strategy + fallback logic.

## Step 5: Choose Governance Model

**Question:** how do you catch cost surprises before finance does?

Minimum viable:
- Per-tenant budgets with soft/hard/kill tiers
- Anomaly detection every 60 seconds
- End-of-month projection with alerts
- Cost observability events on every LLM call

**Decision output:** the governance layer that prevents surprises.

## The Combined Decision — Worked Example

**Customer support copilot for B2B SaaS:**

- **Unit economic:** cost per resolved ticket = $2.04, target < $2.50 (positive margin)
- **Cache:** exact response cache (10% hit), semantic cache 0.95 threshold (25% hit), Anthropic prompt cache with restructured prompts (60% savings on 65% of calls)
- **Routing:** classifier router — Haiku for classification and simple lookups, Sonnet for resolution recommendations
- **Provider:** Anthropic primary, OpenAI fallback, no self-hosting yet at current volume
- **Governance:** per-tenant budget ($500 Starter / $5000 Pro / negotiated Enterprise), runaway detection at 10× baseline, monthly reconciliation, quarterly contract review

Total cost impact vs naive baseline: **~75% reduction.** That's the difference between a project that ships and one that gets killed.
