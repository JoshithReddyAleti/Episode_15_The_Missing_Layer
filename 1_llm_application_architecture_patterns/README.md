# 🏛️ LLM Application Architecture Patterns

> *"Design a customer support copilot."*
>
> *"I'd use RAG."*
>
> *"That's not what I asked."*
>
> *🫠*

That interview happens every week at every MAANG and every frontier lab.

Candidates hear "AI product" and jump to models, prompts, and RAG. Interviewers are testing something else entirely: **do you know the meta-architecture patterns that shape LLM applications before a single prompt gets written?**

This folder is that layer.

Five patterns that separate people who *build LLM features* from people who *architect LLM products*:

1. **Application shape** — Assistant vs Copilot vs Agent-first vs Workflow-first
2. **Multi-tenancy** — How you isolate customers when the model, prompts, and data are shared infrastructure
3. **Streaming architecture** — SSE vs WebSockets, streaming with tool calls, streaming citations, cancellation, resume
4. **Backend-for-frontend** — The middle layer LLM apps need that traditional apps don't
5. **Session continuation and multi-device state** — How conversation state follows the user across devices, sessions, and days

Pick these wrong and no amount of prompt engineering saves you. Pick these right and the rest of the stack falls into place.

---

## 🎯 Why This Layer Exists

Every LLM application you'll ever build has to answer five questions before you touch a model:

1. **What shape is this product?** — Does the user drive, or does the AI drive? Is there a human loop? What does "task complete" mean?
2. **Who is this for?** — One user? One org? Thousands of orgs sharing one deployment?
3. **How do responses arrive?** — All at once? Streaming? Interleaved with tool calls? Resumable?
4. **What sits between the model and the client?** — A dumb pipe? A gateway? A full backend-for-frontend?
5. **How does state follow the user?** — Fresh session every time? Continuous across devices? Recoverable after a crash?

Get these five right and you have an architecture. Get them wrong and you have a demo.

The reason interviews at staff level ask "design a customer support copilot" and not "explain RAG" is that RAG is a component. **This layer is the product.**

---

## 📁 What's In This Folder

| Section | What It Covers | When You Need It |
|---|---|---|
| [`01_application_shapes/`](01_application_shapes/) | Assistant · Copilot · Agent-first · Workflow-first · when to pick which | Every new AI product — this is decision #1 |
| [`02_multi_tenancy/`](02_multi_tenancy/) | Isolation dimensions · per-tenant prompts · per-tenant fine-tunes · data separation · noisy neighbor · scaling to 10K+ tenants | Any B2B SaaS · any regulated deployment |
| [`03_streaming_architecture/`](03_streaming_architecture/) | SSE vs WebSockets · streaming with tool calls · streaming citations · cancellation and resume · backpressure · scaling | Any real-time UX — which is nearly all of them |
| [`04_backend_for_frontend/`](04_backend_for_frontend/) | Why LLM apps need a BFF · request shaping · cross-cutting concerns · caching · when to skip the BFF | Any app talking to multiple providers · any app with real UX |
| [`05_session_and_multi_device/`](05_session_and_multi_device/) | Session state model · multi-device sync · conversation continuity · partial state recovery · scaling sessions | Any product where a user comes back a second time |

---

## 🧭 The Five Questions Before You Prompt

Before you touch a model, answer these. In order.

### 1. What shape is this product?

**The four canonical shapes:**

**Assistant.**
User asks. AI answers. Turn-based. The AI has one job: respond to the current message. State is thin — mostly conversation history and maybe some memory.

*Examples:* ChatGPT, Claude.ai, most B2C chatbots.

**Copilot.**
User is doing something else — writing code, drafting a document, filling a form. AI assists inline. State is rich — the user's current file, cursor position, project context. The AI is not the surface; it *lives inside* the surface.

*Examples:* GitHub Copilot, Cursor, Notion AI, Grammarly.

**Agent-first.**
User states a goal. AI plans, executes, and reports. Turns are meaningful only at the boundary — user request, agent report. Between them, the AI takes 10, 20, 100 actions.

*Examples:* Devin, Manus, autonomous coding agents, deep research features.

**Workflow-first.**
Business process runs on rails. LLM is called at specific steps for specific tasks. No user in the loop for most of it. Reliability and cost matter more than intelligence or personality.

*Examples:* Invoice classification pipelines, content moderation, automated triage.

**Why the choice matters:**

| Property | Assistant | Copilot | Agent-first | Workflow-first |
|---|---|---|---|---|
| User in loop | Every turn | Passive | Boundary only | Rarely |
| State richness | Thin | Rich (host context) | Rich (task state) | Thin per-invocation |
| Latency budget | Seconds | Sub-second | Minutes to hours | Batch acceptable |
| Failure mode | Bad response | Misleading suggestion | Wrong outcome | Silent bad output |
| Primary metric | Response quality | Suggestion acceptance rate | Task success rate | Throughput × accuracy |
| Streaming importance | Very high | Very high | Low | None |
| Evaluation difficulty | Medium | Medium | Very high | Low |

Pick wrong and everything after is off. Cursor built with an Assistant architecture would be terrible. ChatGPT built as Workflow-first would be a search bar.

**Full deep-dive:** [`01_application_shapes/`](01_application_shapes/)

---

### 2. Who is this for?

**Single-tenant** — one user or one org owns the entire deployment. Easy.

**Multi-tenant with logical isolation** — one deployment, many customers, isolated at the software layer. This is where 95% of B2B SaaS lives. And it's where 95% of teams get isolation wrong.

**Multi-tenant with physical isolation** — regulated deployments (healthcare, defense, some enterprises). Separate infrastructure per tenant. Expensive but sometimes non-negotiable.

**The isolation dimensions everyone forgets:**

- **Prompt isolation.** Tenant A's system prompt cannot leak into tenant B's session.
- **Model isolation.** If tenant A has a custom fine-tune, tenant B cannot invoke it.
- **Data isolation.** Tenant A's documents cannot appear in tenant B's retrieved context.
- **Memory isolation.** Tenant A's stored preferences cannot influence tenant B's responses.
- **Cost isolation.** Tenant A's runaway usage cannot degrade tenant B's latency or budget.
- **Rate limit isolation.** One tenant's traffic burst cannot 429 another tenant's users.

Miss any of these six and you're one incident away from a security disclosure email.

**Full deep-dive:** [`02_multi_tenancy/`](02_multi_tenancy/)

---

### 3. How do responses arrive?

Not "streaming or not." Streaming has a *shape*, and the shape depends on your app.

**Full-response (no streaming).**
Simple. Client waits, then renders. Fine for background jobs, batch inference, workflow steps. Terrible for user-facing chat with 3-second first-token latency.

**Simple token streaming (SSE).**
Server pushes tokens as they generate. Client renders progressively. Standard for chat.

**Streaming with tool calls.**
The model streams a partial response, decides to call a tool, pauses, tool executes, model resumes. What does the client see during the pause? What happens if the tool fails mid-generation? What if the user cancels?

**Streaming with citations.**
Model generates content and, in parallel or after, emits citations tied to spans in the output. How do you show these appearing in real time without the UI jumping around?

**Streaming with cancellation.**
User closes the tab. Do you stop the generation? Do you keep the tokens for their next visit? Does the tool call complete or abort?

**Streaming with resume.**
User's connection drops mid-response. Do they lose the answer? Do they get it when they reconnect? Where is the state?

**The choice of SSE vs WebSockets matters more than you think:**

- SSE — one-way (server → client), automatic reconnect, HTTP/2 friendly, cheap to run, no bidirectional flow control.
- WebSockets — bidirectional, richer protocol, but sticky sessions, load-balancer complications, and mid-stream cancellation is harder.

For pure text streaming: SSE wins in 80% of cases.
For voice, agents with human-in-the-loop, collaborative editing: WebSockets earn their complexity.

**Full deep-dive:** [`03_streaming_architecture/`](03_streaming_architecture/)

---

### 4. What sits between the model and the client?

The lazy answer: nothing. Client hits the model provider directly.

That works for demos. It falls apart in production because you need:

- **Provider abstraction** — swap OpenAI ↔ Anthropic ↔ Bedrock without touching the client
- **Model routing** — small model for easy queries, escalation to large for hard ones
- **Auth transformation** — user's session token → provider API key, without leaking the provider key
- **Caching** — semantic cache, prompt cache, KV cache; the client has no business managing these
- **Guardrails** — input validation, output filtering, PII scrubbing — all before the client sees anything
- **Observability** — trace every LLM call with full context; the client shouldn't log prompts
- **Rate limiting per user** — provider limits are shared; per-user requires accounting the client can't do
- **Prompt versioning** — clients should reference "customer_support_prompt" not paste 3KB of system prompt
- **Streaming translation** — provider streaming format ≠ your client's ideal format

This is a **Backend-for-Frontend** (BFF) — an old pattern reborn for LLMs.

Traditional BFF adapts APIs to specific frontends. LLM BFF does that *plus* it centralizes all the cross-cutting concerns above. It's the reason your client stays simple and your infrastructure stays flexible.

The moment you skip the BFF is the moment your Anthropic API key ends up in a mobile app decompiled by a security researcher.

**Full deep-dive:** [`04_backend_for_frontend/`](04_backend_for_frontend/)

---

### 5. How does state follow the user?

**The three levels of state in an LLM app:**

**Session state** — this conversation right now. Messages, streaming partial responses, active tool calls.

**Continuous state** — this user's history across conversations. Preferences, past chats, memory.

**Multi-device state** — the same user, on their phone at lunch, laptop at their desk, tablet at home.

**The questions you have to answer:**

- Where does the current message live while it's being generated? (Server memory? Redis? Persistent DB?)
- If the user closes the tab mid-stream, what happens when they reopen?
- If they open the same conversation on a second device, what do they see?
- If the server they were connected to crashes, do they lose everything?
- If they have 500 past conversations, how do you paginate, search, and archive without wrecking startup latency?

**The consistency choices:**

- **Ephemeral** — state dies with the session. Simple. Users lose everything on refresh.
- **Server-persisted** — state written to DB after every turn. Standard for chat products.
- **Multi-region** — user in Europe hits US-hosted state? Latency and residency both hurt.
- **Multi-device sync** — state changes on device A must appear on device B. Push? Poll? Realtime?
- **Offline-first** — user drafts on the plane; syncs when back online. Rare but critical when required.

**Full deep-dive:** [`05_session_and_multi_device/`](05_session_and_multi_device/)

---

## 🧠 The Interview Angle

Staff-level system design interviews for AI products are 80% this layer.

**"Design a customer support copilot."**

The bad answer talks about RAG for 20 minutes.

The good answer opens with:

*"Before we get to retrieval — this is a copilot, not an assistant. The support agent is doing something else (working the ticket) and the AI assists inline. That changes latency budget to sub-second, changes the primary metric to suggestion acceptance rate, and means we need a streaming architecture with cancellation because the agent may type past our suggestion. It's multi-tenant because we're selling to multiple support orgs. We need per-tenant prompts, per-tenant knowledge bases, and cost isolation. We need a BFF because we're talking to three providers with different capabilities. And state has to survive tab reloads because support agents live in ticket queues that reset routinely. Now let's talk about the RAG."*

**That's the difference.** RAG is a component. This layer is the product.

**The five questions this folder trains you to answer instantly:**

1. What shape is this product?
2. Who is this for?
3. How do responses arrive?
4. What sits between the model and the client?
5. How does state follow the user?

Answer these before touching model selection or prompt design. Every time.

---

## 📚 How To Read This Folder

**If you have 2 hours:** read this README + the READMEs in each of the 5 subfolders. That's the mental model.

**If you have a weekend:** read all sub-READMEs and skim the code examples. That's staff-level fluency.

**If you're prepping for a system design interview:** read [`docs/INTERVIEW_PREP.md`](docs/INTERVIEW_PREP.md) — it maps every "design an AI product" question type to which of the 5 sections you should lean on.

**If you're actually building this at work:** read [`docs/DECISION_FRAMEWORK.md`](docs/DECISION_FRAMEWORK.md) — it's the decision tree you can use in a real design doc.

---

## 🔗 What This Folder Connects To

- **Depends on:** Ep 1-14 (you should already know LLM internals, RAG, memory, agents, deployment, observability, security, and A/B testing).
- **Bridges to:** Folder 3 in this repo (Reasoning Models) and Folder 4 (Enterprise Integration).
- **Prepares you for:** Agentic AI Roadmap 2027 — this layer is *especially* important for agents, where the architecture decisions compound.

---

*Return to [Episode 15 main README](../README.md) · Next folder: [Cost Engineering →](../2_cost_engineering/)*
