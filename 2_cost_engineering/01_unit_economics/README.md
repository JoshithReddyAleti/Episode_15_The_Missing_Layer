# 💵 Unit Economics — The Only Cost Metric That Matters

> *"What does one customer cost you?"*
>
> *"Uh... we spent $12K on OpenAI last month?"*
>
> *"That's not what I asked."*

The number "$12K on OpenAI" tells you nothing about whether your product is viable.

**Cost per successful task tells you whether the business works.** This section is how to compute it, how to interpret it, and how to move it.

---

## The Definition

**Cost per successful task** = total variable cost incurred to produce one successful business outcome.

Not one API call. Not one query. Not one conversation. One *successful outcome*.

Because that's the unit users pay for. That's the unit that must be profitable.

---

## The Formula

For any LLM feature:

```
Cost_per_success = (C_llm × N_calls + C_retrieval × N_retrievals + C_other)
                   × (1 / Success_rate)
                   + C_escalation × (1 - Success_rate)
                   + C_fixed_per_task
```

Where:
- `C_llm` = average cost per LLM call (post-caching, post-routing)
- `N_calls` = average LLM calls per task attempt (including retries)
- `C_retrieval` = cost per RAG retrieval (embedding + vector search)
- `N_retrievals` = retrievals per task attempt
- `C_other` = other variable costs per attempt (guardrails, tool calls, etc.)
- `Success_rate` = fraction of attempts that complete successfully
- `C_escalation` = cost of the fallback when the AI fails (human agent, retry, etc.)
- `C_fixed_per_task` = fixed cost per task regardless of attempts (logging, audit, notifications)

**Every term in this formula is a lever you can pull.**

---

## The Worked Example — Customer Support Copilot

**Given:**

- Provider: GPT-4o
- Input pricing: $2.50/M tokens, output: $10/M
- Cache hit rate on system prompt: 50%
- Per task: 4 LLM calls (initial, 2 tool calls with follow-up, final)
- Average tokens per call: 2500 input, 400 output
- Retrieval per attempt: 2 (initial context + refinement)
- Retrieval cost: $0.0003 each (embedding + Pinecone query)
- Success rate: 75% (25% escalate to human)
- Human agent cost per escalation: $8
- Fixed per task: $0.002 (audit, notifications, session storage)

**Compute:**

```
C_llm per call (with 50% cache):
  Input: 2500 × 0.5 (cached at ~50% discount for OpenAI) = 1250 effective × $2.50/M = $0.00313
  Output: 400 × $10/M = $0.00400
  Total per call: $0.00713

C_llm × N_calls = $0.00713 × 4 = $0.02852

C_retrieval × N_retrievals = $0.0003 × 2 = $0.0006

Variable cost per attempt = $0.02852 + $0.0006 = $0.02912

Cost per success = $0.02912 / 0.75 = $0.03883
                 + $8 × 0.25 (human escalation cost)
                 + $0.002
                 = $0.03883 + $2.00 + $0.002
                 = $2.04
```

**Cost per successfully resolved ticket = $2.04**

**Now the business question:**
- Revenue per resolved ticket (savings vs full human): $2.50
- **Contribution margin per success: $0.46 (18%)**

That's marginal. Not comfortable. Small changes will make or break it.

---

## Lever Analysis — What Actually Moves The Number

Same example, ask: "which changes move cost per success the most?"

**Lever 1: Improve success rate from 75% → 85%.**

```
Cost = $0.02912 / 0.85 + $8 × 0.15 + $0.002 = $0.0343 + $1.20 + $0.002 = $1.24
```

Savings: **$0.80 per success (39% reduction).** Massive.

**Lever 2: Reduce LLM calls per attempt from 4 → 3.**

```
Variable = $0.00713 × 3 + $0.0006 = $0.02199
Cost = $0.02199 / 0.75 + $8 × 0.25 + $0.002 = $0.02932 + $2.00 + $0.002 = $2.03
```

Savings: **$0.01. Negligible.**

**Lever 3: Route 60% of traffic to GPT-4o-mini instead of GPT-4o.**

```
Mini cost per call: $0.15/M × 1250 + $0.60/M × 400 = $0.000188 + $0.00024 = $0.000428
Blended (60% mini, 40% full): 0.6 × $0.000428 + 0.4 × $0.00713 = $0.003109
Variable = $0.003109 × 4 + $0.0006 = $0.01304
Cost = $0.01304 / 0.75 + $8 × 0.25 + $0.002 = $0.01739 + $2.00 + $0.002 = $2.02
```

Savings: **$0.02.** Small — because escalation dominates.

**Lever 4: Reduce escalation cost from $8 → $4 (better triage).**

```
Cost = $0.02912 / 0.75 + $4 × 0.25 + $0.002 = $0.03883 + $1.00 + $0.002 = $1.04
```

Savings: **$1.00 per success (49% reduction).** Enormous.

**The lesson:** in this product, the LLM cost is the tip of the iceberg. Success rate and escalation cost dominate. Optimizing prompt caching while your escalation cost is $8 is fiddling while Rome burns.

**Cost engineering is knowing which lever matters.** Not every lever moves the number.

---

## The Cost Layers Revisited (per successful task)

For the copilot above, decompose the $2.04:

| Layer | $ per success | % of total |
|---|---|---|
| Inference (LLM calls) | $0.038 | 1.9% |
| Retrieval | $0.001 | 0.05% |
| Storage / audit / fixed | $0.002 | 0.1% |
| Escalation (human fallback) | $2.00 | 98% |

**98% of your cost is human agents catching what the AI missed.** Any prompt engineering below that is noise.

**The right investments:**
1. Raise success rate (better prompts, better retrieval, better tools)
2. Reduce escalation cost (better handoff, smaller escalations)
3. Then, and only then, optimize the LLM cost

Teams that skip 1 and 2 to optimize 3 are running the wrong race.

---

## Cost Per Task At Different Product Shapes

The formula is the same. The dominant terms change.

**Assistant (consumer chat):**
```
Success = "user got a useful answer"
Dominant terms: N_calls × C_llm (no escalation, low retrieval)
Typical cost: $0.001 - $0.05
Optimization focus: cache hit rate, model routing
```

**Copilot (inline suggestions):**
```
Success = "user accepted the suggestion"
Dominant terms: N_calls × C_llm × (1/acceptance_rate)
Typical cost: $0.005 - $0.10
Optimization focus: acceptance rate, prompt caching, small-model default
```

**Agent-first (autonomous task):**
```
Success = "task completed correctly"
Dominant terms: N_tool_calls × (C_llm + C_tool) × attempts_per_success
Typical cost: $0.10 - $10.00
Optimization focus: reduce tool calls, higher success rate on first attempt
```

**Workflow-first (batch pipeline):**
```
Success = "correctly classified output"
Dominant terms: N_documents × C_llm (small, fixed per doc)
Typical cost: $0.0001 - $0.001
Optimization focus: routing to smallest capable model, batch inference
```

---

## The CAC / LTV Question

Once you know cost per successful task, you can compute:

**Cost per Active User (CPU):**
```
CPU = tasks_per_user_per_month × cost_per_success × months_active
```

**Contribution Margin per User:**
```
CM = revenue_per_user - CPU
```

**LTV / CAC ratio for the business:**
```
LTV = CM × expected_retention_months
CAC = customer acquisition cost
Healthy ratio: LTV/CAC > 3
```

**If you can't compute these numbers, you cannot answer:**
- "How much can we spend on marketing?"
- "Can we afford to give the product away free?"
- "Which customer segments are profitable?"
- "What price should we charge?"

Every product person needs cost-per-success. Not just engineers.

---

## Marginal Cost vs Allocated Cost

**Marginal cost:** the additional cost of serving one more task. Variable, direct.

**Allocated cost:** marginal + share of fixed costs (infrastructure, headcount, tooling).

For unit economic decisions (should we pursue this customer segment?), **marginal cost is what matters.**

For financial reporting (what's our gross margin?), **allocated cost is what matters.**

Most engineers only think about marginal. Most CFOs only think about allocated. Neither is wrong; both are needed.

**The trap:** a feature can be marginally profitable but destroy total gross margin if it consumes disproportionate fixed capacity. Watch for this in high-touch enterprise deployments.

---

## Real Numbers From Real Deployments

**Fiserv-style RAG knowledge base (production, 2024-2025):**
- Cost per query: ~$0.002 (with heavy prompt caching)
- Success rate: 92%
- Escalation cost: $0.50 (routing to specific team lookup)
- **Cost per success: $0.045**
- Volume: 400K queries/month
- Total: **~$18K/month**

**Boehringer-style vision QA (production, 2025-2026):**
- Cost per inspection: ~$0.008 (VLM API + edge compute)
- Success rate: 95% (5% flagged for human review)
- Human review cost: $0.60 per flag
- **Cost per successful inspection: $0.038**
- Volume: 1.2M inspections/month
- Total: **~$46K/month**

**Anti-example (project that got killed):**
- Autonomous procurement agent (proposed, 2025)
- Cost per attempt: $12 (many tool calls, GPT-4-class model)
- Success rate: 40% initial testing
- Escalation cost: $80 (human procurement specialist)
- **Cost per success: $12/0.4 + $80×0.6 = $30 + $48 = $78**
- Revenue per successful task: $45
- **Negative contribution margin. Killed at planning.**

Cost engineering *before you build* saves months.

---

## Files in This Folder

| File | Concept |
|---|---|
| [`cost_per_success_formula.py`](cost_per_success_formula.py) | The formula + calculator for common product shapes |
| [`journey_math.py`](journey_math.py) | Decomposing a user journey into LLM-cost events |
| [`marginal_vs_allocated.py`](marginal_vs_allocated.py) | The distinction and when each matters |
| [`lever_analysis.py`](lever_analysis.py) | How to identify which cost lever matters most for your product |
| [`unit_economics_at_scale.py`](unit_economics_at_scale.py) | CAC/LTV and business-side implications |

---

## The Staff Interview Question

*"How much does this feature cost per user?"*

**The wrong answer:** "Uh, we spent $X on LLM last month divided by users..."

**The right answer:**
"Let me decompose. Cost per user per month is: tasks per user per month, times cost per successful task. Cost per successful task decomposes into: variable cost per attempt, divided by success rate, plus escalation cost times (1 minus success rate), plus fixed cost per task. Variable cost per attempt is calls per attempt times per-call cost with routing and caching factored in, plus retrieval cost. For this feature, we've measured tasks per user per month at 12, success rate at 78%, escalation cost at $2.50, per-call cost at $0.008 with 4 calls per attempt. That gives cost per success of $0.596 and cost per user of $7.15/month. Revenue per user is $12/month. Contribution margin is 40%. The dominant lever for this product is success rate — a 10-point improvement drops cost per user by 22%. Optimizing prompt caching further only nets 3%. So our roadmap prioritizes retrieval quality over cache tuning."

That's an architect's answer.

---

*Return to [folder README](../README.md) · Next: [Cache Hierarchy →](../02_cache_hierarchy/README.md)*
