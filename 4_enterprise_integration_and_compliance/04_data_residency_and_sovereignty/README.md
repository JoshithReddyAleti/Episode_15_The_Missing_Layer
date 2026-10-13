# 🌍 Data Residency & Sovereignty — Where The Bytes Actually Live

> *"Our EU customers' data stays in the EU."*
>
> *"OK. Your Redis cache is in us-east-1. Your prompt cache is on OpenAI's servers in Texas. Your semantic cache backend is a Pinecone index in us-west. Your audit logs go to Datadog which stores in us-east. Where exactly does the EU data stay?"*
>
> *🫠*

Data residency is the single most under-modeled aspect of enterprise AI deployment. Every layer of your stack — application, cache, vector index, LLM provider, observability — is a data location. If your customer's contract requires "data stays in region X," every one of those layers must comply.

This section is how to build architecture that actually delivers on residency promises.

---

## Why This Matters More Than Most Engineers Realize

**The regulatory drivers:**

- **GDPR:** cross-border transfers of EU personal data require adequacy decision, SCCs, or specific derogations. Non-compliance = fines up to 4% of global revenue.
- **Schrems II (CJEU 2020):** invalidated Privacy Shield. Made US-EU transfers legally uncertain. DPF (Data Privacy Framework) partially replaces it but ongoing legal challenges.
- **China Cybersecurity Law + PIPL:** personal data of Chinese residents must be stored in China (with narrow exceptions). Cross-border transfer requires security assessment.
- **Russia (152-FZ):** personal data of Russian citizens must be stored on servers physically in Russia.
- **India Digital Personal Data Protection Act (2023):** cross-border transfers restricted to notified countries.
- **Brazil LGPD:** similar transfer restrictions to GDPR.
- **Australian Privacy Act updates:** ongoing tightening.
- **US state-level:** CCPA doesn't mandate residency but does impose transfer disclosure.

**The commercial drivers:**

- **Sovereign cloud requirements:** many enterprises now write "data must remain in region X" into contracts, independent of legal requirement, driven by boardroom concerns about foreign government access.
- **Government + defense customers:** sovereignty is non-negotiable. Often requires deployment in gov-specific clouds.
- **Sector-specific:** European banking regulators, healthcare authorities have sector-specific residency expectations.

**The engineering consequence:** you cannot ship an enterprise AI product with a single global deployment. Multi-region is the entry ticket.

---

## The Data Locations You Actually Have

For any LLM call, data touches at minimum:

| Layer | Typical location | Residency risk |
|---|---|---|
| Client app | User's device | Low (transient) |
| API gateway | Your primary region | Medium |
| BFF service | Your primary region | Medium |
| Session cache (Redis) | Your primary region | High (contains user query + response) |
| Response cache | Your primary region | High |
| Semantic cache | Vector DB region | High |
| Vector store (RAG) | Vector DB region | Critical (customer documents) |
| Conversation history DB | Primary region | Critical |
| User memory / preferences | Primary region | High |
| LLM provider | Provider's region | Critical (raw prompt with user data) |
| LLM provider prompt cache | Provider's region | High |
| Observability (metrics, traces) | Observability provider region | Medium-High |
| Audit log storage | Your primary region | Critical (contains PII/PHI) |
| DLP scanning | DLP provider region | High |
| Guardrail model calls | Guardrail provider region | High |

**Every one of these is a residency decision point.** Every one can violate a residency requirement.

Most teams optimize the first few and forget the rest.

---

## The Regional Architecture Pattern

The core idea: **partition your deployment by region, and route users to their region's stack based on residency policy.**

```
                         User request
                              │
                              ▼
              ┌────────────────────────────┐
              │  Geo-routing / DNS or CDN   │
              │  Determines region based on  │
              │  user identity + policy      │
              └────────────────────────────┘
                    │             │             │
          ┌─────────┴──┐   ┌──────┴──────┐   ┌──┴─────────┐
          ▼            │   ▼              │   ▼             │
   ┌───────────────┐   │  ┌───────────────┐  ┌───────────────┐
   │  us-east-1    │   │  │  eu-west-1    │  │ ap-southeast-1│
   │  US stack      │   │  │  EU stack      │  │  APAC stack   │
   │  full stack   │   │  │  full stack    │  │  full stack   │
   │               │   │  │                │  │               │
   │ • BFF          │   │  │ • BFF           │  │ • BFF          │
   │ • Redis (US)   │   │  │ • Redis (EU)    │  │ • Redis (APAC) │
   │ • Vector DB    │   │  │ • Vector DB     │  │ • Vector DB    │
   │ • LLM: OpenAI  │   │  │ • LLM: Anthropic│  │ • LLM: Bedrock │
   │   (US region)  │   │  │   (EU region)   │  │   (APAC)       │
   │ • Audit (US)   │   │  │ • Audit (EU)    │  │ • Audit (APAC) │
   └───────────────┘   │  └───────────────┘  └───────────────┘
```

**Key properties:**
- Each region is a full stack — data does not leave the region
- User is bound to a home region based on their identity/tenant/consent
- Cross-region data flow only for explicit business reasons (analytics aggregation, audit rollups) and only in anonymized/aggregated form
- Failover within region (multi-AZ), not across regions, for residency-sensitive tenants

---

## Regional LLM Provider Availability

Not every LLM is available in every region. As of 2026:

**OpenAI direct API:**
- Global endpoint (routing not guaranteed to a region)
- No formal regional API endpoints for standard products
- **Azure OpenAI** is how you get regional (Azure regions worldwide)
- **Data residency guarantees available on Azure OpenAI** for specific regions

**Anthropic direct API:**
- Global endpoints (US and EU as of 2026)
- **Bedrock (Anthropic on AWS):** available in multiple AWS regions with regional guarantees

**Google (Gemini):**
- Vertex AI in many GCP regions
- Regional model access varies (larger models sometimes US-only initially)

**AWS Bedrock:**
- Multiple regions including us-east-1, us-west-2, eu-central-1, eu-west-1, eu-west-3, ap-northeast-1, ap-south-1, and GovCloud
- Regional isolation with cross-region inference optional (must explicitly enable)
- **Bedrock Custom Model Import** for full residency of self-hosted models

**Azure OpenAI:**
- Extensive regional coverage
- **Provisioned Throughput Units (PTUs)** give regional guarantees
- **Azure Government** for FedRAMP High

**DeepSeek and other Chinese providers:**
- China + potentially APAC (varies)
- Legal issues for EU/US regulated deployments (transfer restrictions apply from China)

**Self-hosted (Llama-3, DeepSeek-R1, Mistral):**
- Any region you can deploy GPUs
- **The escape hatch for sovereignty concerns**

### Practical routing table (2026 recommendations)

| User region | Recommended primary LLM | Fallback |
|---|---|---|
| US commercial | OpenAI/Anthropic/Bedrock (any US region) | Cross-provider failover |
| US Government | Bedrock GovCloud / Azure OpenAI Gov | Self-hosted (GovCloud GPU) |
| EU commercial | Anthropic EU / Bedrock eu-central-1 / Azure OpenAI EU | Self-hosted in EU |
| EU regulated (banking, healthcare) | Bedrock eu-* with residency contract / Azure OpenAI EU | Self-hosted |
| UK | Same as EU or Azure UK South | |
| APAC commercial | Bedrock ap-* / Azure OpenAI APAC | |
| Japan (strict) | Bedrock ap-northeast-1 / Azure Japan | |
| India | Bedrock ap-south-1 (India residency requires care) | Self-hosted India |
| China | Self-hosted DeepSeek-R1 / Qwen on Chinese cloud | (Legal review required for cross-border) |
| Russia | Self-hosted only | (Legal review) |

---

## Cross-Border Data Transfer Legal Instruments

When data must cross borders:

### Adequacy decisions
Countries the EU has determined provide adequate protection. Transfer without additional safeguards.
- As of 2026: UK, Switzerland, Japan, Canada (partial), South Korea, and others.
- **US has DPF (Data Privacy Framework)** — allows transfers to DPF-certified US organizations. Under legal challenge (Schrems III likely).

### Standard Contractual Clauses (SCCs)
Contract templates approved by the European Commission. Used for transfers to non-adequate countries.
- Requires Transfer Impact Assessment (TIA)
- Must include supplementary measures if the destination country's laws could compel disclosure
- Most legally robust option today

### Binding Corporate Rules (BCRs)
Internal rules for intra-group transfers. Only useful for large multinationals with EU authority approval.

### Derogations (Article 49)
Explicit consent, contract necessity, public interest. Narrow and specific.

**For LLM apps:** the practical answer is regional deployment (no transfer) or SCCs (regulated transfer). Adequacy for US is uncertain long-term.

---

## The Provider Cache and Training Problem

**Provider prompt cache:** even if you route to eu-west-1, if the provider's cache stores your prompt content and that cache is replicated globally for performance, you may have unintentional transfers.

**What to check:**
- Is the prompt cache regional or global?
- What's the TTL and eviction policy?
- Is cache data included in the DPA?

**Provider training on inputs:** if the provider trains on API inputs (some do by default; enterprise contracts usually opt out), your data becomes model weights globally distributed.

**Non-negotiable for enterprise:** training opt-out in the contract. Every provider offers this on enterprise tier.

**Anthropic:** does not train on API inputs by default (explicit opt-in required, mostly for research collaborations).

**OpenAI:** enterprise API does not train by default. ChatGPT does. Confirm your surface.

**Google:** enterprise Vertex API does not train by default.

---

## Tenant-Specific Residency Preferences

For multi-tenant SaaS, different tenants have different residency requirements:

- Tenant A (US non-regulated): any US region
- Tenant B (US healthcare): specific US region, BAA, encryption at rest with CMK
- Tenant C (EU): EU-region, no US transfer
- Tenant D (Germany-only): eu-central-1 (Frankfurt) specifically, no other EU region
- Tenant E (multi-region, complex): user-level residency (EU users in EU, US users in US)

**Architecture pattern:**

Tenant config includes:
```yaml
tenant_id: acme_healthcare
primary_region: us-east-1
allowed_regions: [us-east-1, us-east-2]  # for failover
llm_providers: [anthropic-bedrock-us-east-1]
require_cmk: true
cache_regions: [us-east-1]
vector_store: pinecone-us-east
audit_region: us-east-1
observability: datadog-us
data_classification: hipaa_phi
require_baa: true
```

BFF reads this config for every request and enforces routing. Any component call to a region not in `allowed_regions` is a compliance violation — must fail closed.

**For user-level residency** (Tenant E):
- User's home region stored in identity claims
- Requests always routed to home region regardless of where user physically is
- If user in Tokyo logs in for a US-home tenant, request still routes to US region (adds latency, but preserves residency guarantee)

---

## Data Sovereignty vs Data Residency

**Data residency:** data physically located in region X.

**Data sovereignty:** data subject only to region X's laws and immune to foreign government access requests.

They are not the same.

**The Schrems II issue:** even if EU data is physically in EU-region servers, if the operator is a US company subject to US law (Cloud Act, FISA), the data may not have true sovereignty.

**True sovereignty solutions:**

- **Sovereign cloud offerings:** GCP Sovereign Controls, AWS European Sovereign Cloud (upcoming), Azure EU Data Boundary. Structured to isolate from parent-company control.
- **In-country operators:** German Trust Region (T-Systems), French operator partnerships. Data controlled by in-country entity.
- **Self-hosted in your own facility:** ultimate sovereignty. Highest operational cost.

**For most enterprise deployments:** regional deployment satisfies residency requirements. Sovereignty specifically comes up for government, defense, and highly regulated verticals.

---

## The Observability Trap

Everyone plans regional stacks for the main data path. Observability is where residency assumptions leak.

**The failure mode:** BFF in eu-west-1 logs to Datadog. Datadog stores in Datadog's US region by default. EU personal data is now in the US.

**The mitigations:**
- Datadog / New Relic / Splunk offer EU regions — configure explicitly
- Trace sampling with PII scrubbing before export
- Local metrics stores + regional dashboards
- Log aggregation regional, cross-region rollups only for anonymized aggregate

**The audit log specifically:** given it's forensically critical and contains user identity, it belongs in the same residency as primary data.

---

## Testing Residency Compliance

**The auditor's question:** "prove that user X's data has never left the EU."

**How to answer:**
- Network flow logs showing all connections stayed in EU regions
- Explicit egress firewall rules blocking non-EU destinations
- Automated tests injecting EU test users, tracking all downstream calls, verifying region tags on every hop
- Provider attestations that their EU-region service does not egress data

**Recommended: quarterly residency audit.**
- Automated test suite runs synthetic EU user traffic
- Instrumentation captures every downstream service call with region tag
- Test fails if any call goes to non-EU region
- Results archived for regulatory disclosure

---

## Files In This Folder

| File | Concept |
|---|---|
| [`regional_deployment_pattern.py`](regional_deployment_pattern.py) | Multi-region stack topology and routing |
| [`provider_region_selection.py`](provider_region_selection.py) | LLM provider regional availability decision matrix |
| [`transfer_instruments.py`](transfer_instruments.py) | Adequacy, SCCs, BCRs — when each applies |
| [`tenant_residency_config.py`](tenant_residency_config.py) | Per-tenant residency policy enforcement |
| [`sovereign_cloud_options.py`](sovereign_cloud_options.py) | Sovereign cloud vs sovereign self-hosted patterns |
| [`residency_test_harness.py`](residency_test_harness.py) | Automated residency validation |

---

## The Staff Interview Question

*"How do you handle GDPR data residency for a multi-tenant AI SaaS?"*

**The wrong answer:** "We deploy in EU regions for EU customers."

**The right answer:**
*"Multi-layered residency architecture. First — regional stack topology. Every region has a full independent stack: BFF, Redis, vector DB, audit log, observability. Regions do not share data at rest. Second — tenant residency policy in tenant config, enforced at every layer. Any service call to a region not in the tenant's allowed list fails closed with an alert. Third — LLM provider selection per region. For EU, we use Anthropic EU or Bedrock eu-central-1 or Azure OpenAI EU depending on tenant's provider preference and BAA arrangements. Prompt cache and any provider-side data explicitly scoped to region via provider contract. Training opt-out mandatory in the DPA. Fourth — cross-border data flow only for anonymized aggregate telemetry, with cryptographic PII scrubbing before export. All observability into the EU-region SaaS accounts of Datadog / equivalent, not the default US. Fifth — automated residency validation. Quarterly synthetic-user tests generate EU traffic and instrumentation captures every downstream call. Any non-EU destination fails the test. Sixth — transfer instrument coverage: SCCs signed with every sub-processor that ever legitimately needs cross-border transfer. Transfer Impact Assessment documented. Seventh — architectural documentation ready for supervisory authority: data flow diagram, region map, control evidence, DPA and SCC copies. That's the residency posture. For sovereign customers — defense, government — we additionally offer self-hosted deployment with DeepSeek-R1 or Llama in the customer's cloud or facility. That's the fallback for true sovereignty."*

That's a principal-level answer.

---

*Previous: [← Compliance Frameworks](../03_compliance_frameworks/README.md) · Return to [folder README](../README.md) · Next: [Audit Trails & Observability →](../05_audit_trails_and_observability/README.md)*
