# 📊 Cost Model Template

Drop this into your design doc for any new LLM feature.

---

## Feature: [Name]

**Product shape:** Assistant / Copilot / Agent-first / Workflow-first
**Success definition:** [what does "one success" mean for this feature?]

---

## Unit Cost Model

### Variable cost per task attempt

| Component | Estimate | Notes |
|---|---|---|
| LLM calls per attempt | | |
| Average tokens per call (input) | | |
| Average tokens per call (output) | | |
| Model | | e.g., GPT-4o mini for classification, GPT-4o for reasoning |
| Base cost per call | $ | Input + output pricing |
| Cache savings (%) | | 3-layer cache hierarchy |
| Effective cost per call | $ | After caching |
| Retrieval calls | | RAG lookups |
| Retrieval cost each | $ | Embedding + vector query |
| Tool call costs | $ | External API costs from tool use |
| Guardrail costs | $ | Any additional LLM calls for safety |
| **Total variable cost per attempt** | $ | |

### Task-level economics

| Component | Estimate | Notes |
|---|---|---|
| Success rate | % | Realistic estimate after golden set eval |
| Fixed cost per task | $ | Storage, audit, notification |
| Escalation cost per failure | $ | Human agent, retry, etc. |
| **Cost per successful task** | $ | Full formula |

### Formula
```
Cost_per_success = variable_per_attempt / success_rate
                 + escalation_cost × (1 - success_rate)
                 + fixed_cost_per_task
```

---

## Business Model

| Component | Estimate |
|---|---|
| Revenue per successful task | $ |
| Contribution margin per task | $ |
| Margin % | % |

**Verdict:** Sustainable / Marginal / Unsustainable

---

## Lever Analysis

Which single variable would most improve cost per success? Rank top 3:

1. **[Lever name]** — expected impact: X% reduction in cost per success
2. **[Lever name]** — expected impact: X% reduction
3. **[Lever name]** — expected impact: X% reduction

---

## Scale Projections

| Volume | Cost per success | Monthly cost |
|---|---|---|
| 10K tasks/month | $ | $ |
| 100K tasks/month | $ | $ |
| 1M tasks/month | $ | $ |
| 10M tasks/month | $ | $ |

**Crossover to self-hosting:** [volume threshold, if applicable]

---

## Governance

- **Per-tenant budget tiers:** [Starter / Pro / Enterprise limits]
- **Runaway detection thresholds:** [cost per query, query rate, escalation rate]
- **End-of-month projection alerts:** [at 90% budget, at 120% projected]
- **Reconciliation cadence:** [monthly against provider invoices]

---

## Sign-off

- [ ] Product Manager reviewed unit economics
- [ ] Engineering Lead reviewed cache and routing strategy
- [ ] Finance reviewed provider strategy and projections
- [ ] Ops reviewed governance and observability plan
