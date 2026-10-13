# 📜 Audit Trails & Observability — What The Auditor Actually Asks For

> *"Can you produce a complete record of every LLM call user Alice made between March 1 and March 15, including the identity chain, retrieved documents, model version, prompt content, response, and downstream tool invocations — within 48 hours?"*
>
> *"Uh... we have Datadog?"*

Enterprise AI lives and dies by audit trails.

Not "logs." Not "we have observability." **Audit trails.** A specific, forensic record of every action, with cryptographic integrity, sufficient retention, and disclosure workflows that satisfy regulators, litigation, and internal governance.

This section is what to actually log, how to store it, how long to keep it, and how to produce it on demand.

---

## Why Audit Is Different From Observability

**Observability answers:** "why is the system slow / breaking / cost-spiking?"
Metrics, traces, logs. Sampling is fine. Aggregation is helpful. Data retention is short.

**Audit answers:** "what did user X do on date Y, and what was the system's response?"
Complete record. Zero sampling. Tamper-evident storage. Long retention (years, sometimes decades).

You need both. **They cannot be the same system.**

**Common mistake:** treating Datadog as the audit log. Datadog is sampled, mutable, retention-limited, and hosted where it may not satisfy residency. It's a great observability platform. It's a bad audit log.

---

## The Audit Event Schema

Every LLM call emits an audit event. The schema:

```json
{
  "event_id": "evt_01H8XPQZ...",
  "event_type": "llm.call",
  "event_version": "1.0",
  "timestamp": "2026-08-11T14:32:00.123Z",
  "timestamp_source": "server_ntp",

  "identity": {
    "user_id": "usr_alice_123",
    "user_email": "alice@acmecorp.com",
    "tenant_id": "acme_corp",
    "workspace_id": "ws_engineering",
    "authentication_method": "saml_okta",
    "mfa_verified": true,
    "session_id": "sess_...",
    "acting_as": null,
    "delegation_ticket": null,
    "roles": ["member", "ai_user"],
    "groups": ["engineering", "senior_staff"],
    "identity_provider_claims_hash": "sha256:..."
  },

  "request": {
    "feature": "code_review_copilot",
    "prompt_version": "code_review_v3.2",
    "user_message_hash": "sha256:...",
    "user_message_length_tokens": 342,
    "user_message_contains_pii": false,
    "retrieved_documents": [
      {"doc_id": "doc_a", "source": "github", "acl_check": "passed", "score": 0.87},
      {"doc_id": "doc_b", "source": "github", "acl_check": "passed", "score": 0.82}
    ],
    "tools_available": ["file_read", "code_search"],
    "context_classification": "internal"
  },

  "processing": {
    "model": "gpt-4o",
    "model_version": "2025-11-06",
    "provider": "openai",
    "provider_region": "us-east-1",
    "reasoning_enabled": false,
    "input_tokens": 3450,
    "output_tokens": 512,
    "reasoning_tokens": 0,
    "cache_status": "prefix_hit",
    "cost_usd": 0.0087,
    "latency_ms": 2340
  },

  "response": {
    "response_hash": "sha256:...",
    "response_length_tokens": 512,
    "contains_pii": false,
    "contains_code": true,
    "tool_calls_made": [
      {"tool": "file_read", "params_hash": "sha256:...", "success": true}
    ],
    "guardrail_flags": [],
    "human_reviewed": false
  },

  "policy_evaluation": {
    "rbac_check": {"result": "allow", "policy_version": "v2.1"},
    "abac_check": {"result": "allow", "conditions_met": ["classification_ok", "region_ok"]},
    "dlp_scan_input": {"result": "clean", "categories_checked": ["pii", "phi", "pci"]},
    "dlp_scan_output": {"result": "clean", "categories_checked": ["pii", "phi"]},
    "content_moderation": {"result": "clean"}
  },

  "integrity": {
    "prev_event_hash": "sha256:...",
    "self_hash": "sha256:...",
    "signature": "..."
  }
}
```

**Rationale for each block:**

- **identity:** answers "who did this" — SOC 2, HIPAA, GDPR all require this
- **request:** answers "what did they ask" — sufficient for reconstruction without storing full PII
- **processing:** answers "how did we handle it" — model, cost, latency for internal and regulatory review
- **response:** answers "what did we return" — hash for verification, flags for content
- **policy_evaluation:** answers "did we enforce policy correctly" — critical for compliance audits
- **integrity:** cryptographic chain — proves the log wasn't tampered with

**Note on content:** we store *hashes* of user messages and responses, not the plaintext. This is intentional — plaintext audit logs are a data-protection nightmare. If we need plaintext for investigation, it's retrieved from separate content storage with additional access controls and shorter retention.

---

## Content Storage Separate From Audit

**The pattern:**

- **Audit log (long-term, immutable):** metadata + hashes. Retained per compliance requirement (7 years typical for financial).
- **Content archive (medium-term, encrypted):** actual plaintext prompts and responses. Retained per data minimization principle (30-90 days typical, longer for specific tenants).
- **Content lookup workflow:** during investigation, authorized user requests content by event_id. Access logged. Content retrieved from encrypted storage.

**Why this split:**
- Compliance requires long audit retention but minimization principle discourages long plaintext retention
- Plaintext logs are a breach target
- Content typically needed only during active investigation, not routine review
- Segregation of duties: audit log admin isn't automatically content admin

---

## Tamper-Evident Storage

Regulators (SOC 2, HIPAA, SOX especially) require that audit logs cannot be silently modified after the fact.

**Options, from lightest to heaviest:**

### Option A: Append-Only with Access Controls
Standard database with strict INSERT-only permissions. No UPDATE, no DELETE. Backup rotation ensures old data can't be modified.

**Weakness:** an admin with sufficient privilege can still modify.

### Option B: WORM (Write-Once, Read-Many) Storage
AWS S3 Object Lock in Compliance mode, Azure Blob Immutability, GCP Bucket Retention Lock. Once written, cannot be modified or deleted for the retention period, even by root/owner.

**Strength:** genuine immutability, satisfies most auditors.

### Option C: Cryptographic Hash Chain
Each event includes hash of previous event. Modifying any event invalidates the chain from that point forward. Requires periodic anchoring of the chain head to an external timestamp (blockchain, external notary, DNS-based timestamp).

**Strength:** even total control of the storage system can't hide tampering — verification is external.

### Option D: External Signing / Notarization
Events cryptographically signed by an HSM, or notarized to an external service (public blockchain, trusted timestamp authority).

**Strength:** highest integrity assurance. Required for some legal contexts.

**Practical recommendation:**

- **Standard enterprise:** WORM storage (Option B) with cryptographic hash chain (Option C).
- **High-stakes (financial, litigation-exposed, government):** add external signing (Option D).
- **HIPAA / SOC 2 minimum:** Option A + Option B. Auditors accept.

---

## Retention Policies

Different data requires different retention. And retention is often the *maximum* not the minimum — data minimization principle requires disposing when no longer needed.

**Typical retention matrix:**

| Data type | Regulated minimum | Business need | Recommended |
|---|---|---|---|
| Audit log metadata | 3-7 years (varies) | Investigation window | 7 years, then archive |
| Content plaintext | None mandated | Investigation window | 30-90 days |
| Conversation history | User preference | Product feature | User-configurable, default 90 days |
| Session state | None | Session recovery | 24 hours |
| Semantic cache | None | Cost optimization | 7 days |
| PHI in audit | HIPAA 6 years | Compliance | 7 years |
| Financial audit | SOX 7 years | Compliance | 7 years |
| GDPR-erasure-requested data | Must delete | User right | Immediate |
| Legal hold data | Duration of hold | Litigation | Preserve indefinitely until hold released |

**Retention automation:**

- **Lifecycle policies at storage layer** (S3 lifecycle, blob tiering) — move to cold storage then delete
- **Application-level TTLs** for cache and session
- **Right-to-erasure processor** — user requests delete, application deletes across all layers (see below)
- **Legal hold flag** — sets retention to "indefinite" until released by legal; overrides normal deletion

---

## Right-to-Erasure Workflows

GDPR Art 17 requires deletion within 30 days of verified request. Implementation is genuinely hard because data is spread across many stores.

**The multi-system erasure workflow:**

```
1. User submits erasure request (verified via re-auth)
2. Legal reviews and confirms no legal hold or retention obligation prevents deletion
3. Deletion job initiated with tracking ID
4. Delete from:
   a. Primary database (user record + linked records)
   b. Conversation history DB
   c. Session cache (Redis) — evict all keys for user
   d. Semantic cache — evict all entries where user was contributor
   e. Vector store — delete embeddings of user's uploaded content
   f. Backup snapshots — mark for scrubbing on next rotation
   g. LLM provider prompt cache — API call to evict if provider supports
   h. Observability metrics — evict identifiable traces
   i. Content archive — delete plaintext prompts/responses
5. Audit log (RETAINED) — records the erasure event but keeps the pre-erasure metadata (allowed under legitimate interest for compliance)
6. Downstream integrations notified via webhook
7. Confirmation to user within 30 days with attestation
8. Post-erasure verification job — sample confirms deletion actually occurred
```

**The gotchas:**

- **Backups:** you may not delete from backups immediately. Document backup retention and eventual deletion cadence.
- **Model weights:** if the provider trained on the user's inputs, weights contain memorized data. You cannot delete from weights. Prevent via training opt-out.
- **Analytics aggregates:** aggregated statistics that no longer identify the user typically don't need deletion.

**Enterprise expectation:** produce a documented erasure runbook and test it quarterly.

---

## Legal Hold

Litigation or regulatory investigation freezes normal retention.

**The pattern:**

- Legal team receives hold notice from counsel
- Marks affected tenants / users / date ranges in the retention system
- Normal deletion workflows skip held data
- Held data retained until hold released
- All access to held data logged separately for the litigation record

**Common failure:** legal hold flag exists but application code doesn't check it. Normal deletion happens. Discovery request comes back "we don't have that data." Adverse inference in court.

**Design implication:** legal hold check is at the deletion layer, not the request layer. Every deletion operation — automatic or manual — checks the hold registry first.

---

## SIEM Integration

Enterprise security operations centers (SOCs) expect your audit events to flow to their SIEM.

**Standard integrations:**

- **Splunk:** HTTP Event Collector (HEC) or Splunk Connect
- **Datadog:** Cloud SIEM ingestion
- **Sentinel (Microsoft):** connectors for major AWS/GCP/SaaS
- **Chronicle (Google):** cloud-native ingestion
- **Sumo Logic, Rapid7, Exabeam:** vendor-specific connectors

**What to send:**
- All authentication events
- All authorization decisions (especially denies)
- All AI feature usage events
- All policy violations and DLP flags
- All admin/support impersonation events
- All configuration changes

**What NOT to send:**
- Plaintext user content (PII contamination of SIEM)
- Provider API keys or secrets
- Full conversation history (metadata sufficient)

**Format:** most SIEMs prefer CEF (Common Event Format), Syslog, or JSON. Standardize on one.

---

## Anomaly Detection

Beyond audit logging, actively detect suspicious activity:

**AI-specific anomalies:**

- **Prompt injection attempts:** patterns matching known injection payloads
- **Data exfiltration patterns:** user asking for large data extraction, or long output that looks like a data dump
- **Impossible travel:** user auth from geographically implausible location pair within short window
- **Privilege escalation attempts:** user querying about system prompts, jailbreak patterns, adversarial phrases
- **Volume anomalies:** user's LLM usage 100× baseline in short window
- **Sensitive query patterns:** queries about specific PII/PHI fields that this user shouldn't be interested in
- **Off-hours access:** access outside user's normal working hours (or holidays)
- **New device or new region:** user accessing from unrecognized device/location

**Response tiers:**

- **Log only** — for informational anomalies
- **Alert on-call** — for suspicious patterns
- **Step-up MFA** — challenge the user
- **Rate limit** — throttle traffic
- **Block + investigate** — for high-confidence attacks

---

## Discovery and Disclosure Workflows

Regulators, litigation, and internal investigations demand data. Have a runbook.

**Typical scenarios:**

**Subpoena / regulatory request:** legal receives, evaluates scope, coordinates with engineering to produce data within legal deadline (often 14-30 days).

**Data Subject Access Request (GDPR):** user requests their data. 30-day deadline. Automated tooling ideally produces a package.

**Security incident forensics:** investigator needs full trace of specific user's activity during incident window.

**Regulatory audit:** auditor samples random events, requests full context, evaluates policy compliance.

**Toolkit:**

- **Audit event query interface** — search by user, date range, event type, feature
- **Content retrieval workflow** — fetch plaintext for specific event IDs
- **Data package export** — assemble into regulator-friendly format (JSON, PDF report)
- **Chain-of-custody log** — every access to audit data during investigation is itself logged

**Test the runbook quarterly.** Real incidents come with time pressure.

---

## Files In This Folder

| File | Concept |
|---|---|
| [`audit_event_schema.py`](audit_event_schema.py) | Schema definition + validation for audit events |
| [`content_and_metadata_split.py`](content_and_metadata_split.py) | Separate storage for content vs audit metadata |
| [`tamper_evident_storage.py`](tamper_evident_storage.py) | WORM + hash chain + external signing patterns |
| [`retention_and_erasure.py`](retention_and_erasure.py) | Retention policy engine + right-to-erasure processor |
| [`legal_hold.py`](legal_hold.py) | Legal hold registry + deletion gating |
| [`siem_integration.py`](siem_integration.py) | Splunk / Datadog / Sentinel export patterns |
| [`anomaly_detection.py`](anomaly_detection.py) | AI-specific anomaly signals and response |
| [`discovery_workflow.py`](discovery_workflow.py) | Regulatory disclosure and DSAR fulfillment |

---

## The Staff Interview Question

*"An auditor wants a full record of user Alice's LLM interactions with your system last month. What can you produce, and how quickly?"*

**The wrong answer:** "We have logs in Datadog."

**The right answer:**
*"Full disclosure package within 24 hours. Our audit log is a separate system from observability — immutable, tamper-evident storage with cryptographic hash chain and WORM guarantees, retained 7 years, stored in the user's residency region. Every LLM call emits a structured audit event with identity chain, request metadata (including hashes of user content), processing details (model, region, cost, latency), response metadata, policy evaluation results, and integrity signatures. For Alice's month, I'd query the audit log by user_id and date range, retrieve every event, and cross-reference with the content archive to fetch plaintext prompts and responses for the events. Because content archive access is logged separately and requires legal review, that step is gated but scriptable. Output package includes the raw audit events as JSON, human-readable summary of the interactions, plaintext content correlated to events, retrieved document IDs and ACL check results per event, tool invocations, guardrail flags, and any anomaly alerts triggered during the period. Chain-of-custody log tracks every step of the export process. We can produce it in the auditor's preferred format — JSON for machine ingestion, PDF report for human review, or exported to a review platform. Timeline: 24 hours for a single-user month, up to 2 weeks for large-scale disclosure (thousands of users, GB-scale content). We run quarterly tabletop exercises specifically testing this workflow so it's not the first time we've done it under real pressure."*

That's a principal-level answer.

---

*Previous: [← Data Residency & Sovereignty](../04_data_residency_and_sovereignty/README.md) · Return to [folder README](../README.md)*
