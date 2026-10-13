# 📈 Cost at Scale — Governance, Budgets, and the Anomalies That Kill You

> *"Our LLM bill just went from $30K to $180K. Nobody knows why."*
>
> — a CFO, in a conversation nobody wants to have

Every unit-economic model works until scale exposes it.

Costs that were 5% of your budget at 10K users become 30% at 10M users. Runaway agents burn a month's inference budget in an hour. A silent prompt regression takes cache hit rate from 60% to 5% and nobody notices until the invoice arrives.

This section is the discipline that catches these problems *before* they land in a finance meeting.

---

## The Four Governance Layers

Every serious production LLM app needs:

1. **Per-tenant budgets** — hard caps and soft alerts
2. **Runaway detection** — automated anomaly response
3. **Forecasting** — predict spend before it happens
4. **Cost observability** — the metrics that make cost debuggable

Skip any and you'll learn the hard way.

---

## Layer 1: Per-Tenant Budgets

**The bare minimum.** Every tenant has a defined budget. Usage above it either degrades, throttles, or blocks.

### The Budget Model

**Three levels:**

- **Soft budget:** alert triggered at 80% of tier limit. Notify tenant admin. No automatic action.
- **Hard budget:** at 100%, degrade to a smaller model. Session continues, quality drops.
- **Kill switch:** at 150% (or a per-tenant configurable overshoot), block further LLM calls entirely.

### Enforcing budgets in the BFF

```python
def check_budget(tenant_id, estimated_cost):
    budget = get_budget(tenant_id)
    current_spend = get_current_spend(tenant_id)  # this month
    
    projected = current_spend + estimated_cost
    
    if projected > budget.kill_switch:
        raise BudgetExceededError(tenant_id)
    if projected > budget.hard_cap:
        return "degrade"  # route to smaller model
    if projected > budget.soft_cap:
        emit_alert(tenant_id, "80% budget consumed")
    return "ok"
```

**Where the numbers live:**
- Real-time spend accounting in Redis (updated per-request)
- Reconciliation to persistent DB every N minutes (source of truth)
- Budgets pinned in tenant config

### Common failure modes

**"We track cost after the response."**
Cost accounting is post-hoc. A runaway agent costs 100× normal before you notice. Fix: estimate cost pre-flight, check budget, then execute.

**"Budget resets on the wrong day."**
Tenant's calendar month vs your billing month. Different timezones. Renewals mid-month. Get this wrong and disputes happen.

**"No graceful degradation."**
Budget hit → all requests fail. Tenant sees errors. Support ticket. Bad experience. Design the "budget exceeded" state as a first-class product feature: warning banner, fallback to smaller model, or read-only mode.

---

## Layer 2: Runaway Detection

**A budget catches sustained overspend. Runaway detection catches acute anomalies.**

### The Signals

- **Cost per query anomaly.** Individual queries costing 10× normal. Usually a max_tokens misconfiguration or infinite tool loop.
- **Query rate anomaly.** Sudden spike in requests from a single user or tenant. Could be legitimate; could be a bot.
- **Success rate collapse.** Cost stays flat but escalation rate spikes. Cost per successful task explodes.
- **Cache hit rate collapse.** Cache hit rate drops 30%+ vs baseline. Cost per successful task doubles.
- **Model routing shift.** Router escalating 80% of traffic to expensive model when normal is 20%.

### The Response

Automated. Fast. Reversible.

```python
# Every 60 seconds
def anomaly_check():
    for tenant in active_tenants:
        current = get_metrics(tenant, window="15min")
        baseline = get_baseline(tenant, days=30)
        
        if current.cost_per_query > 5 * baseline.cost_per_query_p99:
            emit_alert("high_cost_per_query", tenant)
            
        if current.query_rate > 10 * baseline.query_rate_p95:
            emit_alert("query_spike", tenant)
            if current.query_rate > 50 * baseline.query_rate_p95:
                apply_rate_limit(tenant, factor=0.1)  # throttle to 10% normal
                emit_alert("rate_limit_applied", tenant)
```

### The Playbook

Every alert needs a runbook. Suggested categories:

| Signal | Immediate action | Investigation |
|---|---|---|
| High cost per query | Log recent requests; page if sustained | Check for max_tokens misconfiguration, infinite loop |
| Query rate spike | Rate limit (soft); page on-call | Bot? Legitimate scaling event? |
| Success rate collapse | Alert product team | Prompt regression? Data quality issue? Model change? |
| Cache hit collapse | Alert engineering | Prompt update invalidated cache? |
| Router escalation spike | Alert engineering | Router misconfiguration? Model quality drop? |

---

## Layer 3: Forecasting

**Predicting cost before it happens.** Two horizons.

### Short-term: end-of-month projection

Given current burn rate + trend, project end-of-month cost.

```python
def project_month_end(tenant_id):
    days_elapsed = day_of_month()
    spend_so_far = get_spend_this_month(tenant_id)
    daily_rate = spend_so_far / days_elapsed
    trend_multiplier = compute_trend(tenant_id, last_7_days)  # 1.0 = flat, 1.2 = growing
    days_remaining = days_in_month() - days_elapsed
    projected = spend_so_far + (daily_rate * trend_multiplier * days_remaining)
    return projected
```

**Alerts:**
- Projected > 90% of budget → notify tenant admin
- Projected > 120% of budget → notify engineering (something abnormal)

### Long-term: capacity planning

For your own infrastructure planning, project 3-6 months out.

**Inputs:**
- Historical growth rate (users, tasks per user, tokens per task)
- Product roadmap (new features that increase usage)
- Pricing changes announced by providers
- Seasonal patterns (B2B slows in December, spikes in Q1)

**Outputs:**
- Expected provider spend by month
- Utilization trajectory for self-hosted capacity
- When to renegotiate provider contracts (usually at ~30% next-tier volume)

**Warning:** projections are wrong. Provide P50, P90, P99 estimates. Communicate uncertainty.

---

## Layer 4: Cost Observability

**The metrics that make cost debuggable.**

### The Cost Data Model

Every LLM call emits an event with:

```json
{
  "timestamp": "2026-08-11T14:32:00Z",
  "tenant_id": "acme_corp",
  "user_id": "user_alice",
  "feature": "customer_support_copilot",
  "prompt_version": "v3",
  "model": "gpt-4o",
  "input_tokens": 3200,
  "output_tokens": 450,
  "cache_hit": "partial",
  "cache_savings_usd": 0.008,
  "raw_cost_usd": 0.0125,
  "actual_cost_usd": 0.0045,
  "success": true,
  "task_id": "task_xyz",
  "attempt_number": 1
}
```

**Why every field matters:**

- **tenant, user** → per-tenant/user cost views
- **feature** → which product features are expensive
- **prompt_version** → detect regressions after prompt updates
- **model** → routing distribution
- **cache_hit** → cache health monitoring
- **actual vs raw cost** → track savings
- **success, task, attempt** → cost per successful task calculation

### The Dashboards

**Executive dashboard (weekly):**
- Total monthly spend (actual vs projected)
- Cost per active user (trending)
- Cost per successful task by feature
- Top 10 tenants by spend

**Engineering dashboard (real-time):**
- Cost per query (P50, P95, P99, over time)
- Cache hit rates (each of 3 layers)
- Model routing distribution
- Anomaly alerts

**Product dashboard (weekly):**
- Cost per successful task by feature
- Marginal cost of new features
- User segments by profitability

### The Alerts

**Critical (page on-call):**
- Any tenant hit kill-switch
- Runaway cost > 10× baseline for 15 min
- Provider cost > 3× projected

**High (notify on-call channel):**
- Any tenant projected > 120% budget
- Cache hit rate drop > 30%
- Router escalation > 3× baseline

**Info (log):**
- Any tenant approaching budget
- Weekly cost report
- Provider price changes

---

## The Governance Framework

**Weekly rhythm:**
- Cost engineering standup — review dashboards, flag anomalies
- Feature-level cost review — which features are getting more/less expensive
- Tenant escalations — anyone approaching budget

**Monthly rhythm:**
- Full cost audit — reconcile provider bills to internal tracking
- Unit economics review — cost per successful task trending
- Roadmap review — cost implications of new features
- Contract review — is next-tier volume approaching negotiation threshold?

**Quarterly rhythm:**
- Provider strategy review — pricing, capacity, alternatives
- Self-host decision review — has anything changed the calculus?
- Capacity planning update

**Annually:**
- Full cost model recalibration
- Provider negotiations
- Board-level cost review

---

## What This Looks Like in Real Products

### Anti-example: the runaway agent (2025)

- Deployed autonomous research agent for enterprise sales team
- No per-user budget enforcement
- Sales rep tests it on a Friday afternoon: "give me every fact about every S&P 500 company"
- Agent runs 40 hours, 6M queries, before someone notices
- Bill: **$67,000 in one weekend**
- Post-mortem: needed pre-flight cost estimation + per-user daily kill switch + anomaly detection at 10× baseline

### Working example: multi-tenant SaaS (2026)

- 400 tenants, average $200/month LLM cost each
- Per-tenant budgets in three tiers: Starter ($50), Pro ($500), Enterprise (negotiated)
- Anomaly detection every 60 seconds
- Monthly cost reconciliation against provider invoices — variance < 2%
- End-of-month projection accuracy: within 10%
- **Result:** predictable margins, zero surprise invoices, no financial disputes

### Working example: consumer chat (2026)

- 2M free users, 100K paid users
- Per-user daily token budget (free tier)
- Runaway detection at query-rate + cost-per-query
- Automated rate limiting on abuse patterns
- Free-user cost per DAU: $0.008
- Paid-user LTV/CAC ratio: 4.2
- **Result:** sustainable free tier, healthy paid unit economics

---

## Files in This Folder

| File | Concept |
|---|---|
| [`per_tenant_budgets.py`](per_tenant_budgets.py) | Budget model with soft/hard/kill-switch tiers |
| [`runaway_detection.py`](runaway_detection.py) | Anomaly signals and automated response |
| [`cost_forecasting.py`](cost_forecasting.py) | End-of-month projection + long-term capacity planning |
| [`cost_observability.py`](cost_observability.py) | Event schema, dashboards, alert model |
| [`billing_reconciliation.py`](billing_reconciliation.py) | Matching internal tracking to provider invoices |
| [`governance_rhythm.py`](governance_rhythm.py) | Weekly/monthly/quarterly cost governance workflow |

---

## The Staff Interview Question

*"How do you keep your LLM costs from surprising your CFO?"*

**The wrong answer:** "We track spend in the provider dashboard."

**The right answer:**
"Four layers. Per-tenant budgets — soft alerts at 80%, hard degradation at 100%, kill switch at 150% — enforced in the BFF pre-flight, not post-hoc. Runaway detection — automated checks every minute for cost-per-query spikes, query rate anomalies, success rate collapse, cache hit rate collapse, and router escalation shifts, with automated throttling and paging. Forecasting — end-of-month projection updated daily with trend adjustment; alerts when projected > 120% budget. Cost observability — every LLM call emits an event with tenant, user, feature, prompt version, model, tokens, cache status, cost, and success outcome, feeding dashboards for executives, engineers, and product. Governance rhythm — weekly cost standup, monthly full audit with provider reconciliation, quarterly capacity planning, annual contract renegotiation. Result: end-of-month projection accuracy within 10%, zero surprise invoices, and every finance conversation supported by data. The CFO doesn't get surprised because they've already seen the projection for two weeks."

---

*Previous: [← Provider Economics](../04_provider_economics/README.md) · Return to [folder README](../README.md)*
