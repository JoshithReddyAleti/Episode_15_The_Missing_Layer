# 📱 Session & Multi-Device — State That Follows The User

> *"They started the conversation on their phone. They're now on their laptop. Where does the state live?"*
>
> *"Uh..."*

Consumer AI trained users to expect their AI to remember them across devices and sessions. Enterprise AI trained enterprises to expect the same. Building this is not free — it's a set of specific architecture decisions.

This section is the full state model.

---

## The Three Levels of State

Every LLM app has these — even if you haven't thought about them explicitly:

### Level 1: Session State

**Definition:** the current conversation, right now. Messages in flight, active tool calls, streaming buffers.

**Lifetime:** minutes.

**Storage:** typically in-memory or Redis, keyed by session ID.

**Failure mode if lost:** user has to start over. Annoying but recoverable.

### Level 2: Conversation State

**Definition:** the full history of a specific conversation — every message, every tool call, every citation.

**Lifetime:** hours to days. Sometimes forever.

**Storage:** persistent database. Postgres, MongoDB, DynamoDB.

**Failure mode if lost:** conversation vanishes. User loses trust. Not acceptable in production.

### Level 3: Continuous State (User Memory)

**Definition:** what the AI knows about *this user*, across all conversations. Preferences, past decisions, ongoing projects, entity memory.

**Lifetime:** as long as the user exists.

**Storage:** structured DB + vector store for semantic recall (see Episode 7 for the full memory architecture).

**Failure mode if lost:** the AI treats a long-time user as a stranger. Product feels broken.

---

## The Anatomy of a Session

A single "session" in an LLM chat product involves:

- **Session ID** — server-generated, opaque to client
- **Conversation ID** — the specific conversation this session is working on (may load an old one)
- **User ID** — who owns the conversation
- **Tenant ID** — for B2B products
- **Client fingerprint** — device, browser, OS (for multi-device coordination)
- **Active generation** — is there a streaming response in progress? What's its stream ID?
- **Pending tool calls** — are we waiting for a tool result?
- **Draft messages** — did the user start typing something they haven't sent?

**All of this needs a home.** The naive answer is "in-memory on the connected server." That works until:

- The server crashes
- The load balancer routes the next request to a different server
- The user opens a second device
- The user closes and reopens the app

**Every one of these breaks in-memory state.**

---

## The Storage Hierarchy

Three tiers, matched to state levels:

### Hot Tier: Redis

- Session state (5-30 minute TTL)
- Streaming buffers for resume
- Rate limit counters
- Active tool call state

**Why Redis:** sub-millisecond reads, pub/sub for cross-server coordination, TTL for automatic cleanup.

### Warm Tier: Persistent DB

- Conversation history
- Recent user memory
- Tenant configuration

**Why persistent:** conversations must survive crashes and restarts. Postgres is fine for most; DynamoDB scales further; MongoDB for flexible schemas.

### Cold Tier: Object Storage

- Old conversations (> 90 days)
- Archived tool call logs
- Long-tail user history

**Why cold storage:** cheap, high-volume, and old conversations are rarely accessed. Compress and archive.

**The move between tiers:**
- Hot → warm: at end of session (session_end event or TTL expiry)
- Warm → cold: after N days of inactivity (typically 30-90)
- Cold → warm: on-demand when a user re-accesses old content

---

## Multi-Device Synchronization

The user is on their phone. Send a message. Get a response. Open their laptop. Should they see the phone conversation?

**Yes, obviously.** But making this work well is not trivial.

### The Consistency Choice

Three levels, decreasing complexity:

**Strong consistency.** Every device sees the latest state within milliseconds. Requires push-based sync (WebSockets or push notifications) and careful conflict resolution.

**Eventual consistency.** Every device sees the latest state within seconds-to-minutes. Can be pull-based (poll on device open) or push-based with looser guarantees.

**On-demand refresh.** User pulls-to-refresh or opens a new session. Simple, works, but feels dated.

**Which to pick:**

- Consumer chat with active multi-device usage → eventual consistency + push on new message
- Enterprise copilot with a single active device at a time → on-demand refresh is fine
- Collaborative AI features (multiple users on same conversation) → strong consistency required

### The Push Mechanism

For multi-device sync, when Device A sends a message and gets a response, Device B needs to know:

- **Push notification** for mobile — arrives even when app is closed
- **WebSocket message** for open web apps — real-time
- **Server-Sent Events** for open web apps — real-time, simpler than WS
- **Long-poll** for legacy clients — works but expensive

**The state that gets pushed:** minimal — just "conversation X updated, please refresh." Devices then pull the update. Don't try to push the full new state — bandwidth and consistency get complicated.

---

## Conversation Continuity Across Sessions

User opens the app tomorrow. Their conversation from yesterday should be there.

**Sounds simple. Isn't.**

**The questions:**

- **How do we identify "yesterday's conversation"?** Session-based (last active session) or user-selected (they pick from a list)?
- **How much history do we load?** All 500 messages? Last 20? Load-more pattern?
- **What if the model has updated?** The conversation was on gpt-4o. Now we're on gpt-5. Do we continue in gpt-4o for consistency or switch to gpt-5?
- **What if the prompt has changed?** Yesterday used prompt v3. Today we're on v4. Do we replay with the new prompt or keep the old one?
- **What if tools have changed?** A tool the conversation used has been removed. What happens if the user asks a follow-up that would invoke it?

**The design decisions:**

- **Load recent history eagerly (last 20-50 messages), rest on scroll.**
- **Pin the model + prompt + tools at conversation start.** New conversations use latest; existing conversations preserve their context.
- **Explicit "start new conversation" UX** so users can opt into the new model/prompt.
- **Immutable conversation snapshots** — old conversations are frozen in their original state. Don't rewrite history.

---

## Partial State Recovery

The user was mid-generation. Their laptop crashed. What happens when they come back?

**The states that can be in progress:**

- **Partial user message** — they typed but didn't send. Should be preserved as a draft.
- **In-flight LLM generation** — the model was generating. Was billed. Do we resume, replay, or discard?
- **Pending tool call** — the tool was executing. Did it complete? Do we display the result?
- **Streaming buffer** — tokens were sent to a client that never received them.

**The recovery patterns:**

- **Draft preservation.** User's unsent text saved to session state every N seconds. Restored on reconnect.
- **Buffered streaming replay.** In-flight generations have their tokens buffered server-side. On reconnect, the buffer replays before live streaming resumes.
- **Idempotent tool calls.** Tools with idempotency keys can be safely re-invoked; results deduplicated.
- **Explicit reconnect UX.** Sometimes the honest answer is "your last response was interrupted — retry?"

---

## Session at Scale

At small numbers, session state in Redis just works. At 1M+ concurrent sessions, things break:

- **Redis memory.** 1M sessions × 10KB each = 10GB. Reasonable. But at 100M active users the math changes.
- **Hot key contention.** If one user has multiple devices hitting the same session key, Redis Cluster sharding by user_id creates hot shards.
- **Cross-region.** User in Europe on a session hosted in US-East → high latency and possible residency issues.
- **Session-affinity in load balancers.** With WebSocket sessions, LB must route to the right server; with SSE + resume, cross-server pub/sub replaces affinity.

**The scaling patterns:**

- **Per-region session storage.** User's session lives in the region they connect from. Reduces latency; helps residency.
- **Session migration on user move.** User travels; session data migrates or replicates.
- **Consistent hashing for session distribution.** Distribute session load evenly across Redis nodes.
- **Session archival at TTL.** Move inactive sessions to persistent storage; reduce hot tier memory.

---

## Files In This Folder

| File | Concept |
|---|---|
| [`session_state_model.py`](session_state_model.py) | The three levels of state + storage tier mapping |
| [`multi_device_sync.py`](multi_device_sync.py) | Push mechanisms, consistency models, sync patterns |
| [`conversation_continuity.py`](conversation_continuity.py) | Loading old conversations, pinning model/prompt/tools |
| [`partial_state_recovery.py`](partial_state_recovery.py) | Drafts, buffered streaming, idempotent tool calls |
| [`session_at_scale.py`](session_at_scale.py) | Scaling patterns beyond 1M active sessions |

---

## The Staff Interview Question

*"A user starts a conversation on their phone, then opens the app on their laptop 30 minutes later. Walk me through the state architecture that makes this work."*

**The wrong answer:** "The conversation is in the database, so it just loads."

**The right answer:**
"Three levels of state. Session state — the actively streaming response and any in-flight tool calls — lives in Redis with a TTL, keyed by session ID. Conversation state — the message history — lives in Postgres, keyed by conversation ID and user ID. Continuous state — what we've learned about the user — lives in a mix of structured DB and a vector store for semantic recall. When the user opens the laptop, we authenticate them, resolve their user ID, query recent conversations, and load the most recent one — or let them pick from a list. We load the last 20-50 messages eagerly and paginate the rest. Crucially, we pin the model, prompt version, and tool set at conversation start, so a conversation started yesterday on gpt-4o continues on gpt-4o even after we've moved to gpt-5 for new conversations. For multi-device sync, when they send a message on the laptop, we push an event via WebSocket or SSE to any other connected devices so their phone updates. If the phone is closed, a push notification fires. For partial recovery, if the laptop crashed mid-generation, we buffered the streaming response server-side keyed by stream ID; on reconnect we replay the buffer and resume live streaming. Drafts (unsent text) auto-save every few seconds to session state. That's the architecture."

That's a staff-level answer.

---

*Previous: [← Backend-for-Frontend](../04_backend_for_frontend/README.md) · Return to [folder README](../README.md)*
