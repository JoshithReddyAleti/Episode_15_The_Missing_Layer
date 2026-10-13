# 🎯 Interview Prep — LLM Application Architecture Patterns

Every staff-level "design an AI product" interview tests this layer. This doc maps common questions to which of the 5 sections you should lean on.

## The Universal Opener

For any "design a $PRODUCT" prompt, open with:

*"Let me start by identifying the shape — is this an assistant, a copilot, an agent-first product, or workflow-first? That decision determines latency budget, primary metric, and streaming needs. Then I'll cover tenancy, streaming, the BFF layer, and state model before we get to the actual model and RAG design."*

This alone puts you ahead of 90% of candidates.

## Question Bank

### "Design a customer support copilot."

**Lean on:** Application shapes (Copilot), Multi-tenancy (per-tenant KBs and prompts), Streaming (SSE with tool calls), Session (conversation per ticket).

**Key points to hit:**
- Copilot because agents live in the ticket surface, not in a chat
- Latency budget sub-second (they're typing past our suggestion otherwise)
- Multi-tenant isolation on prompts, KBs, memory, cost
- Streaming with tool call announcements and inline citations
- Conversation state per ticket, pinned to the model/prompt version at ticket start

### "Design a code review AI."

**Lean on:** Application shapes (Copilot on the PR), Streaming (SSE for inline comments), BFF (model routing between small/large based on diff complexity).

**Key points:**
- Copilot embedded in GitHub PR UI
- Streaming suggestions as user scrolls through diff
- Model routing: small model for style comments, larger for logic
- Per-repo prompt customization (multi-tenant)

### "Design a research assistant for financial analysts."

**Lean on:** Application shapes (Assistant-with-heavy-RAG), Streaming (inline citations critical), Multi-tenancy (per-firm compliance), Session (long-running research over days).

**Key points:**
- Assistant, with citations as a first-class requirement
- SSE with inline citation tokens — analysts need attribution in real time
- Per-firm data isolation (regulatory)
- Conversation state persists for days; pin the model/prompt to preserve reproducibility
- Cost isolation critical — analysts run expensive queries

### "Design an autonomous coding agent."

**Lean on:** Application shapes (Agent-first), Session (rich task state), Streaming (low — user waits), BFF (heavy retry/fallback logic).

**Key points:**
- Agent-first — task state is the product
- Streaming is minimal — user gets notified at completion
- Task state persisted continuously; can survive server crashes
- HITL at boundaries (spec approval, dangerous action confirmation)
- Task cost tracked; hard budget cap enforced in BFF

### "Design a document classification pipeline."

**Lean on:** Application shapes (Workflow-first), BFF (retry/routing), no streaming, no session.

**Key points:**
- Workflow-first — pipeline step, no user in loop
- Batch processing acceptable; throughput > latency
- Structured output mandatory
- Model routing: mini for easy cases, escalate to larger for uncertain
- Failure mode: silent bad output compounds — canaries and quality gates required

### "Design a voice AI assistant."

**Lean on:** Application shapes (Assistant), Streaming (WebSockets for audio), BFF (audio streaming translation).

**Key points:**
- Assistant with voice UX
- WebSockets required — bidirectional audio, cancellation on user interruption
- Streaming with tool calls: user hears "let me check that" then a beat of silence during tool exec
- Cancellation is critical — user can interrupt at any time
- BFF translates audio provider streams into unified format

### "How do you handle multi-tenancy in an LLM SaaS?"

**Lean on:** Multi-tenancy (all 6 dimensions).

**Walk through:** prompts, models, data/retrieval, memory, cost, rate limits. For each, explain namespace vs physical isolation and when to use which.

### "How do you stream LLM responses to a mobile app?"

**Lean on:** Streaming (SSE vs WebSockets), Cancellation and Resume, BFF (translation).

**Key points:**
- SSE for text streaming (works through mobile networks and proxies)
- Resume tokens for connection drops (common on mobile)
- Buffered replay server-side keyed by stream ID
- BFF translates provider events into mobile-friendly format
- Push notifications for cross-session updates

### "What sits between your app and OpenAI?"

**Lean on:** Backend-for-Frontend (all 10 concerns).

**Walk through** all 10 concerns. The candidate who lists all 10 has read this folder.

### "How does state work across devices in your product?"

**Lean on:** Session & Multi-Device (three levels, sync model, storage tiers).

**Key points:**
- Three levels of state
- Storage tier per level
- Push mechanism for cross-device (WebSocket, SSE, or push notification)
- Eventual consistency covers most consumer cases
- Buffered replay for connection drops

## The Framework To Remember

**In every AI system design interview, open by identifying:**

1. Shape (Assistant / Copilot / Agent-first / Workflow-first)
2. Tenancy (single / namespace multi / physical multi)
3. Streaming model (SSE / WS / none, and tool call semantics)
4. BFF concerns (the 10)
5. State model (three levels, three tiers)

**Then** proceed to model choice, prompt design, RAG, evaluation, etc.

This structure is not fancy. It's what senior engineers actually do. Interviewers know it. Show that you know it.
