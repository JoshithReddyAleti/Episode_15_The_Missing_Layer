# 🎯 Interview Prep — Enterprise Integration & Compliance

Compliance questions differentiate senior from staff at MAANG cloud and enterprise-focused teams. This doc maps common questions to sections.

## The Universal Opener

For any "design enterprise AI feature" question:

*"Before we architect, let me establish the compliance context — who's the buyer, what data flows through, what regulatory frameworks apply. That determines identity architecture, data access controls, residency, audit posture, and provider selection. Design without those constraints upfront is guaranteed rework at procurement or first audit."*

## Question Bank

### "Design an AI feature for enterprise use."

**Lean on:** all sections.

**Structure:** identify buyer and data → identity/SSO story → data access enforcement → residency → audit → provider contract terms.

### "How do you handle SSO for enterprise?"

**Lean on:** Section 01.

**Key points:** SAML 2.0 for legacy, OIDC for modern, SCIM 2.0 for lifecycle, MFA at IdP, identity propagation as first-class through every layer.

### "How do you enforce data access in a RAG system?"

**Lean on:** Section 02.

**Four layers:** ingestion filtering, permission capture at ingest, retrieval pre-filter (not post), post-retrieval verification. Plus ACL sync patterns (event-driven + periodic + real-time for sensitive).

### "What's the SharePoint problem?"

**Lean on:** Section 02.

**Answer:** SharePoint has hierarchical permissions with decades of accumulated ACL complexity. RAG ingestion typically crawls with admin credentials, embedding documents without preserving user-level permissions. Retrieval then returns documents based on similarity, not authorization — resulting in cross-team data leakage. Solution: capture ACLs at ingestion, enforce at retrieval as pre-filter.

### "Walk me through your HIPAA compliance."

**Lean on:** Section 03.

**Structure:** BAA chain (customer + you + LLM provider), technical safeguards per 164.312 (access, audit, integrity, transmission, encryption), minimum necessary (structured tool outputs not full records), Breach Notification runbook, per-tenant isolation for PHI.

### "How does GDPR affect an AI product?"

**Lean on:** Section 03.

**Key points:** rights (access, erasure, portability, objection, automated decision-making), lawful basis, DPA with providers, SCCs for cross-border, erasure workflow across all storage systems including caches and vector stores.

### "How do you handle data residency for EU customers?"

**Lean on:** Section 04.

**Structure:** regional stack topology, provider selection per region (Bedrock EU, Azure OpenAI EU, Anthropic EU), tenant residency policy enforcement, observability regional too, automated residency testing.

### "What's the difference between residency and sovereignty?"

**Lean on:** Section 04.

**Answer:** residency is physical location. Sovereignty is legal jurisdiction — data subject only to region X's laws and immune from foreign government access. Schrems II tension: EU data in US-operated EU-region servers may lack sovereignty due to US Cloud Act. True sovereignty requires sovereign cloud offerings (GCP Sovereign Controls, upcoming AWS European Sovereign Cloud), local operator partnerships, or self-hosted.

### "What's your audit story?"

**Lean on:** Section 05.

**Structure:** separate audit log from observability, immutable storage (WORM + hash chain), content/metadata split, retention per framework, right-to-erasure workflow, SIEM integration, discovery workflow tested quarterly.

### "Can you produce full LLM interaction records for user X during period Y?"

**Lean on:** Section 05.

**Answer:** 24 hours for a single user month. Query audit log by user_id + date range, cross-reference with content archive for plaintext (content access itself audited), package as JSON + PDF, chain-of-custody log.

### "How do you handle the right to be forgotten in an AI system?"

**Lean on:** Sections 03 + 05.

**Multi-system erasure workflow:** primary DB, session cache, semantic cache, vector store embeddings, backups, provider prompt cache, observability metrics, content archive. Audit log retained (legitimate interest). Provider training opt-out prevents unrecoverable memorization in weights. Documented runbook + 30-day SLA + post-erasure verification.

### "Design an AI assistant for a global healthcare company."

**Full-stack question. Lean on all sections.**

Key points: multi-region deployment, HIPAA + GDPR + local variations, BAA with providers, patient-relationship-graph access control, per-region residency, WORM audit with 7-year retention, PHI content archive with tight retention and access, EU AI Act if high-risk use case.

## The Framework To Remember

Every enterprise/compliance question maps to:

1. **Identity & access** — SSO federation, RBAC/ABAC, identity propagation
2. **Data access enforcement** — permission-aware retrieval, ACL preservation
3. **Compliance frameworks** — SOC 2 / HIPAA / GDPR / PCI / FedRAMP / AI Act mapped to controls
4. **Residency & sovereignty** — regional stacks, provider selection, transfer instruments
5. **Audit & disclosure** — immutable logs, retention, erasure, legal hold, discovery workflows

Show that you know these five and you're an enterprise-ready architect.
