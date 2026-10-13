# 🧭 Decision Framework — LLM Application Architecture

A decision tree you can drop into a design doc. Answer the questions in order.

## Step 1: Application Shape

> *"What kind of AI product am I building?"*

| If... | Then... |
|---|---|
| User comes to the AI, one job per turn | **Assistant** |
| User is working on something and AI helps inline | **Copilot** |
| User states a goal, AI plans and executes | **Agent-first** |
| No user in the loop — pipeline step | **Workflow-first** |

**Key implications:**

| | Assistant | Copilot | Agent-first | Workflow-first |
|---|---|---|---|---|
| Latency budget | 2-5s to first token | < 500ms | Minutes to hours | Batch-tolerable |
| Streaming | Yes | Yes | Low | No |
| Personality | Yes | No | At boundaries | No |
| Primary metric | Response quality | Acceptance rate | Task success | Cost × accuracy |

## Step 2: Tenancy Model

> *"Who owns this deployment?"*

| If... | Then... |
|---|---|
| One user or one org | **Single-tenant** — no isolation work needed |
| Many orgs sharing infrastructure | **Multi-tenant with namespace isolation** |
| Regulated (HIPAA / defense / financial) | **Multi-tenant with physical isolation for regulated tenants** |

For multi-tenant, isolate on all six dimensions: prompts, models, data/retrieval, memory, cost, rate limits.

## Step 3: Streaming Model

> *"How do responses arrive?"*

| If... | Then... |
|---|---|
| Background job or batch | **No streaming** |
| User-facing chat, no tool calls | **SSE, simple token stream** |
| User-facing chat with tool calls | **SSE + announce-execute-continue** |
| RAG with attribution | **SSE + inline citation tokens** |
| Voice or collaborative editing | **WebSockets** |
| Agent app with HITL approvals | **WebSockets or SSE + separate action channel** |

For cancellation and resume: **buffered replay + resume tokens** is the production standard.

## Step 4: Backend Layer

> *"What sits between the model and the client?"*

Rule: **you need a BFF unless you have a very good reason not to.**

The BFF owns:
1. Provider abstraction
2. Model routing
3. Auth transformation
4. Caching (three layers)
5. Guardrails (input and output)
6. Observability
7. Rate limits per user/tenant
8. Prompt registry integration
9. Streaming translation
10. Fallback and retry

## Step 5: State Model

> *"How does state follow the user?"*

Three levels, three storage tiers:

| Level | What | Storage | TTL |
|---|---|---|---|
| Session state | Active generation, tool calls, drafts | Redis | Minutes |
| Conversation state | Message history | Postgres / DynamoDB | Days-years |
| Continuous state | User memory, preferences | Structured DB + vectors | Forever |

For multi-device: **eventual consistency + push on new message** covers 90% of consumer chat.
For enterprise copilot: **on-demand refresh** is usually acceptable.
For collaborative AI: **strong consistency required.**

---

## The Combined Decision — Worked Example

**Customer support copilot for a B2B SaaS:**

- **Shape:** Copilot (agents work in the ticket surface; AI assists inline)
- **Tenancy:** Multi-tenant with namespace isolation on all 6 dimensions
- **Streaming:** SSE with announce-execute-continue for tool calls, inline citation tokens for KB grounding
- **BFF:** Full — provider abstraction (OpenAI + Anthropic fallback), model routing (mini for simple, full for complex), per-tenant caching, injection defense, audit logging
- **State:** Session state in Redis, conversation state in Postgres per-ticket, no cross-conversation memory (compliance requirement)

That's an architecture. Now go build the RAG on top.
