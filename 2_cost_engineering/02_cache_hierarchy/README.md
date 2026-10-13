# 🗂️ The Cache Hierarchy — 40-90% Cost Reduction, Stacked Right

> *Every LLM app has caching. Most have one layer. Serious ones have three.*

Caching is the highest-ROI cost optimization in LLM engineering. And it's the one that most teams do halfway.

This section is the full three-layer stack, how each interacts, how to measure them, and the invalidation problems nobody warns you about.

---

## The Three Caches

Not one cache. Three. They operate at different layers, catch different requests, and stack multiplicatively.

### Cache 1: Exact Response Cache
- **What it stores:** the full response for a fully-identical request
- **Where it lives:** your BFF (Redis typical)
- **Hit rate:** 5-15% typical, 30-60% for FAQ-heavy apps
- **Savings when hit:** 100% (no LLM call at all)

### Cache 2: Semantic Cache
- **What it stores:** the response for a semantically similar previous request
- **Where it lives:** your BFF (vector DB + Redis)
- **Hit rate:** 10-30% typical, higher in narrow domains
- **Savings when hit:** 100% (no LLM call at all)

### Cache 3: Provider Prompt Cache
- **What it stores:** the internal computation for a repeated prompt prefix
- **Where it lives:** provider infrastructure (Anthropic, OpenAI, Gemini)
- **Hit rate on prefix:** 60-95% if you design for it
- **Savings when hit:** 50-90% on cached tokens (input side)

**Combined effect (typical B2B RAG):**
- Response cache: -10% requests
- Semantic cache: -20% remaining requests
- Prompt cache: -70% cost on remaining requests
- **Total cost reduction: ~60-75% vs no caching**

---

## Cache 1: Exact Response Cache

### How it works

Compute a cache key from the full request context. On hit, return the stored response. On miss, call the LLM and store the response.

**Cache key components:**
```
key = hash(
    tenant_id +
    prompt_version +
    user_message +
    retrieved_context_hash +   # RAG dependency
    tools_enabled +
    model_id +
    temperature
)
```

**What makes this simple:** deterministic. Same inputs → same key → same output.

**What makes this hard:** figuring out what to include in the key.

**Common mistakes:**

- **Excluding user_id when it should be there** — user-specific memory or preferences change the answer; cross-user leaks are the result
- **Including timestamp when it shouldn't be there** — even seconds' precision breaks all cache hits
- **Not versioning by prompt or model** — you update the prompt, users still get old responses
- **Not including retrieved context hash** — retrieved docs changed, cache still serves stale answer

### TTL strategy

- **Fresh data queries** (real-time info): 60 seconds - 5 minutes
- **Stable knowledge queries** (documentation, policies): hours to days
- **Personalized queries** (user memory-dependent): don't cache, or scope to user
- **Rate-limit-relevant** (avoid caching to game rate limits): careful

### When exact cache hits and doesn't

**Hits:**
- FAQ-style bots ("what are your business hours?")
- Documentation search
- Predictable button-triggered actions ("summarize this document")

**Misses:**
- Free-form chat (nearly zero exact hits)
- Personalized assistants (user context is unique)
- Agent workflows (each attempt is different)

**Rule:** if your product has structured queries with limited variance, exact cache is a huge win. If it's open-ended conversation, don't bother — go to semantic.

---

## Cache 2: Semantic Cache

### How it works

Embed the user query. Search the semantic cache index for similar past queries. If found above a similarity threshold, return that response.

```python
def semantic_cache_lookup(query, threshold=0.95):
    query_embedding = embed(query)
    hits = cache_vector_db.search(query_embedding, top_k=1)
    if hits and hits[0].score > threshold:
        return hits[0].response
    return None  # miss
```

**Simple in code. Devilish in tuning.**

### The similarity threshold problem

- **Threshold too high (0.99):** almost no hits. Behaves like exact cache with extra latency.
- **Threshold too low (0.85):** hits on unrelated queries. Wrong answers returned.
- **Sweet spot:** 0.93-0.97, application-dependent.

**Real example that broke a product:**
- Threshold set to 0.90
- Query: *"What's the return policy for defective products?"*
- Hit: *"What's the return policy?"* (cached response about general returns)
- User gets wrong information. Files complaint. Legal team gets involved.

**Fix:** the two questions are 0.91 similar. But the answers are different. Threshold needed to be 0.97 for this domain. Every domain is different.

### What to cache and what not to

**Cache:**
- Informational queries (definitions, explanations, general info)
- Stable how-tos (documentation, tutorials)
- Common troubleshooting flows

**Don't cache:**
- Anything context-dependent (specific user, specific tenant, specific document)
- Time-sensitive information
- Anything with side effects (agent actions)
- Anything requiring personalization

### Semantic cache invalidation

The hardest problem.

- **What if the underlying source data changed?** The cache still returns the old answer.
- **Solution:** hash the retrieved-context set. On cache lookup, only return if the context hash matches.

- **What if the prompt template changed?** Cache from old prompt returned.
- **Solution:** include prompt version in the semantic key.

- **What if the model changed?** GPT-4o response returned for a Claude query.
- **Solution:** namespace the semantic cache by model.

---

## Cache 3: Provider Prompt Cache

**The one most teams miss. And the biggest cost lever.**

### How it works (Anthropic model)

You mark portions of your prompt as `cacheable`. Anthropic stores the internal KV cache for those tokens. Next request with the same prefix pays 10% of the input cost for those tokens instead of 100%.

```python
messages = [
    {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": "<big system prompt + few-shot examples>",
                "cache_control": {"type": "ephemeral"}  # ← marks as cacheable
            }
        ]
    },
    {
        "role": "user",
        "content": "<user query>"
    }
]
```

**On first request:** you pay 125% of the normal input token cost (extra 25% for cache write).
**On subsequent requests within TTL:** you pay 10% of the normal input token cost for the cached prefix.

### The TTL

- Anthropic: 5 minutes default, extendable to 1 hour
- OpenAI: automatic, ~5-10 min (no explicit control)
- Gemini: explicit caching API with configurable TTL

**Cache hit requires:**
1. Exact prefix match (byte-for-byte)
2. Within TTL window
3. Same model version

### The prompt structure that maximizes cache hits

**Bad prompt structure (no caching benefit):**
```
User: <user question>
Context: <retrieved docs — different every time>
Instructions: <system prompt>
```

The variable content is at the front. Nothing can be cached.

**Good prompt structure (maximum caching):**
```
Instructions: <system prompt — same every time — CACHED>
Examples: <few-shot examples — same every time — CACHED>
Context: <retrieved docs — sometimes cached>
User: <user question — variable — never cached>
```

Order matters. Everything stable goes first. Variable content goes last.

### Cost math example

**Without prompt caching (GPT-4o):**
- System prompt: 4000 tokens
- Few-shot: 2000 tokens
- Retrieved context: 3000 tokens
- User query: 500 tokens
- Total input: 9500 tokens × $2.50/M = **$0.0238 per call**

**With prompt caching (OpenAI, ~50% cache read discount, system+few-shot cached):**
- Cacheable prefix: 6000 tokens × 50% cost = $0.0075 effective
- Variable portion: 3500 tokens × 100% = $0.00875
- Total: **$0.0163 per call**
- Savings: **31%**

**With prompt caching (Anthropic, ~90% cache read discount):**
- Cacheable prefix: 6000 tokens × 10% cost = $0.0015 effective
- Variable portion: 3500 tokens × 100% = $0.00875
- Total: **$0.0102 per call**
- Savings: **57%**

**At 1M calls/month:** ~$14,000/month → ~$10,200/month with OpenAI caching → ~$6,240/month with Anthropic caching.

Not optional. Table stakes for any serious production LLM app.

### Prompt cache pitfalls

**"Cache miss cascade":**
- You update your system prompt for A/B testing
- Every user who was in the cached-prefix path now misses
- Cost spikes 2-3× for hours until cache warms
- **Mitigation:** stagger prompt updates; keep both versions warm during rollout

**"Retrieved context breaks the cache":**
- You put retrieved RAG context BEFORE the user query (bad cache structure)
- Every unique retrieval breaks the cache
- **Fix:** keep retrieved context at a stable prefix boundary; user query last

**"Small prompt changes destroy huge caches":**
- Adding one comma to your system prompt invalidates the cache for millions of tokens
- **Mitigation:** treat system prompts as production code; changes go through review

---

## KV Cache — Session-Level Caching

**The fourth cache, only for conversational apps.**

Within a single conversation, tokens from earlier turns can be cached for reuse in later turns of *the same session*. This is what makes long chat conversations affordable.

**How it works:**
- Session state pins the KV cache computed at the last turn
- Next turn's LLM call reuses those KV values for prior context
- Only the new user message and generation are freshly computed

**Where it lives:**
- Sometimes provider-managed (session-scoped inference APIs)
- Sometimes self-managed (if you self-host and control the inference server)

**Cost impact:**
- Enables long conversations without linear cost growth
- 10-turn conversation with 500 tokens each: naive cost O(N²), with KV cache O(N)
- At 20+ turns, the difference is 5-10× cost

**Note:** Most provider APIs don't expose this directly. Anthropic's prompt caching is the closest proxy. Full KV control requires self-hosting (see [Provider Economics](../04_provider_economics/README.md)).

---

## The Combined Cost Model

**Naive baseline:**
```
Cost = requests × cost_per_call
```

**With three-cache stack:**
```
after_exact_cache    = requests × (1 - hit_exact)
after_semantic_cache = after_exact × (1 - hit_semantic)
llm_cost_per_call    = cost_per_call × (1 - prompt_cache_savings)
Cost                 = after_semantic × llm_cost_per_call
```

**Worked example — 1M requests/month, RAG chatbot on GPT-4o:**

- Baseline cost per call: $0.024
- Exact cache hit rate: 8%
- Semantic cache hit rate: 22% (of remaining 92%)
- Prompt cache savings: 45% on remaining calls

```
after_exact = 1,000,000 × 0.92 = 920,000
after_semantic = 920,000 × 0.78 = 717,600
llm_cost_effective = $0.024 × 0.55 = $0.0132
Total cost = 717,600 × $0.0132 = $9,472
```

**vs naive: $24,000. Savings: 60%.**

Not from any single optimization. From stacking three of them.

---

## Cache Observability

You cannot optimize what you cannot measure. Every cache needs:

**Hit rate metrics:**
- Overall hit rate
- Hit rate by feature / query type
- Hit rate over time (trending down = something changed)

**Cost impact metrics:**
- Estimated savings per cache
- Actual vs projected

**Correctness metrics:**
- False hits (wrong response returned) — sampled human review
- User escalations after cached response

**Invalidation events:**
- Cache misses following a prompt update
- Cache misses following a data refresh

**Alerts:**
- Hit rate drops 20%+ vs baseline
- Cost spikes uncorrelated with volume
- Semantic cache false-hit rate above threshold

---

## Files in This Folder

| File | Concept |
|---|---|
| [`exact_response_cache.py`](exact_response_cache.py) | Reference implementation with correct key derivation |
| [`semantic_cache_implementation.py`](semantic_cache_implementation.py) | Semantic cache with threshold tuning + context hashing |
| [`prompt_cache_optimization.py`](prompt_cache_optimization.py) | Prompt structure for max provider cache hits |
| [`kv_cache_session_level.py`](kv_cache_session_level.py) | Session KV cache for long conversations |
| [`cache_invalidation_patterns.py`](cache_invalidation_patterns.py) | The hard invalidation problems and how to handle them |
| [`cache_observability.py`](cache_observability.py) | Metrics, alerts, dashboards for cache health |

---

## The Staff Interview Question

*"How would you cut LLM inference cost by 50%?"*

**The wrong answer:** "Use a cheaper model."

**The right answer:**
"Three-layer cache stack. Exact response cache in the BFF for identical requests, keyed by tenant, user, prompt version, retrieved context hash, and model. Semantic cache with tuned similarity threshold — 0.95 default, tune per domain, embed queries into a small vector index in Redis. Provider prompt cache — restructure prompts so system prompt and few-shot examples come first as a stable prefix, retrieved context and user query variable at the end. Anthropic gives 90% discount on cached prefix, OpenAI gives 50%. Combined, expect 50-70% cost reduction on typical RAG workloads. Instrument hit rates and false-hit sampling from day one — silent cache degradation is a common failure mode. Then, if we still need more, model routing to a smaller default with escalation. But cache first."

---

*Previous: [← Unit Economics](../01_unit_economics/README.md) · Return to [folder README](../README.md) · Next: [Model Routing →](../03_model_routing/README.md)*
