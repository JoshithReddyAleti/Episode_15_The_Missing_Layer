# 🛤️ Model Routing — The Highest-ROI Cost Pattern

> *"We use GPT-4o for everything."*
>
> *"Even the two-word classification tasks?"*
>
> *"Well, yeah, quality matters."*
>
> *"That's a $30K/month choice you didn't have to make."*

Model routing is choosing the smallest capable model for each request. Done well, it cuts inference cost 40-70% with minimal quality loss. Done badly, it collapses your quality gates and creates user complaints you can't debug.

This section is the routing patterns that work in production.

---

## The Core Idea

**Not every request needs your best model.**

**Simple requests → cheap fast model. Complex requests → expensive capable model.**

That sentence contains the whole discipline. The rest is *how you decide which is which*.

---

## The Cost Delta Is Massive

| Task type | Cheap model | Expensive model | Cost ratio |
|---|---|---|---|
| GPT-4o-mini vs GPT-4o | $0.15/M in | $2.50/M in | **17×** |
| Claude Haiku vs Sonnet | $0.25/M in | $3.00/M in | **12×** |
| Claude Haiku vs Opus | $0.25/M in | $15.00/M in | **60×** |
| Gemini Flash vs Pro | $0.10/M in | $1.25/M in | **12×** |
| Standard vs reasoning | $2.50/M in | $15/M in | **6×** (input; more on output) |

**If 80% of your traffic can be handled by the cheap model at acceptable quality, routing gives you a 12-17× cost reduction on that 80%.**

At 1M queries/month, this is often the difference between $30K and $8K.

---

## The Router Pattern

Three components:

**1. Classifier.** Decides which model to send this request to. Fast, cheap.

**2. Executor.** Sends the request to the chosen model, gets the response.

**3. Escalator.** If the cheap model's response is unsatisfactory, retries with the expensive model.

```
                       ┌──────────────┐
Request  ─────────────>│   Classifier  │
                       └──────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
               [ Cheap model ]    [ Expensive model ]
                    │                   │
                    ▼                   ▼
              ┌─────────────┐          ┌─────────────┐
              │ Confidence  │─No──────>│ Return       │
              │ check       │          │ response     │
              └─────────────┘          └─────────────┘
                    │Yes
                    ▼
              [ Return response ]
```

---

## Router Implementation Options

### Option 1: Rule-Based Router

Deterministic rules based on query features.

```python
def route(request):
    tokens = estimate_tokens(request.messages)
    if tokens < 500 and not request.tools_enabled:
        return "gpt-4o-mini"
    if request.task_type == "classification":
        return "gpt-4o-mini"
    if request.task_type == "reasoning":
        return "o1"
    return "gpt-4o"  # default
```

**Pros:** transparent, cheap, easy to debug.
**Cons:** rigid, hard to maintain as complexity grows.

**When it wins:** simple products, few distinct request types.

### Option 2: Classifier Model Router

A small LLM (or fine-tuned classifier) that decides the route.

```python
def route(request):
    prompt = f"Classify this query: {request.user_message}\n\nCategories: [simple_qa, complex_reasoning, multi_step_task]\nAnswer:"
    label = classifier_llm.complete(prompt, model="gpt-4o-mini")  # cheap classifier
    routing_map = {
        "simple_qa": "gpt-4o-mini",
        "complex_reasoning": "o1",
        "multi_step_task": "gpt-4o",
    }
    return routing_map[label]
```

**Pros:** adapts to nuanced queries, easier to tune.
**Cons:** adds a classifier call (10-20ms + a few cents per 1000), less transparent.

**When it wins:** diverse query types, need to handle edge cases.

### Option 3: Cascade Router

Always start with the cheapest model. Only escalate if confidence is low or output fails validation.

```python
def route(request):
    response = cheap_model.complete(request)
    if is_confident(response) and passes_validation(response):
        return response
    return expensive_model.complete(request)  # escalate
```

**Pros:** maximizes cheap-model usage. Naturally adapts.
**Cons:** escalations pay for BOTH calls. Only wins if cheap-model success rate is high.

**Break-even math:**
```
cascade wins if: p_cheap_success × cost_cheap + (1 - p_cheap_success) × (cost_cheap + cost_expensive)
              <  cost_expensive
Simplify:
              cost_cheap × 1 + (1 - p_cheap_success) × cost_expensive < cost_expensive
              cost_cheap < p_cheap_success × cost_expensive
              cost_cheap / cost_expensive < p_cheap_success
```

If cheap costs 10% of expensive, cascade wins when cheap-model success rate > 10%. Nearly always true.

### Option 4: Learned Router

Fine-tune a small model on (query → correct route) labeled data.

**Pros:** best accuracy, adapts to your specific traffic patterns.
**Cons:** requires labeled data, training pipeline, deployment complexity.

**When it wins:** high-scale production, where routing accuracy compounds.

---

## The Confidence / Validation Signal

For cascade and hybrid routers, you need to know when to escalate. Three approaches:

### Signal 1: Model Self-Assessment
Ask the model: *"How confident are you in this answer? (0-100)"*
- **Cheap:** works with any model
- **Unreliable:** models over-report confidence, especially small ones
- **Better:** ask for a structured self-check ("does this address the question?" — yes/no)

### Signal 2: Log Probability
Use the model's log probabilities as a confidence proxy.
- Available from OpenAI Completions API (`logprobs=true`)
- Not exposed by Anthropic; workaround: sample multiple times and check consistency

### Signal 3: Output Validation
Task-specific validators.
- Structured output → schema validation (Pydantic, JSON schema)
- Code generation → syntax check + type check
- Math → symbolic verifier
- Retrieval-grounded → check citations exist and are accurate

**Best in practice:** combine signal 2 (log prob) + signal 3 (task-specific validator). Fall back to signal 1 (self-assessment) only when others unavailable.

---

## The Quality/Cost Frontier

Every routing choice is a point on the quality/cost frontier.

```
                Quality
                   ▲
                   │
       expensive   ●───── expected: quality is high
       model      │
                   │
                   │
       cascade    ●─────────── near-expensive quality, ~30% of the cost
                   │
                   │
       classifier ●─────────── ~90% of expensive quality, ~40% of the cost
                   │
                   │
       cheap only ●─────────── low quality on complex queries, ~10% of the cost
                   │
                   └──────────────────────────► Cost
```

**Your goal:** find the point that maximizes quality at your cost budget, or minimizes cost at your quality target.

**Not a single point:** it's often best to have different routing policies per feature.

---

## Evaluating a Router

Router changes affect quality. You need to measure both cost AND quality on the same eval set.

**Metrics:**
- **Cost per request** (average, P95, P99)
- **Quality score** (LLM-judge, human eval, task-specific)
- **Model mix distribution** (% traffic to each model)
- **Escalation rate** (for cascade routers)
- **Latency** (P50, P95, P99)

**Never A/B a router without a golden eval set.** You cannot afford silent quality degradation.

**Suggested eval set composition:**
- 40% "simple" queries the cheap model should handle
- 40% "medium" queries where routing matters most
- 20% "complex" queries the expensive model is needed for

Track quality on each bucket separately.

---

## Real Routing Wins

### Fiserv-style RAG (2024):
- Original: GPT-4 for all queries → $32K/month
- After routing (classifier + cascade): 78% traffic to gpt-3.5, 22% to GPT-4 → $9K/month
- Quality delta: -1.5% on golden set (acceptable)
- **Savings: 72%, ~$23K/month**

### Support triage system (2025):
- Original: Claude Sonnet for all → $45K/month
- After routing: Haiku for classification + summarization, Sonnet for resolution suggestions → $12K/month
- Quality delta: neutral (Sonnet was overkill for classification)
- **Savings: 73%, ~$33K/month**

### Coding assistant (2025):
- Original: GPT-4 for all completions → $60K/month
- After routing: gpt-3.5 for simple completions (60% of traffic), GPT-4 for complex → $28K/month
- Escalation rate: 12% (higher than expected)
- Quality delta: +2% (routing improved response speed → user perception)
- **Savings: 53%, ~$32K/month**

---

## Router Anti-Patterns

**"Route everything to the cheap model, escalate on error."**
Errors from the cheap model are silent quality failures, not exceptions. Cascade requires actual quality signal, not just "did it crash."

**"Route by input length."**
Sometimes correct, often not. A 2-token input can be complex ("solve integral from 0 to π"). A 2000-token input can be trivial ("summarize this article").

**"Route by user tier."**
Enterprise users get GPT-4o, free users get mini. Reasonable business logic, but often the free tier feature was the one differentiating your product. Watch for quality complaints.

**"Set-and-forget routing."**
Traffic patterns change. Models get better. Prices change. Routing config needs quarterly review at minimum.

**"Route without measurement."**
Ship a router. Assume it's saving money and preserving quality. Neither is guaranteed. Instrument or don't ship.

---

## Router at Scale

**At 10M+ requests/month:**

- **Classifier latency matters.** A 200ms classifier call in front of a 1s LLM call is 20% overhead. Use logistic-regression or small distilled classifiers, not another LLM call.
- **Batch routing decisions.** Don't call classifier per-request; batch 10-100 requests, classify once.
- **Cache routing decisions.** Similar queries → same route. Route by semantic cluster, not per-request.
- **Multi-region routing.** Some models available only in some regions. Route considers latency + availability + cost.

---

## Files in This Folder

| File | Concept |
|---|---|
| [`rule_based_router.py`](rule_based_router.py) | Deterministic routing with feature-based rules |
| [`classifier_model_router.py`](classifier_model_router.py) | Small-LLM classifier for routing decisions |
| [`cascade_router.py`](cascade_router.py) | Cascade pattern with confidence-based escalation |
| [`router_evaluation.py`](router_evaluation.py) | Measuring quality + cost together on eval sets |
| [`confidence_signals.py`](confidence_signals.py) | Log probs, self-assessment, validators |
| [`router_at_scale.py`](router_at_scale.py) | Batching, caching, multi-region patterns |

---

## The Staff Interview Question

*"Our LLM bill is too high. Walk me through how you'd bring it down."*

**The wrong answer:** "Use a cheaper model."

**The right answer:**
"Three moves in order. First — measure current cost per successful task, decomposed by feature and by user segment. That tells us where the dollars go and which features to target. Second — cache stack. Exact response cache in the BFF, semantic cache with tuned threshold, provider prompt cache with restructured prompts. Expect 50-60% reduction stacked. Third — model routing. Classifier-based router with cascade escalation. For each feature, define the golden eval set, measure current model performance, identify the smallest capable model per query type, and set up cascade with confidence-based escalation to the expensive model. Expect another 40-60% reduction on remaining traffic. Combined: 70-80% reduction is realistic without quality loss, if we're currently unoptimized. Measurement gates every step — quality on golden set, cost per successful task, escalation rate. If quality drops, we back off. Cost engineering is not a one-shot project — it's a continuous discipline, so instrument for ongoing optimization."

---

*Previous: [← Cache Hierarchy](../02_cache_hierarchy/README.md) · Return to [folder README](../README.md) · Next: [Provider Economics →](../04_provider_economics/README.md)*
