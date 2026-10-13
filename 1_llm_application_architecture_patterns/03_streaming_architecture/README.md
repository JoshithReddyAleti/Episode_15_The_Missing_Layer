# 🌊 Streaming Architecture — The Real-Time Layer

> *"Streaming is just SSE, right?"*
>
> *"OK. What happens when the model calls a tool mid-stream?"*
>
> *"..."*

Streaming looks simple until you have to build it in production. Then you discover it's actually five separate architectural decisions, each with tradeoffs, and each interacting with the others.

This section is the full landscape.

---

## The Five Streaming Decisions

Every LLM app makes these choices — knowingly or not. Making them consciously is the difference between a UX that feels magical and one that stalls, jitters, and drops mid-response.

1. **Transport** — SSE vs WebSockets vs HTTP long-polling
2. **Tool call semantics** — how streaming pauses, resumes, and interleaves with tool execution
3. **Citation delivery** — how sources arrive without wrecking the UI
4. **Cancellation** — what happens when the user closes the tab or hits stop
5. **Resume** — what happens when the connection drops mid-stream

---

## Decision 1: Transport — SSE vs WebSockets vs HTTP Long-Polling

### Server-Sent Events (SSE)

**How it works:** HTTP/1.1 or HTTP/2 connection stays open. Server pushes text-formatted events to client. One-way (server → client).

**Strengths:**
- **Automatic reconnection** built into the browser EventSource API
- **HTTP-native** — works through proxies, load balancers, corporate firewalls
- **No sticky sessions required** at the load balancer (with reconnect logic)
- **Cheap to run** — connection state is minimal
- **Simple client code** — 10 lines of JS

**Weaknesses:**
- **One-way only** — client can't send messages on the same connection
- **HTTP/1.1 connection limit** — 6 concurrent per origin (mitigated by HTTP/2)
- **Text only** — binary data needs base64 encoding

**When it wins:** LLM chat apps, streaming responses to a browser, most consumer-facing streaming.

### WebSockets

**How it works:** Upgrade from HTTP to a bidirectional persistent socket. Both client and server can send messages at any time.

**Strengths:**
- **Bidirectional** — client sends cancel signals, user actions, cursor position
- **Binary support** — audio streams, video frames, structured protocols
- **Lower per-message overhead** — no HTTP headers per event
- **Real-time collaboration primitive** — presence, cursors, edits

**Weaknesses:**
- **Sticky sessions required** — one server owns the connection; load balancer must route back to it
- **Reconnection logic is your problem** — no browser-provided retry
- **Proxy/firewall issues** — some corporate networks strip the WS upgrade
- **More expensive to run** — each connection is a stateful resource on your server
- **Server code is heavier** — you're managing socket lifecycles

**When it wins:** Voice apps, collaborative editing with AI, agent apps with human-in-the-loop approvals, anything with a bidirectional interaction pattern.

### HTTP Long-Polling

**How it works:** Client makes HTTP request; server holds it open until it has data (or timeout); returns; client immediately requests again.

**Strengths:**
- **Works everywhere** — no special protocol support needed
- **Simple failure model** — every response is a fresh HTTP request

**Weaknesses:**
- **Highest overhead** — HTTP headers on every event
- **Latency spikes** on reconnect
- **Rarely the right choice in 2026** — SSE covers this use case better

**When it wins:** Legacy environments that don't support SSE (rare), or when you need pull semantics for specific reasons.

### The Choice

| Case | Transport |
|---|---|
| Chat, RAG, single-turn LLM responses | **SSE** |
| Voice conversations, real-time audio | **WebSockets** |
| Collaborative doc editing with AI | **WebSockets** |
| Agent apps with approve/deny buttons streaming to user | **WebSockets** |
| Copilot inline suggestions in an IDE | **WebSockets** (already have a socket for LSP) |
| Batch job status updates | **SSE** |
| Server → mobile push notifications | Neither — use push notifications |
| Legacy support required | HTTP long-polling as fallback |

**Rule of thumb:** SSE by default. WebSockets when you *genuinely* need bidirectional communication or binary data.

---

## Decision 2: Tool Call Semantics During Streaming

The model streams tokens: `"Let me check that for you. "` — then decides to call a tool. What does the client see?

**Three patterns:**

### Pattern A: Pause, Execute, Resume

Model streams up to the tool call decision. Client sees a "typing..." indicator. Tool executes. Model resumes streaming with the result.

**Pros:** Simple client-side rendering. Natural pause.
**Cons:** UX pause can feel like a hang — 3+ second tool calls are jarring. No visibility into what the AI is doing.

### Pattern B: Announce, Execute, Continue

Model streams: `"Let me check the order status."` — then explicitly emits a tool call event: `[TOOL: check_order(id=12345)]`. Client renders it as a chip or step indicator. Tool executes. Result streams: `"Your order shipped yesterday."`

**Pros:** User sees exactly what the AI is doing. Great UX for agent-flavored features. Auditable.
**Cons:** Slightly more complex client rendering. Requires structured streaming protocol.

### Pattern C: Speculative Streaming

Model streams while tool executes in parallel. If the model's speculative continuation contradicts the tool result, tokens get rewound or corrected. Bleeding-edge.

**Pros:** Feels fastest.
**Cons:** Rare in production. Complex. Only worth it for latency-critical apps.

**Which to pick:**

- **Assistant / chat:** Pattern A for one-shot tools, Pattern B for multi-step or slow tools.
- **Agent-first:** Pattern B — users want to see the reasoning trace.
- **Copilot:** Pattern A — the user just wants the completion, not the play-by-play.

---

## Decision 3: Citation Delivery

RAG apps have to show sources. Streaming complicates this because the source isn't known until *after* the model has generated the span that cites it.

**Three approaches:**

### Approach A: Citations After

Stream the full response. Then, at the end, emit `[CITATIONS: {span: [1-45], source: "doc_abc"}]`. Client renders sources as a section below.

**Pros:** Simple. Deterministic.
**Cons:** User sees a wall of text with no attribution during the stream. Trust builds slowly.

### Approach B: Inline Citation Tokens

Model is trained (or prompted with structured output) to emit `[cite:doc_abc]` inline as it generates. Client parses these during streaming and turns them into superscript links.

**Pros:** Attribution appears in real time. Higher user trust.
**Cons:** Requires the model to reliably emit correct citation tokens. Client rendering is non-trivial (superscript numbering, hover previews).

### Approach C: Post-Stream Grounding

Stream the response naturally. Run a *second* model call after (or in parallel) that identifies which spans came from which sources. Emit citations as a follow-up event.

**Pros:** Works with any base model — no citation training required. Higher accuracy of grounding.
**Cons:** Extra latency and cost. Citations appear a beat after the text.

**Which to pick:**

- **Consumer chat with RAG:** Approach B — trust is critical for consumer AI.
- **Research / enterprise search:** Approach B or C, depending on grounding accuracy needs.
- **Prototypes:** Approach A.

---

## Decision 4: Cancellation

The user closes the tab, hits stop, or navigates away mid-generation. Three questions:

**Q1: Do you stop the LLM generation?**

- **Yes always:** simplest, saves cost, model provider stops billing when you close the stream.
- **No, keep going:** if you're paying for tokens you might as well finish; user might come back.
- **Depends:** short queries continue (waste is minimal), long generations stop.

**Q2: What happens to in-flight tool calls?**

- **Complete them:** side effects have already started; may as well finish (dangerous for agent apps).
- **Attempt cancellation:** best-effort abort. Requires tools to support cancellation.
- **Fail cancel:** tool completes; result stored but not delivered.

**Q3: Do you keep the partial response for later?**

- **Yes:** user reopens the app, sees "cancelled at 200 tokens" with option to continue.
- **No:** user reopens, session is fresh. Cheaper, cleaner UX.

**The choices interact:**

- **Assistant chat, short responses:** stop LLM, don't keep partial, don't cancel tools. Simple.
- **Agent-first, long-running tasks:** don't stop LLM, keep partial, cancel non-idempotent tools. User can come back and see progress.
- **Copilot suggestions:** stop LLM immediately, discard partial. User has already moved on.

---

## Decision 5: Resume

User's connection drops. The response is 60% generated. What now?

**Option A: Restart.** Client reconnects, server starts a new generation. Wasteful. Poor UX. Never do this in production.

**Option B: Reconnect and stream the rest.** Server holds the in-progress generation, client reconnects with a resume token, server streams from where it left off.

**Option C: Buffered replay.** Server stored what it already streamed. Client reconnects, gets the buffered chunk instantly, then live-streams the rest.

**The cost of doing this right:**

- **Server-side state.** In-flight generations must be recoverable — usually a Redis-backed buffer with the stream ID.
- **Client resume tokens.** JWT or opaque ID that lets the server re-attach the client.
- **Timeout on abandoned streams.** If the client never comes back, tear down after N minutes.
- **Multi-server coordination.** In a horizontally-scaled deployment, the client may reconnect to a different server than the one running the generation. Use pub/sub (Redis, NATS) to route.

**Option C is the production standard.** Buffered replay + resume tokens + Redis pub/sub for cross-server delivery.

---

## Backpressure and Flow Control

**The failure mode nobody plans for:** the client can't consume tokens as fast as the model produces them. Buffers fill. Memory bloats. In severe cases, the server OOMs.

**Where it happens:**

- Mobile clients on slow networks
- Clients with heavy rendering (syntax highlighting, markdown parsing) blocking the receive
- Middleware transforming tokens (translation, PII scrubbing) slower than the source

**Mitigation:**

- **Server buffer bounds.** If the buffer to the client exceeds N tokens, either pause the generation or drop the connection.
- **Client-side ACKs.** For WebSockets, client sends periodic ACKs; server slows if ACKs lag.
- **Token batching.** Instead of one event per token, batch 5-20 tokens per event. Reduces overhead, easier flow control.

---

## Streaming at Scale

Streaming architecture that works for 100 concurrent users breaks in interesting ways at 100K:

- **Connection limits.** SSE on HTTP/1.1 caps browsers at 6 concurrent connections. On the server side, 100K open connections require careful tuning (increased ulimit, epoll-based servers, kernel-level networking optimizations).
- **Load balancer sticky sessions.** For WebSockets you need affinity. For SSE with resume, you need affinity or cross-server state.
- **Provider streaming rate limits.** Some LLM providers rate-limit *concurrent* streams. Your architecture may need to queue at high load.
- **Cost of holding connections.** Idle streaming connections still consume server memory. At 100K connections × 1MB per connection = 100GB RAM just for buffers.

---

## Files In This Folder

| File | Concept |
|---|---|
| [`sse_vs_websockets.py`](sse_vs_websockets.py) | Transport decision — code comparison and choice framework |
| [`streaming_with_tool_calls.py`](streaming_with_tool_calls.py) | Three patterns for pausing and resuming around tool calls |
| [`streaming_citations.py`](streaming_citations.py) | Three approaches to attribution during streaming |
| [`cancellation_and_resume.py`](cancellation_and_resume.py) | Cancellation semantics + buffered replay pattern |
| [`backpressure_and_flow_control.py`](backpressure_and_flow_control.py) | Bounded buffers, ACKs, and safety at high load |
| [`streaming_at_scale.py`](streaming_at_scale.py) | Connection limits, load balancing, sticky sessions |

---

## The Staff Interview Question

*"Design the streaming layer for an AI chat product with tool calls and citations."*

**The wrong answer:** "I'd use SSE."

**The right answer:**
"Five decisions. Transport: SSE, because it's one-way from server to client, works through proxies, and reconnects automatically. WebSockets only if we need bidirectional — not the case for basic chat. Tool call semantics: Pattern B, announce-execute-continue, because users want visibility into what the AI is doing during tool execution, especially for anything > 500ms. Citations: inline citation tokens, Approach B, because trust is critical in consumer AI and post-hoc citations feel disconnected. Cancellation: user closes tab, we stop LLM generation immediately to save cost, we cancel idempotent tool calls, we don't retain partial output. Resume: buffered replay with Redis-backed stream state, resume tokens signed as JWTs, pub/sub for cross-server delivery so any load-balanced server can serve the resume request. At scale we'd add per-user connection quotas, token batching to reduce event overhead, and bounded buffers to prevent OOM from slow clients."

That's the answer.

---

*Previous: [← Multi-Tenancy](../02_multi_tenancy/README.md) · Return to [folder README](../README.md) · Next: [Backend-for-Frontend →](../04_backend_for_frontend/README.md)*
