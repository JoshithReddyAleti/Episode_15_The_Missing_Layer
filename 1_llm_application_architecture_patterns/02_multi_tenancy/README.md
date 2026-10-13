# 🏢 Multi-Tenancy — The Isolation Nobody Plans For

> *"We're multi-tenant."*
>
> *"How?"*
>
> *"Uh... each customer has their own account?"*
>
> *🫠*

Multi-tenancy in traditional SaaS is well-understood. Row-level security, tenant IDs on every table, load isolation, done.

Multi-tenancy in LLM apps is different. And harder. Because the *model* is shared infrastructure, the *prompts* are the product, and the *retrieved context* can leak across tenants in ways that don't exist in a traditional database.

This section is the six dimensions of LLM multi-tenancy — and how to actually isolate on each.

---

## The Six Dimensions of LLM Isolation

Traditional multi-tenancy asks: "can Tenant A read Tenant B's data?"

LLM multi-tenancy asks that *and*:

1. Can Tenant A's *prompt* leak into Tenant B's session?
2. Can Tenant A's *fine-tuned model* be invoked by Tenant B?
3. Can Tenant A's *documents* end up in Tenant B's retrieved context?
4. Can Tenant A's *memory* influence Tenant B's responses?
5. Can Tenant A's *cost blowup* degrade Tenant B's latency?
6. Can Tenant A's *traffic burst* 429 Tenant B's users?

Miss any and you have an incident waiting to happen.

---

## Dimension 1: Prompt Isolation

**The risk:** Tenant A pays for a customized system prompt (their brand voice, their custom instructions, their internal terminology). If Tenant B ever sees any of it, that's IP leakage.

**How it happens:**

- Shared prompt cache with wrong keying — provider caches by prompt content, cross-tenant sharing invisible to you
- Prompt template mis-substitution — {{tenant_id}} placeholder fails, defaults leak in
- Debug endpoints that return the assembled prompt — internal tool exposed by mistake
- Prompt injection extracting the prompt — user in Tenant A's session tricks the model into repeating the system prompt

**How to isolate:**

- **Tenant-scoped prompt registry.** Prompt versions live under a tenant ID. No cross-tenant reads.
- **Deterministic prompt assembly.** No fallback to global template if tenant template missing — fail closed.
- **Prompt cache keyed by (tenant_id, prompt_hash).** Never share cache across tenants.
- **Prompt access audit log.** Every read of a tenant's prompt logged with the caller's tenant context.
- **Injection defense.** See Episode 14 — spotlighting, dual-LLM, output filtering.

---

## Dimension 2: Model Isolation (Custom Fine-Tunes)

**The risk:** Tenant A fine-tunes a model on their data. That fine-tune is IP-sensitive (their labeled data trained it). If Tenant B can invoke that fine-tune, Tenant A's data leaks by inference.

**How it happens:**

- Shared model registry with weak ACLs — Tenant B discovers Tenant A's fine-tune ID
- Multi-tenant adapter serving (SLoRA, Punica) with wrong routing — request from Tenant B hits Tenant A's LoRA adapter
- Model versioning that promotes a tenant-specific model to global without noticing

**How to isolate:**

- **Fine-tune ownership metadata.** Every custom model is owned by a tenant. Non-owner requests fail.
- **Adapter routing keyed by tenant.** Multi-LoRA serving picks adapter based on tenant context, not just model name.
- **No global "latest" pointers on tenant models.** Prevents accidental cross-tenant serving.
- **Explicit sharing model.** If Tenant A wants to share a fine-tune with Tenant B (rare but possible), it's an intentional action with an audit trail.

---

## Dimension 3: Data / Retrieval Isolation

**The most common leak surface.** Vector databases don't understand tenants natively — that's your job.

**The risk:** Tenant A's documents end up in Tenant B's retrieved context. Tenant B asks a question, gets an answer citing Tenant A's confidential document, and now you have a breach.

**How it happens:**

- Shared vector index with tenant_id in metadata but no enforcement — retrieval queries forget the filter
- Post-hoc filtering (retrieve top-k then filter) — you retrieve Tenant A's docs, throw them out, but sometimes get < k results and downgrade UX invisibly
- Approximate similarity search that ignores metadata during graph traversal — HNSW without filter-aware search sees cross-tenant neighbors
- Semantic dedup pipelines that operate across tenants — you dedupe Tenant A's doc against Tenant B's and delete the "duplicate"

**How to isolate:**

- **Pre-filter, not post-filter.** Vector DB does the tenant filter *during* the search, not after. Requires filter-aware ANN (Qdrant, Weaviate, Milvus support this).
- **Physically separate indexes per tenant** for regulated tenants or high-value contracts.
- **Namespace-per-tenant** as the default for shared indexes (Pinecone's model, Qdrant collections).
- **Retrieval audit trail.** Every retrieval logs the tenant context and the returned doc IDs. Cross-tenant hits are a critical alert.
- **Row-level security in source data.** Postgres RLS, Snowflake row-access policies — the vectors inherit the source's isolation.

---

## Dimension 4: Memory Isolation

**The subtle one.** User memory / entity memory / long-term memory in an LLM app is often stored per-user. But *user* isn't the same as *tenant*.

**The risk:** In a B2B SaaS, the same person may work at two companies. Their preferences at Company A shouldn't influence their session at Company B.

**How it happens:**

- Memory scoped to user_id when it should be (user_id, tenant_id)
- Cross-workspace users in Slack-style products with shared user identity
- Global "personalization" features that ignore tenancy

**How to isolate:**

- **Memory keys are (tenant_id, user_id, memory_type).** Never just user_id.
- **Explicit user consent for cross-tenant memory** if you offer it — with clear UX.
- **Memory purge on tenant offboarding.** When a customer leaves, their users' memories at that tenant go too.

---

## Dimension 5: Cost Isolation

**The one that kills contracts.** Tenant A has a runaway agent making 10K tool calls. Provider bills spike. Latency shared with Tenant B degrades. Tenant B's users see slowdowns.

**How it happens:**

- Shared provider quotas — one tenant burns the org's OpenAI TPM
- Shared inference pool — one tenant's high-token queries starve others
- No per-tenant cost tracking — you can't even see which tenant is causing the spike

**How to isolate:**

- **Per-tenant budget with hard caps.** Tenant hits their monthly LLM budget → gracefully degrade (fallback to smaller model, rate-limit, or block).
- **Per-tenant token accounting in real-time.** Every LLM call debits the tenant's budget bucket.
- **Cost anomaly detection per tenant.** Spike → alert → auto-throttle.
- **Contractual tier caps.** Free tier = 100K tokens/day. Pro = 10M. Enterprise = negotiated. Enforced in the BFF.
- **Provider account separation for premium tiers.** True cost isolation, at the price of losing volume discounts.

---

## Dimension 6: Rate Limit / Noisy Neighbor Isolation

**The distributed systems classic, applied to LLMs.**

**The risk:** Tenant A's traffic spike hits the provider's rate limit. Provider returns 429s. Your service returns errors to *everyone*, including Tenant B who's within their budget.

**How it happens:**

- Single provider API key shared across tenants — one tenant's TPM is everyone's TPM
- No fair scheduling in the request queue — bursty tenant crowds out steady tenants
- Backpressure not propagated per-tenant — Tenant A's queue depth affects Tenant B's latency

**How to isolate:**

- **Per-tenant rate limits enforced in the BFF.** Before you call the provider, check if the tenant is within their limit. If not, 429 *them* specifically.
- **Fair scheduling.** Weighted queue by tenant tier. Enterprise tenants have reserved capacity.
- **Multiple provider accounts** for large tenants — tenant-specific API key means their limit is their own.
- **Circuit breakers per tenant.** Tenant A's provider errors trip a breaker for *their* traffic, not global.
- **Priority tiers on the queue.** Real-time interactive traffic > batch background jobs.

---

## The Isolation Reference Matrix

| Dimension | Shared-Everything | Namespace Isolation | Physical Isolation |
|---|---|---|---|
| **Prompts** | Shared registry, tenant-tagged | Prompt registry per tenant | Separate registry deployments |
| **Models** | Shared model, per-tenant adapters | Isolated fine-tunes, shared base | Separate model deployments |
| **Vector data** | Shared index, tenant filter | Namespace per tenant | Separate vector DB per tenant |
| **Memory** | Shared DB, (tenant, user) keys | Schema per tenant | Separate DB per tenant |
| **Cost / quotas** | Global provider limits | Per-tenant budgets in BFF | Per-tenant provider accounts |
| **Rate limits** | Global provider TPM | Per-tenant rate limits | Dedicated provider accounts |

**How to choose:**

- **Startup / early product:** Shared-everything with strict namespace hygiene. Fast to build, acceptable for most B2B SaaS.
- **Growing SaaS:** Namespace isolation on all six dimensions. This is where most mature products live.
- **Regulated (HIPAA, defense, financial):** Physical isolation on at least data and memory. Sometimes on all six.

---

## Scaling to 10,000 Tenants

At small numbers, namespace isolation is easy. At 10K+ tenants it breaks in interesting ways:

- **Cold prompts.** You cache prompts, but the "long tail" of small tenants blows the cache. Solution: LRU per-tier, keep enterprise prompts warm.
- **Cold vectors.** 10K namespaces in a single vector DB creates memory pressure per active namespace. Solution: on-demand loading, cold storage for inactive tenants.
- **Small-tenant overhead.** Some tenants send 5 requests a day. Per-tenant infrastructure is wasteful. Solution: tiered architecture — shared resources for small tenants, dedicated resources for large.
- **Metadata explosion.** Every LLM call needs to know tenant tier, budget remaining, prompt version, retrieval policy, model routing rules... Solution: fast metadata cache with tenant config, refreshed on change.

---

## Files In This Folder

| File | Concept |
|---|---|
| [`isolation_dimensions.py`](isolation_dimensions.py) | Overview of the six dimensions with tenant-context reference model |
| [`prompt_isolation.py`](prompt_isolation.py) | Tenant-scoped prompt registry pattern |
| [`model_and_adapter_isolation.py`](model_and_adapter_isolation.py) | Multi-LoRA adapter routing with tenant context |
| [`data_and_retrieval_isolation.py`](data_and_retrieval_isolation.py) | Vector search with pre-filtering and RLS integration |
| [`quota_and_noisy_neighbor.py`](quota_and_noisy_neighbor.py) | Per-tenant rate limits, budgets, fair scheduling |
| [`tenancy_at_scale.py`](tenancy_at_scale.py) | Scaling patterns beyond ~1000 tenants |

---

## The Staff Interview Question

*"You're building a support automation SaaS for enterprises. Walk me through your multi-tenancy story."*

**The wrong answer:** "We put a tenant_id column on every table."

**The right answer:**
"Six dimensions to isolate. Prompts — tenant-scoped registry, cache keyed by (tenant, prompt_hash), no global fallback. Models — if tenants have fine-tunes, adapter routing by tenant context, no cross-tenant invocation. Data — vector index namespaces per tenant, pre-filter on retrieval, retrieval audit log with cross-tenant hit alerts. Memory — (tenant, user, type) composite key, purge on offboarding. Cost — per-tenant budget, hard cap, cost anomaly detection. Rate limits — per-tenant in the BFF, fair scheduling, enterprise tier gets reserved capacity. For enterprise tenants specifically, physical isolation on data and cost — separate vector DB, separate provider account. That's the isolation story. Now let's talk about the actual RAG pipeline."

Walk in with this. Every SaaS AI interview should end here.

---

*Previous: [← Application Shapes](../01_application_shapes/README.md) · Return to [folder README](../README.md) · Next: [Streaming Architecture →](../03_streaming_architecture/README.md)*
