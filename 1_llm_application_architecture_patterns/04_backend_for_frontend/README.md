# 🎛️ Backend-for-Frontend — The Middle Layer LLM Apps Need

> *"Why do we need a BFF? The client can just call the LLM provider directly."*
>
> *— every team, right before their API key ends up in a decompiled mobile binary*

Traditional Backend-for-Frontend adapts APIs to specific frontends. LLM BFF does that *plus* centralizes every cross-cutting concern that keeps your app secure, cheap, and fast.

It's not optional. It's the layer that separates a demo from a product.

---

## What The Client Actually Needs From The LLM Layer

The bad architecture:

```
[ Mobile App ] ──API key──> [ OpenAI ]
[ Web App ]   ──API key──> [ Anthropic ]
[ CLI ]       ──API key──> [ Bedrock ]
```

Every client has the provider key. Every client implements retries, streaming parsing, error handling. Every client picks the model. Every client is subject to prompt injection because it assembles the prompts. When you want to swap providers, you update every client. When you want to add a cache, you can't — the client is talking to the provider directly.

**This is not multi-tenant. This is not secure. This is not maintainable.**

The good architecture:

```
[ Mobile App ] ──user token──┐
[ Web App ]   ──user token──┼──> [ LLM BFF ] ──provider key──> [ OpenAI ]
[ CLI ]       ──user token──┘         │                   ──> [ Anthropic ]
                                       └─────────────────> [ Bedrock ]
```

**The BFF owns all the concerns that shouldn't leak to clients.**

---

## The Ten Concerns the BFF Owns

### 1. Provider Abstraction

Client asks for "chat_completion." BFF decides which provider gets the call. Client doesn't know or care.

Why: providers deprecate models, change pricing, have outages. You need to swap in real time without a client release.

### 2. Model Routing

Small request → gpt-4o-mini. Complex request → gpt-4o. Reasoning task → o3. Failure → fallback to Claude Sonnet.

Why: cost. A well-tuned router saves 40-70% on inference costs without users noticing quality change.

### 3. Auth Transformation

Client sends a user session token (JWT, session ID). BFF resolves it to a user identity + tenant + entitlements. Then attaches the provider API key (never seen by client).

Why: security. Provider keys must never leave the server. User auth must be validated per call, not trusted.

### 4. Caching

Semantic cache (similar queries hit the same answer). Prompt cache (provider-side, if supported). KV cache (per-user session, for long conversations).

Why: cost and latency. See the Cost Engineering folder for the full hierarchy.

### 5. Guardrails

Input: PII scrubbing, injection detection, content moderation on user messages.
Output: harmful content filtering, PII detection, format validation.

Why: safety and compliance. Clients shouldn't be trusted to enforce these consistently.

### 6. Observability

Every LLM call traced with: user, tenant, prompt version, model, tokens, latency, cost, tool calls, output. Stored in a searchable log for debugging, analytics, and audit.

Why: you cannot debug what you cannot see. The client isn't the right place for this — traces would leak sensitive prompts to logs on user devices.

### 7. Rate Limiting Per User / Per Tenant

Provider limits are shared across all users. Per-user or per-tenant limits require accounting the client can't do.

Why: fair usage, cost control, noisy neighbor prevention.

### 8. Prompt Registry Integration

Client says "send message using customer_support_prompt_v3." BFF looks up the versioned prompt, assembles it, and sends. Client never handles prompt text.

Why: prompt versioning, A/B testing, security (no prompt tampering from client).

### 9. Streaming Translation

Provider streams events in *their* format. Client wants events in *your* format. BFF translates in the middle — including things like combining tool calls into single events, adding citation metadata, normalizing token counts.

Why: consistency across providers. Client code is simpler.

### 10. Fallback and Retry Logic

Provider returns 429 → wait and retry. Provider is down → route to backup provider. Model errors → escalate to a stronger model. All invisible to client.

Why: resilience. A single provider outage should not take down your product.

---

## The BFF is Not the API Gateway

**Common confusion:** teams put "the BFF" behind their existing API gateway and think they're done.

**The distinction:**

- **API Gateway** — routes traffic to services, does auth, rate limiting *at the request level*. Generic. Doesn't understand LLM concerns.
- **LLM BFF** — owns LLM-specific concerns. Prompt assembly, model routing, streaming translation, cache management, retry semantics per-provider.

The gateway is upstream. The BFF is where LLM specifics live. Sometimes they're combined for simplicity in small apps. In serious apps, they're separate.

---

## The Anatomy of a Well-Designed LLM BFF

```
                        ┌──────────────────────────────┐
User request  ─────────>│         LLM BFF               │
                        │                              │
                        │  1. Auth resolution           │
                        │  2. Rate limit check          │
                        │  3. Prompt assembly           │──> [ Prompt Registry ]
                        │  4. Cache lookup              │──> [ Semantic Cache ]
                        │  5. Model routing             │
                        │  6. Provider call             │──> [ Provider APIs ]
                        │  7. Guardrails on output      │
                        │  8. Streaming translation     │
                        │  9. Observability emission    │──> [ Trace Store ]
                        │  10. Response to client       │
                        └──────────────────────────────┘
Response  <───────────────────────────────
```

Each concern is a middleware. Each middleware is testable. Each is swappable.

---

## When You Can Skip the BFF

Rare, but exists:

- **Internal-only tools** where the client is a trusted script, not a shipped app
- **Server-to-server LLM calls** where the "client" is your own backend service (still separate concerns, but often folded into the calling service)
- **True prototypes** where you're evaluating whether the product works before investing in infra

**Do not skip the BFF because:**

- "It adds latency" — 10-30ms is negligible
- "We only have one provider" — providers change; features change; scale changes
- "We can add it later" — you can, but every client integration you build without it becomes tech debt
- "Our team is small" — a well-designed BFF is a few hundred lines of code; not a heavy investment

---

## Request Shaping — What Comes In, What Goes Out

The BFF is where request shapes get normalized.

**What the client sends:**
```json
{
  "conversation_id": "conv_abc",
  "message": "What's the status of order 12345?",
  "prompt_variant": "customer_support_v3",
  "tools_enabled": ["order_lookup", "shipping_status"],
  "stream": true
}
```

**What the BFF assembles for the provider:**
```json
{
  "model": "gpt-4o",  // decided by routing
  "messages": [
    { "role": "system", "content": "<expanded system prompt with tenant customizations>" },
    { "role": "user", "content": "<history from conversation_id>" },
    { "role": "user", "content": "What's the status of order 12345?" }
  ],
  "tools": [ /* JSON schemas for enabled tools */ ],
  "stream": true
}
```

**What the client sees back:**
```
event: token
data: {"text": "Let me check that."}

event: tool_call_start
data: {"name": "order_lookup", "args": {"order_id": "12345"}}

event: tool_call_result
data: {"name": "order_lookup", "result": {"status": "shipped"}}

event: token
data: {"text": " Your order shipped yesterday."}

event: citation
data: {"span": [23, 60], "source": "order_lookup:12345"}

event: done
data: {"tokens_used": 143, "cost_usd": 0.0021}
```

**Every one of those transformations happens in the BFF. Client stays simple.**

---

## Caching at the BFF

The BFF is the right place for caching because it sees every request. Three layers:

### Layer 1: Response Cache

Exact match on the full request. If the same tenant + user + prompt + tools + message have already produced an answer in the last N minutes, return it directly.

**Hit rate in production:** 5-15% for chatbots. 30-60% for FAQ-like features.

### Layer 2: Semantic Cache

Fuzzy match on the user's message. If a semantically similar query got a good answer recently, return that.

**Hit rate:** 10-30% depending on task diversity. Higher for narrower domains.

**Risk:** returning stale or wrong answers if similarity threshold is too loose. Always tune per-app.

### Layer 3: Provider-Side Prompt Cache

Modern providers (Anthropic, OpenAI, Google) cache the "prompt prefix" server-side. You pay less for the cached portion. The BFF is responsible for structuring prompts to maximize this — system prompt + retrieved context first (cached), user query last (variable).

**Savings:** 50-90% cost reduction on the cached prefix.

---

## Files In This Folder

| File | Concept |
|---|---|
| [`bff_fundamentals.py`](bff_fundamentals.py) | Reference architecture with all 10 concerns |
| [`llm_specific_bff.py`](llm_specific_bff.py) | What makes an LLM BFF different from a traditional BFF |
| [`request_shaping.py`](request_shaping.py) | Client request → provider request → client response transformations |
| [`caching_at_the_bff.py`](caching_at_the_bff.py) | Three cache layers and their integration |
| [`bff_vs_direct_provider.py`](bff_vs_direct_provider.py) | When to use each; the anti-patterns |

---

## The Staff Interview Question

*"Walk me through the middle layer between your web app and OpenAI."*

**The wrong answer:** "Nothing — the app calls OpenAI directly."

**The right answer:**
"We have a BFF. It owns ten concerns the client shouldn't. Provider abstraction — client asks for 'chat completion,' BFF picks OpenAI, Anthropic, or Bedrock. Model routing — small queries to a cheap model, complex to a capable one. Auth transformation — client sends a session token, BFF resolves it and attaches the provider API key server-side. Caching — three layers: exact response cache, semantic cache with tuned similarity threshold, and provider-side prompt cache maximized by prompt structure. Guardrails on input and output. Rate limits per user and per tenant. Prompt registry integration — clients reference prompt IDs, not text. Streaming translation — provider events normalized before reaching the client. Observability — every call traced with cost, latency, and tokens. Retry and fallback logic hidden from the client. All this is a small service — a few hundred lines of middleware — but it's the difference between shipping a product and shipping a demo."

---

*Previous: [← Streaming Architecture](../03_streaming_architecture/README.md) · Return to [folder README](../README.md) · Next: [Session and Multi-Device →](../05_session_and_multi_device/README.md)*
