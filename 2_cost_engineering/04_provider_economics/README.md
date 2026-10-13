# 🏭 Provider Economics — Buy vs Build, With Real Numbers

> *"Should we self-host?"*
>
> *"Only if all three conditions are true. Let me show you the math."*

The self-host vs API decision is one of the biggest architectural bets in AI infrastructure. Get it right and you cut inference cost 60-80% at scale. Get it wrong and you burn a quarter re-inventing what OpenAI already runs better than you.

This section is the honest, numbers-first version of that decision.

---

## The Three Ways to Serve Inference

**1. Provider APIs.** OpenAI, Anthropic, Google, Bedrock, Together, Groq. You pay per token; provider handles all infrastructure.

**2. Managed inference platforms.** Modal, Replicate, RunPod, Fireworks. You bring the model; they run the GPUs and handle scaling.

**3. Self-hosted inference.** Your GPUs, your infrastructure, your operations. Maximum control, maximum operational burden.

Most production apps use **1 by default** and consider **3 only at specific scale/capability thresholds.**

---

## Provider API Economics (2026, approximate)

### The Cheap Tier

| Model | Input $/M | Output $/M | Best for |
|---|---|---|---|
| Gemini 2.0 Flash | $0.10 | $0.40 | Cheapest capable model |
| GPT-4o mini | $0.15 | $0.60 | OpenAI ecosystem default |
| Claude Haiku | $0.25 | $1.25 | Anthropic ecosystem default |
| DeepSeek-V3 | $0.14 | $0.28 | Very cheap for standard tasks |
| Llama-3-70B (via Together) | $0.88 | $0.88 | Open source, mid-tier price |

### The Balanced Tier

| Model | Input $/M | Output $/M | Best for |
|---|---|---|---|
| Gemini 2.5 Pro | $1.25 | $5.00 | Long context (2M tokens) |
| GPT-4o | $2.50 | $10.00 | OpenAI balanced choice |
| Claude Sonnet | $3.00 | $15.00 | Strong reasoning + tool use |
| Nova Pro (Bedrock) | $0.80 | $3.20 | AWS ecosystem |

### The Premium Tier

| Model | Input $/M | Output $/M | Best for |
|---|---|---|---|
| Claude Opus | $15.00 | $75.00 | Highest quality |
| o1 | $15.00 | $60.00 | Reasoning-heavy |
| o3 | $15+ | $60+ | Frontier reasoning |

### Discounts You Should Actually Use

**Prompt caching:** already covered in [Cache Hierarchy](../02_cache_hierarchy/README.md). 50-90% off input tokens on cached prefix.

**Batch API:** OpenAI, Anthropic offer 50% discount for batch (24-hour SLA). Perfect for workflow-first apps.

**Enterprise contracts:** at $50K+/month, providers negotiate. Discounts of 20-40% typical; committed spend gets more.

**Regional pricing:** some providers have regional cost differences (Bedrock especially).

---

## Self-Hosting Economics (2026, approximate)

### The Hardware Cost

**AWS H100 80GB:**
- On-demand: ~$4-5/hr
- Reserved 1-year: ~$2-3/hr
- Reserved 3-year: ~$1.50-2/hr
- Spot: ~$1-2/hr (interruptible)

**Alternatives:**
- A100 80GB: ~60% of H100 price for ~60% of throughput
- L40S: cheap but lower throughput; niche use
- Consumer GPUs (via specialty providers): sometimes cheap, sometimes unreliable

### The Throughput

**Approximate output throughput on 2× H100 with vLLM (2026):**

| Model | Aggregate tokens/sec | Concurrent requests |
|---|---|---|
| Llama-3-8B | 25,000-40,000 | 100+ |
| Llama-3-70B | 5,000-8,000 | 30-60 |
| Llama-3-405B (needs 8× H100) | 2,000-4,000 | 15-30 |
| Mistral-Large | 4,000-7,000 | 25-50 |
| DeepSeek-V3 (needs multi-node) | 3,000-5,000 | 20-40 |

**Assumptions:** vLLM or TGI, mixed input/output ratios, no aggressive quantization.

### The Break-Even Math

**Question:** at what throughput does self-hosting beat GPT-4o?

**GPT-4o cost:** $2.50/M input + $10/M output ≈ $6/M blended (typical input:output ratio ~3:1)

**Self-hosted Llama-70B on 2× H100:**
- Hardware: 2 × $3/hr reserved = $6/hr
- Add ops overhead (~40%): ~$8.40/hr all-in
- Sustained throughput: ~6000 output tok/s = 21.6M output tokens/hour
- Cost per M output tokens: $8.40 / 21.6 = **$0.39/M**

**vs GPT-4o output at $10/M — self-hosted is 25× cheaper on output side.**

But: you have to keep GPUs full.

**Break-even utilization:**

If you can only fill 30% of the throughput sustained (7M tok/hour instead of 21.6M):
- Effective cost per M: $8.40 / 7 = $1.20/M — still 8× cheaper than GPT-4o
- But now add opportunity cost of unused capacity + on-call rotation

**Rule of thumb:** at sustained >50% utilization, self-hosting Llama-70B beats GPT-4o comfortably. Below 30%, provider APIs win once you factor in ops.

### The Ops Overhead Nobody Tells You

**What "self-hosting" actually requires:**

- GPU procurement and reservation
- Cluster management (Kubernetes, Ray, or managed platforms)
- Model deployment pipelines (staging, canary, rollback)
- Load balancing and autoscaling
- Monitoring (GPU utilization, throughput, latency, memory)
- On-call rotation (GPUs fail, drivers break, memory leaks)
- Model updates (new weights, quantization tuning)
- Multi-region if you need low latency globally
- Disaster recovery (what happens when a region fails?)

**Realistic overhead cost:**

- 1-2 dedicated infrastructure engineers ($200-400K/year fully loaded)
- 30-40% infrastructure premium over raw GPU cost
- ~6 months to reach production reliability

**Where teams underestimate:** the on-call rotation. Provider APIs are debugged by thousands of engineers at OpenAI/Anthropic. Your rotation is you.

---

## The Decision Framework

**Self-host when ALL of these are true:**

**1. Sustained load justifies it.** > 15-30M tokens/hour equivalent, 24/7.

**2. Provider APIs don't meet your requirements.**
- Latency: you need < 200ms P99 that APIs can't guarantee
- Model customization: you're fine-tuning and want inference control
- Data residency: you can't send data to third-party providers (regulated industries)
- Model choice: the model you need (specific fine-tune, specific quantization) isn't available via API

**3. You have (or can build) the ops team.**
- Not "someone who ran Kubernetes once"
- 1-2 senior infra engineers who own GPU inference in production
- On-call rotation
- Runbooks, observability, incident response

**If any of these three fails: provider APIs are the right call.**

---

## The Hybrid Pattern (Most Common)

Very few serious production systems are pure self-hosted or pure API.

**The typical hybrid:**

- **Primary:** Provider API for the majority of traffic
- **Overflow:** Second provider API for redundancy and rate limit relief
- **Specialized:** Self-hosted for specific workloads
  - Long-context heavy tasks (embedding, summarization)
  - High-volume batch jobs (workflow-first apps)
  - Fine-tuned custom models
  - Regulated data flows

**Why hybrid wins:**
- Reliability: multi-provider immunity to any single outage
- Cost: self-host the workloads that consistently justify it; API the burst/variable load
- Compliance: keep regulated data in-cluster; use API for non-regulated
- Flexibility: swap providers as pricing changes without rewriting apps

---

## Cost Model — Worked Example

**Scenario:** support automation processing 1M tickets/month.

- Average tokens per ticket: 8000 (mostly RAG context)
- Peak QPS: 100
- Sustained QPS: 25

### Option A: Pure GPT-4o via API

```
Volume: 1M tickets × 8K tokens = 8B tokens/month
Cost with caching (55% savings on input): ~$0.020 per ticket
Monthly: $20,000
```

### Option B: Self-Host Llama-3-70B on 2× H100

```
Peak QPS 100 × 400 tok/response = 40K tok/sec peak
Sustained 25 QPS × 400 tok/response = 10K tok/sec
2× H100 can do ~6000 tok/sec sustained — INSUFFICIENT
Need 4× H100 for peak safety: $12/hr × 730 hr = $8,760/month
Add ops overhead (40%): $12,264
```

But the math changes:
- Only 55% utilization on sustained load
- Peak safety adds another 25% capacity buffer
- **Cost: $12,264/month vs $20,000/month — $7.7K savings**

**But:** ops overhead, on-call, 6-month build cost, and Llama-70B quality is ~10-15% lower on complex reasoning tasks than GPT-4o.

**Verdict:** hybrid. Route simple tickets (60%) to self-hosted Llama-70B, complex tickets (40%) to GPT-4o via API. Realized savings: ~$8K/month once operational. Adjusted for ops overhead and quality risk: real savings ~$3-5K/month. Whether that's worth the ops team is a business decision.

---

## Reserved vs Spot vs On-Demand

**On-demand:** most expensive, most flexible. Use for staging, canary, unpredictable workloads.

**Reserved (1-year or 3-year):** 30-70% discount. Requires commitment. Use for baseline production capacity.

**Spot:** 60-90% discount. Interruptible. Use for:
- Batch inference (workflow-first apps)
- Fine-tuning jobs
- Backfill workloads
- NEVER for interactive user-facing traffic

**The typical production mix:**
- 60% reserved (baseline)
- 30% on-demand (peak burst)
- 10% spot (batch/backfill)

---

## Multi-Provider Strategy

**Why multiple providers:**
- Outages happen (any provider can be down for hours)
- Rate limits (one provider's TPM ceiling is another's floor)
- Pricing negotiation (competitive quotes)
- Model availability (some models only on some providers)
- Regional coverage

**How to implement:**
- Provider abstraction in the BFF (already covered in [BFF section](../../1_llm_application_architecture_patterns/04_backend_for_frontend/README.md))
- Fallback logic: primary → secondary → tertiary
- Cost tracking per provider
- Weekly review of provider spend + performance

**Warning:** provider-specific features (Anthropic tool use, OpenAI structured outputs, Gemini long context) tie you in. Design fallback semantics that work with graceful degradation.

---

## Files in This Folder

| File | Concept |
|---|---|
| [`provider_pricing_2026.py`](provider_pricing_2026.py) | Reference pricing tables + provider comparison |
| [`self_hosting_math.py`](self_hosting_math.py) | Break-even calculator for self-host decision |
| [`hybrid_deployment_pattern.py`](hybrid_deployment_pattern.py) | Reference architecture for API + self-hosted hybrid |
| [`reserved_vs_spot.py`](reserved_vs_spot.py) | Capacity strategy for different workload types |
| [`multi_provider_fallback.py`](multi_provider_fallback.py) | Provider abstraction with fallback logic |
| [`ops_overhead_reality.py`](ops_overhead_reality.py) | Honest checklist of self-hosting operational cost |

---

## The Staff Interview Question

*"When would you self-host inference vs use an API?"*

**The wrong answer:** "When it's cheaper."

**The right answer:**
"Three conditions must all hold. First — sustained load. Break-even for self-hosting a 70B model is around 15-30M tokens per hour sustained. Below that, provider APIs win once you factor in ops overhead. Second — provider APIs don't meet your requirements. Either latency (need sub-200ms P99 API can't guarantee), or customization (fine-tuned model with specific inference tuning), or data residency (regulated data flows). Third — you have the ops team. Not just Kubernetes experience — actual GPU inference in production, on-call rotation, incident response. If any of these fail, provider APIs are the right call. Even at scale, most serious systems are hybrid: primary provider API for burst and variable load, self-hosted for specific sustained workloads. Pure self-hosting is rare. Pure API is common. Hybrid is the mature production pattern. And the multi-provider abstraction lives in the BFF — never let the client know which provider is serving the request."

---

*Previous: [← Model Routing](../03_model_routing/README.md) · Return to [folder README](../README.md) · Next: [Cost at Scale →](../05_cost_at_scale/README.md)*
