# 📖 Glossary — LLM Application Architecture Patterns

**Agent-first** — Application shape where the user states a goal and the AI plans and executes. High blast radius. Task success rate as primary metric.

**Ambient assistance** — Copilot pattern where AI helps without being explicitly asked. Autocomplete, inline suggestions.

**Assistant** — Application shape where the user talks *to* the AI. Turn-based. Streaming-first.

**Backend-for-Frontend (BFF)** — Middle layer between clients and providers, owning all cross-cutting concerns (routing, caching, guardrails, observability).

**Buffered replay** — Streaming pattern where server buffers the in-flight response so a reconnecting client can catch up before live streaming resumes.

**Consistency (multi-device)** — How quickly changes on one device appear on another. Strong (real-time), eventual (seconds-minutes), on-demand (refresh required).

**Copilot** — Application shape where AI assists the user inline while they work on something else. Sub-second latency required. Acceptance rate as primary metric.

**Cross-tenant contamination** — Failure where one tenant's data influences another tenant's session. Catastrophic security incident.

**Idempotency key** — Identifier that lets a tool call be safely retried without side effects being applied twice. Essential for agent apps.

**Isolation dimensions** — The six categories of LLM multi-tenant isolation: prompts, models, data/retrieval, memory, cost, rate limits.

**Model routing** — BFF pattern where different requests are sent to different models based on complexity, cost, or quality requirements.

**Multi-tenant with namespace isolation** — Shared infrastructure with per-tenant identifiers ensuring separation. The 95% case for B2B SaaS.

**Multi-tenant with physical isolation** — Dedicated infrastructure per tenant. Required for regulated deployments.

**Noisy neighbor** — Multi-tenant failure mode where one tenant's usage patterns degrade other tenants' experience.

**Per-tenant budget** — Cost cap enforced in the BFF, preventing a runaway tenant from spending unbounded provider dollars.

**Pinning (model/prompt)** — Locking a conversation to the specific model/prompt/tool versions it started with, so upgrades don't break history.

**Pre-filter (retrieval)** — Applying the tenant filter *during* vector search, not after. Required for correct multi-tenant RAG.

**Prompt cache** — Provider-side caching of prompt prefixes, dramatically reducing cost for stable system prompts.

**Prompt registry** — Centralized store of versioned prompts, referenced by ID from clients so prompt text never leaves the server.

**Resume token** — Signed identifier that lets a reconnecting client re-attach to an in-flight streaming response.

**Semantic cache** — Cache layer that returns previous answers for semantically similar (not just identical) queries.

**Session affinity** — Load balancer configuration ensuring subsequent requests from the same client hit the same server. Required for WebSockets and simplifies SSE resume.

**Session state** — Current conversation, active generation, drafts. Lives in Redis with a TTL. Minutes lifetime.

**Server-Sent Events (SSE)** — One-way HTTP-based streaming protocol. Default choice for LLM streaming.

**Speculative streaming** — Advanced pattern where the model streams while a tool executes in parallel, with rewind/correction if the speculation was wrong.

**Spotlighting** — Prompt-injection defense where untrusted content is marked so the model treats it as data, not instructions.

**Sticky session** — Load-balancer routing that sends the same client to the same backend server. Required for stateful streaming.

**Streaming with tool calls** — Streaming pattern where the model pauses to invoke tools and resumes with results. Three sub-patterns: pause-execute-resume, announce-execute-continue, speculative.

**Tenant** — In multi-tenant architecture, one customer / one organization / one isolation boundary.

**WebSocket** — Bidirectional persistent connection. Required for voice, collaborative editing, and interactive agent flows.

**Workflow-first** — Application shape where the LLM is a pipeline step, no user in loop. Throughput and reliability over interactivity.
