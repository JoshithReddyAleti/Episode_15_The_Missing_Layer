# 🧭 Enterprise Integration & Compliance Decision Framework

Answer these before shipping any enterprise-tier feature.

## Step 1: Who Is The Buyer?

| Buyer | Compliance baseline |
|---|---|
| Startup, non-regulated | SOC 2 Type II sufficient |
| Enterprise B2B, non-regulated | SOC 2 Type II + ISO 27001 |
| Enterprise B2B, EU customers | + GDPR + regional deployment |
| US Healthcare | + HIPAA + BAA + specific technical safeguards |
| US Financial Services | + GLBA + SOX (if reporting flows) |
| US Government / Contractor | + FedRAMP Moderate or High + ITAR/EAR check |
| EU High-Risk AI use case | + EU AI Act obligations |
| Global consumer product | + CCPA + state AI laws + international patchwork |

## Step 2: What Data Flows Through The AI?

| Data type | Requirements |
|---|---|
| Public / marketing data | Standard controls |
| Internal / business confidential | Access controls, encryption, audit |
| Customer non-personal | + data residency |
| Personal data (any user) | + GDPR / CCPA rights workflows |
| PHI (US healthcare) | + BAA + HIPAA safeguards |
| PCI (card data) | + PCI-DSS scope OR tokenize out |
| Classified / ITAR | + FedRAMP + facility clearance |

## Step 3: Identity Architecture

- SSO federation (SAML for legacy IdPs, OIDC for modern) — non-negotiable for enterprise
- SCIM for user lifecycle — auditors check this
- RBAC for feature-level access + ABAC for data-level access
- Zero-trust: every LLM call re-evaluates policy
- Provider credentials: never a lifetime API key in env vars; use STS or sub-tenancy where available

## Step 4: Data Access Enforcement

- Ingestion filtering — only embed content the feature is authorized to embed
- Permission capture at ingestion — store source ACLs as index metadata
- Retrieval PRE-filter — filter during vector search, never post-filter only
- ACL sync: event-driven + periodic resync + real-time for sensitive
- Field-level and relationship-based access where required (legal, healthcare)

## Step 5: Residency

- Multi-region deployment with tenant-configurable home region
- Provider selection per region (see Section 04 matrix)
- Cross-border transfers under SCCs or adequacy
- Observability regional (Datadog EU for EU, etc.)
- Automated residency validation tests, quarterly

## Step 6: Audit Trail

- Separate audit log from observability platform
- Immutable storage (WORM) with cryptographic hash chain
- Content separate from metadata; hashes in audit, plaintext elsewhere with own access controls
- Retention per compliance requirement (7 years financial, varying)
- Right-to-erasure processor with multi-system deletion
- Legal hold registry gating deletions
- SIEM integration for real-time SecOps
- Discovery/DSAR workflow tested quarterly

## Step 7: Provider Contract Terms

Every LLM provider agreement must include:
- No training on your inputs (opt-out)
- BAA if PHI in scope
- DPA if EU personal data in scope
- SCCs if cross-border transfer
- Residency guarantees for regional deployments
- Sub-processor list disclosed and change notification
- Incident response coordination
- Audit rights (annual right to audit, or reliance on SOC 2 report)
- Data return / deletion on termination

## Combined Decision — Worked Example

**Enterprise B2B AI feature for global Fortune 500 healthcare customer:**

- Compliance baseline: SOC 2 Type II + ISO 27001 + HIPAA + GDPR + EU AI Act (if high-risk use)
- Data: PHI in scope → BAA with LLM provider mandatory, choose Bedrock (Anthropic on AWS with BAA) or Azure OpenAI
- Identity: SSO with hospital IdP, SCIM for provisioning, MFA mandatory, provider credentials via STS with per-tenant role
- Data access: patient-record retrieval with per-user care-team relationship graph, ABAC on all patient data, pre-filter always
- Residency: US-region for US hospital, EU-region for EU hospital, no cross-region
- Audit: WORM audit log with hash chain, 7-year retention, PHI in content archive with 90-day retention plus longer with legal hold, SIEM ingestion to hospital's Splunk
- Provider: Bedrock Anthropic in us-east-1 with BAA, no training on inputs, DPA and SCCs for EU sub-tenants

This is what shipping enterprise healthcare AI looks like.
