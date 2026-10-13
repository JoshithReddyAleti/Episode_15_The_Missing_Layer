# 📋 Compliance Frameworks — Specifications, Not Checkboxes

> *"Are you SOC 2 compliant?"*
>
> *"We're SOC 2 Type II with our AI features in scope, audit dated within the last 12 months. Which specific controls do you want to dive into?"*
>
> — the sentence that unlocks enterprise procurement

This section is the honest map of the compliance landscape as it applies to LLM applications, and how each framework translates to concrete architectural controls.

Not "here's what SOC 2 is" — you can Google that. **What controls does SOC 2 require of an LLM system, and how do you satisfy them at the architecture level?** That's this section.

---

## The Framework Landscape

Every enterprise LLM app operates under multiple overlapping frameworks depending on customer, vertical, and geography.

| Framework | Scope | Region | Who requires it |
|---|---|---|---|
| **SOC 2 Type II** | Security, availability, confidentiality controls | Global (US origin) | Every enterprise B2B SaaS customer |
| **ISO 27001 / 27017 / 27018** | Information security management | Global | European + APAC enterprises especially |
| **HIPAA** | Protected Health Information | US healthcare | Any US healthcare or health-adjacent customer |
| **GDPR** | Personal data of EU residents | EU (extraterritorial) | Any customer with EU users |
| **CCPA / CPRA** | Personal data of California residents | US | Any customer with CA users (most large US customers) |
| **PCI-DSS** | Payment card data | Global | Any customer processing card data |
| **FedRAMP** | US Federal government workloads | US | US government + contractors |
| **HITRUST CSF** | Comprehensive healthcare + finance | US primarily | Health payers, some financial |
| **EU AI Act** | High-risk AI systems | EU | Any customer deploying regulated AI in EU |
| **NYC Local Law 144** | Automated employment decisions | NYC | HR / recruiting features in NYC |
| **Colorado AI Act (SB24-205)** | Algorithmic discrimination in consequential decisions | Colorado | Consequential decision-making AI in CO |
| **SOX** | Financial reporting controls | US public companies | Any AI touching financial reporting |
| **GLBA** | Financial customer information | US financial services | US banks, credit unions, insurers |

**Not all apply to every product.** But if you're selling to Fortune 500, expect SOC 2 + ISO 27001 + GDPR baseline, with vertical-specific overlays.

---

## SOC 2 — The Table Stakes

Nearly every US enterprise buyer requires SOC 2 Type II. The Type II means the auditor observed controls operating over time (typically 6-12 months), not just at a point in time (Type I).

**The Trust Services Criteria that matter for AI:**

### CC6.1 — Logical Access Controls

The system implements logical access controls to prevent unauthorized access.

**For LLM systems, means:**
- SSO with MFA for all users (see Section 01)
- RBAC/ABAC policies for AI feature access
- Least privilege for service accounts calling LLM providers
- Regular access reviews (quarterly minimum, annually documented)
- Removal of access within defined SLA when users leave

**How auditors test:** they'll ask you to show them a user's access to AI features, then demonstrate revocation and confirm access ceases within your stated SLA.

### CC6.6 — Boundary Protection

External access is authenticated and authorized.

**For LLM systems, means:**
- API gateway with authentication in front of your BFF
- Rate limiting per user and per tenant
- Network segmentation isolating LLM inference from other workloads
- No direct internet exposure of internal services
- WAF rules covering common attacks (SQL injection, and increasingly, prompt injection patterns)

### CC6.7 — Data In Transit

Data in transmission is protected against unauthorized access.

**For LLM systems, means:**
- TLS 1.2+ for all client → server communication
- TLS 1.2+ for BFF → LLM provider (all major providers require this)
- Certificate pinning for high-security clients (mobile apps)
- Encrypted service mesh internally (mTLS)

### CC6.8 — Data At Rest

Data at rest is protected against unauthorized access.

**For LLM systems, means:**
- Encryption at rest for all data stores: Postgres, Redis, vector DB, object storage
- Customer-managed keys (CMK) for enterprise tenants (BYOK)
- Encryption of caches — semantic cache and prompt cache
- Encryption of session state and conversation history
- Encryption of audit logs

**The often-missed one:** LLM provider caches. If Anthropic caches your prompts server-side, are those encrypted at rest at Anthropic? Answer per your contract with them.

### CC7.2 — System Monitoring

The system monitors for security events and incidents.

**For LLM systems, means:**
- Audit logs of every LLM call with identity + input + output classification (Section 05)
- Anomaly detection — sudden cost spikes, unusual query patterns, permission escalations
- SIEM integration (Splunk, Datadog, Sentinel)
- 24/7 monitoring for critical services
- Automated alerts routed to on-call

### CC8.1 — Change Management

System changes are authorized, tested, and monitored.

**For LLM systems, means:**
- Prompt changes go through code review and staged rollout
- Model version changes require approval (especially for regulated features)
- Config changes are versioned and auditable
- Rollback procedures documented and tested
- Change advisory board for high-risk changes

**Under-appreciated for AI:** prompt engineering is code. Every prompt change is a system change. Track it in git, review it, deploy it through your change process.

### CC9.2 — Vendor Management

Vendors are assessed and monitored.

**For LLM systems, means:**
- LLM provider agreements reviewed by security and legal
- Vendor SOC 2 reports reviewed annually (OpenAI, Anthropic, Google all publish)
- Documented data flows between your system and each provider
- BAAs, DPAs, SCCs in place per requirement
- Incident response coordination with providers

---

## HIPAA — Protected Health Information

If your customer is in US healthcare or handles US PHI, HIPAA applies. Non-compliance risks are large fines and criminal liability in extreme cases.

### The rules that matter

**Privacy Rule (§ 164.500-534):** governs use and disclosure of PHI. Minimum necessary standard, patient rights (access, amendment, accounting of disclosures).

**Security Rule (§ 164.302-318):** administrative, physical, and technical safeguards for ePHI.

**Breach Notification Rule (§ 164.400-414):** disclosure obligations when PHI is compromised. 60-day notification to affected individuals; HHS notification; media notification for large breaches.

### The Business Associate Agreement (BAA)

If you handle PHI, you and every downstream vendor need a BAA. **Every.**

**Your LLM provider must have a BAA with you covering PHI processing.**

- **OpenAI:** BAA available on enterprise agreements
- **Anthropic:** BAA available on commercial agreements
- **Google Cloud (Gemini via Vertex AI):** BAA available under GCP BAA
- **AWS Bedrock:** BAA available under AWS BAA
- **Azure OpenAI:** BAA available under Microsoft BAA
- **DeepSeek, other Chinese providers:** BAA typically NOT available. Cannot use for PHI.

**The gotcha:** using a provider's "standard" API without a BAA to process PHI is a HIPAA violation *by you*, even if the provider is otherwise capable. The BAA is what makes them a covered business associate.

### Technical safeguards HIPAA requires

**§ 164.312(a)(1) — Access controls:** unique user ID, emergency access, automatic logoff, encryption/decryption. All the identity work in Section 01 applies.

**§ 164.312(b) — Audit controls:** hardware, software, and procedural mechanisms to record and examine access. Full audit trail per Section 05.

**§ 164.312(c)(1) — Integrity:** ePHI is not altered or destroyed in unauthorized manner. Requires tamper-evident storage for records; version control for documents.

**§ 164.312(d) — Person or entity authentication:** verify user identity. MFA required practically.

**§ 164.312(e)(1) — Transmission security:** integrity and encryption controls. TLS + secure inter-service.

*Note: exact citation numbers should be verified — Claude may hallucinate specific section numbers.*

### The minimum-necessary problem for LLM apps

HIPAA requires disclosing only the "minimum necessary" PHI for the purpose. LLM prompts often over-share.

**The failure mode:** to answer "what's this patient's next appointment," you pass the model the full patient record including diagnoses, medications, notes. That's more than minimum necessary.

**The mitigation:** structured tool outputs. LLM asks for specific fields via a tool call. Tool returns only requested fields. LLM never sees the full record.

---

## GDPR — Personal Data of EU Residents

Extraterritorial: applies to any org processing EU-resident data, regardless of where the org is based.

### The rights that create engineering work

**Right of access (Article 15):** users can request all their personal data. Must be provided within 30 days.

**Right to erasure / "right to be forgotten" (Article 17):** users can request deletion.

**Right to data portability (Article 20):** users can request their data in machine-readable format.

**Right to object (Article 21):** users can object to processing.

**Right not to be subject to automated decision-making (Article 22):** relevant when AI makes consequential decisions.

### What this means for LLM apps

**Erasure is the hard one.**

When a user requests erasure, you must delete their personal data from:
- Your primary database (obvious)
- Your session state (Redis)
- Your semantic cache (their queries, their responses)
- Your vector index (any embeddings of their content)
- Your audit logs (usually retained under legitimate interest — must show)
- Your LLM provider's cache (if you use provider-side prompt caching)
- Your LLM provider's training data (if you didn't opt out of training on your inputs)
- Any downstream systems that received the data

**Erasure workflow:**
1. Receive request through documented channel
2. Verify identity
3. Trigger deletion across all listed systems
4. Confirm completion to user within 30 days
5. Retain audit record of the erasure itself

**The gotcha:** if your LLM provider trained on your inputs and now the model has memorized user data, you cannot delete it from the model weights. This is why most providers offer training opt-out for enterprise, and why your DPA must document it.

### Lawful basis for processing

GDPR requires a lawful basis for processing personal data. For AI features, common bases:

- **Consent (Art 6(1)(a)):** user explicitly consented. Must be freely given, specific, informed.
- **Contract (Art 6(1)(b)):** processing necessary to perform the contract.
- **Legitimate interest (Art 6(1)(f)):** balanced against user rights.

**For LLM features specifically:** typically "contract" (the user is asking the AI to help) or "legitimate interest" (fraud detection, improving service). Consent is needed for optional AI enrichment features.

**Automated decision-making (Art 22):** if AI makes decisions with legal or similarly significant effects on users (hiring, lending, insurance underwriting), users have the right to human review. Design for it.

### DPA and SCCs

**Data Processing Agreement (DPA):** contract between you (controller or processor) and your LLM provider (sub-processor). Covers what data flows, for what purpose, with what safeguards.

**Standard Contractual Clauses (SCCs):** required for transfer of EU personal data to countries without an adequacy decision. The US has DPF (Data Privacy Framework) — some US providers rely on it, but its longevity is uncertain (Schrems II legacy). SCCs remain the safer path.

---

## PCI-DSS — Payment Card Data

If cardholder data touches your LLM feature, you're in scope for PCI. Most teams should aggressively **keep card data out** of LLM flows.

**The right pattern:** tokenize card data at the entry point. Never pass raw PAN (primary account number), CVV, or expiration to the LLM. If the LLM needs to "check the card status," it calls a tool with a token; the tool queries the payment system.

**If you must process card data through AI (rare):** you're in full PCI scope. Requires network segmentation (PCI zone), quarterly ASV scans, annual QSA audit, encrypted storage, key management program.

**Nearly every LLM app should keep this out of scope by design.**

---

## FedRAMP — US Federal Deployments

US federal customers require FedRAMP authorization for cloud services. Two paths:

**FedRAMP Moderate:** most agency workloads. ~325 controls.

**FedRAMP High:** high-impact systems. ~421 controls. Difficult.

**For LLM services:**
- **AWS Bedrock GovCloud:** FedRAMP High authorized. Bedrock in GovCloud regions.
- **Azure OpenAI Government:** FedRAMP High authorized. Azure Government cloud.
- **Google Cloud (Assured Workloads):** FedRAMP High for specific services.
- **OpenAI direct, Anthropic direct:** typically not FedRAMP authorized. Route through Bedrock or Azure.

**The pattern:** if you're building for federal, deploy in GovCloud/Azure Gov, use only FedRAMP-authorized LLM services, inherit their controls, and get your own FedRAMP authorization for your service.

---

## EU AI Act — The New Layer

Applied progressively 2025-2027. Categorizes AI systems by risk.

**Prohibited (banned):** social scoring, real-time biometric surveillance in public (with exceptions), manipulative AI.

**High-risk:** hiring, credit, education, law enforcement, critical infrastructure, medical devices. Requires:
- Risk management system
- Data governance and quality
- Technical documentation
- Record-keeping
- Transparency to users
- Human oversight
- Accuracy, robustness, cybersecurity
- Post-market monitoring

**Limited risk (chatbots, generative AI):** transparency obligations. Users must know they're interacting with AI. AI-generated content must be labeled.

**Minimal risk:** most AI. No specific obligations.

**If you're building high-risk AI in EU:** significant compliance program required. Similar cost profile to HIPAA.

---

## US State-Level AI Laws

Fragmenting quickly. As of 2026:

**Colorado AI Act (SB24-205):** effective Feb 2026. Consequential decision-making AI must implement algorithmic discrimination prevention.

**NYC Local Law 144:** employers using automated employment decision tools must conduct annual bias audits and provide notice.

**Illinois BIPA:** biometric data (voice, face) requires informed consent. AI voice features fall under this.

**California SB 942 (AI Transparency):** requires disclosure of AI-generated content on public-facing platforms.

**Multiple states pending:** patchwork continuing to evolve.

**Practical approach:** implement the union of requirements. Bias auditing, disclosure, consent, opt-out. Do it once, comply everywhere.

---

## The Compliance Control Matrix

For any enterprise feature, produce a matrix mapping frameworks to controls to your implementation:

| Framework | Control | Requirement | Implementation | Evidence |
|---|---|---|---|---|
| SOC 2 | CC6.1 | Access controls | SSO + RBAC in BFF | Auth logs, access review reports |
| SOC 2 | CC7.2 | Monitoring | SIEM ingestion of AI events | Alert configurations, response records |
| HIPAA | 164.312(a) | Access | Section 01 + BAA with provider | Signed BAA, access logs |
| HIPAA | 164.312(b) | Audit | Section 05 audit trail | 7-year audit log with tamper protection |
| GDPR | Art 17 | Erasure | Multi-system deletion workflow | Erasure runbook + test evidence |
| GDPR | Art 22 | Automated decisions | Human review path for consequential outcomes | UX + policy documentation |

Every framework applicable to your customer, every control it requires, how your architecture satisfies it, and what evidence you can produce.

**This is what enterprise procurement asks for.** Have it ready.

---

## Files In This Folder

| File | Concept |
|---|---|
| [`soc2_controls_mapping.py`](soc2_controls_mapping.py) | SOC 2 CC controls mapped to LLM architecture patterns |
| [`hipaa_baa_and_safeguards.py`](hipaa_baa_and_safeguards.py) | HIPAA requirements including provider BAA landscape |
| [`gdpr_rights_workflows.py`](gdpr_rights_workflows.py) | Erasure, access, portability implementation patterns |
| [`pci_dss_and_tokenization.py`](pci_dss_and_tokenization.py) | Keeping card data out of LLM flows via tokenization |
| [`fedramp_and_govcloud.py`](fedramp_and_govcloud.py) | US federal deployment paths |
| [`eu_ai_act_risk_tiers.py`](eu_ai_act_risk_tiers.py) | EU AI Act tier classification and obligations |

---

## The Staff Interview Question

*"A hospital wants to use your AI. Walk me through your HIPAA story."*

**The wrong answer:** "We're SOC 2 compliant."

**The right answer:**
*"HIPAA requires a specific set of things. First — BAA. We have BAAs available with our LLM providers — Anthropic, Bedrock, and Azure OpenAI on our supported list. We sign a BAA with the hospital as the covered entity, and we ensure the LLM provider BAA is in the chain. Second — technical safeguards. § 164.312 requires access controls with unique user IDs and MFA, audit controls capturing all PHI access, integrity controls preventing unauthorized alteration, transmission security via TLS, and encryption at rest. Our architecture satisfies each: SSO federation with the hospital's IdP, per-user identity in every LLM call and every retrieval event, immutable audit log with 7-year retention in tamper-evident storage, TLS 1.2+ everywhere and mTLS internally, encryption at rest for all data stores including caches. Third — minimum necessary. Our LLM prompts don't dump full patient records; structured tool calls fetch only fields the model needs. Fourth — Breach Notification. We have a documented 60-day notification workflow and 24-hour internal incident response. Fifth — the hospital gets a dedicated deployment posture: separate vector namespace, per-tenant encryption keys, no cross-tenant caching. Sixth — right-to-access and accounting of disclosures — we support HIPAA-compliant patient data requests. We can produce a full HIPAA compliance package including our vendor BAA chain, technical control documentation, breach runbook, and third-party HITRUST assessment if the hospital requires it. What specifically would you like to dig into?"*

That's the answer that closes a hospital deal.

---

*Previous: [← Data Access & RLS](../02_data_access_and_row_level_security/README.md) · Return to [folder README](../README.md) · Next: [Data Residency & Sovereignty →](../04_data_residency_and_sovereignty/README.md)*
