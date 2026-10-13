# 📊 Compliance Control Matrix Template

Drop this into your compliance documentation. Fill it in per your architecture.

## How To Use

For each enterprise feature that touches customer data or produces user-facing outputs, produce a matrix like this. Auditors and enterprise procurement teams request it directly.

## The Matrix

| Framework | Control | Requirement | Implementation | Evidence Location |
|---|---|---|---|---|
| **SOC 2 CC6.1** | Access Controls | Logical access controls limit access to authorized users | SSO federation via SAML/OIDC; RBAC and ABAC in BFF; quarterly access reviews; SLA-based deprovisioning | Access logs (audit system); access review reports (quarterly); SCIM lifecycle logs |
| **SOC 2 CC6.6** | Boundary Protection | External access is authenticated and authorized | API gateway with auth; WAF; rate limiting per user/tenant; network segmentation | Gateway config; WAF rules; network diagrams; segmentation attestations |
| **SOC 2 CC6.7** | Data In Transit | Data transmission is protected | TLS 1.2+ everywhere; mTLS internal service mesh; certificate pinning for mobile | TLS scan reports; service mesh config; mobile pin verification |
| **SOC 2 CC6.8** | Data At Rest | Encryption at rest | Encryption at rest on Postgres, Redis, vector DB, S3, caches; CMK for enterprise tenants | Encryption config; CMK usage logs |
| **SOC 2 CC7.2** | System Monitoring | Monitor for security events | Full audit trail; SIEM ingestion; anomaly detection; 24/7 on-call | Audit log samples; SIEM dashboards; alert response records |
| **SOC 2 CC8.1** | Change Management | Changes authorized and monitored | Prompt changes in git with review; model version approval workflow; staged rollout; rollback procedures | Change tickets; deployment logs; rollback test evidence |
| **SOC 2 CC9.2** | Vendor Management | Vendors assessed and monitored | LLM provider security reviews annually; DPA/BAA/SCC in place; sub-processor list maintained | Signed contracts; provider SOC 2 reports; risk assessments |
| **HIPAA 164.312(a)(1)** | Access Controls | Unique user ID, emergency access, automatic logoff, encryption | SSO with unique user_id; emergency access procedure; session timeouts; encryption everywhere | Identity system config; access procedures; timeout config; encryption evidence |
| **HIPAA 164.312(b)** | Audit Controls | Record and examine PHI access | Audit event on every PHI-touching operation; 7-year retention; immutable storage | Audit event samples; retention policy; storage attestation |
| **HIPAA 164.312(c)(1)** | Integrity | Prevent unauthorized alteration | Hash chain in audit log; version control on all documents; tamper-evident storage | Hash chain verification; version history samples |
| **HIPAA 164.312(d)** | Authentication | Verify user identity | MFA at IdP; MFA reverification for high-blast actions; device trust | MFA policy; step-up event logs |
| **HIPAA 164.312(e)(1)** | Transmission Security | Encrypt transmissions | TLS 1.2+; mTLS internal; end-to-end where applicable | Same as SOC 2 CC6.7 |
| **HIPAA BAA** | Covered vendor | BAA with LLM provider | Signed BAAs with Anthropic, AWS Bedrock, Azure OpenAI (whichever applies) | Signed BAAs on file |
| **GDPR Art 5** | Principles | Lawfulness, purpose limitation, data minimization | Documented lawful basis; purpose limitation in tenant config; minimum-necessary in prompts | DPA; purpose docs; prompt design review |
| **GDPR Art 15** | Right of Access | Provide user's data on request | DSAR workflow; 30-day SLA; automated export tooling | DSAR runbook; test evidence; export sample |
| **GDPR Art 17** | Right to Erasure | Delete on request | Multi-system erasure workflow; 30-day SLA; verification | Erasure runbook; test evidence |
| **GDPR Art 22** | Automated Decision | Human review for consequential automated decisions | Human review workflow; opt-out UI; documentation | UX evidence; policy docs |
| **GDPR Art 30** | Records of Processing | Maintain processing records | ROPA maintained; sub-processor list current | ROPA document; sub-processor page |
| **GDPR Art 32** | Security | Appropriate technical and organizational measures | Same evidence as SOC 2 security controls | Cross-reference SOC 2 |
| **GDPR Art 44-49** | Transfers | Cross-border with adequate safeguards | SCCs signed; TIA documented; adequacy relied on where applicable | SCC copies; TIA documents |
| **PCI-DSS** | Scope | Cardholder data | Tokenize at entry; card data never touches LLM | Data flow diagram; tokenization design |
| **FedRAMP Moderate** | (as applicable) | US federal controls | Deploy in GovCloud / Azure Gov; inherit provider FedRAMP | GovCloud architecture; ATO letter |
| **EU AI Act (high-risk)** | Risk management | Risk management system, technical documentation, human oversight, accuracy | Risk register; technical doc; human review paths; accuracy monitoring | Risk docs; AI system documentation; oversight evidence |

## Per-Framework Attestation Checklist

Before shipping to a regulated customer, produce and provide:

### SOC 2 Type II
- [ ] Report from qualified auditor
- [ ] Dated within last 12 months (or bridge letter for gap)
- [ ] Feature in scope
- [ ] Exceptions documented and remediated

### HIPAA
- [ ] Signed BAA with customer
- [ ] Signed BAAs with all sub-processors handling PHI
- [ ] Risk analysis and risk management plan
- [ ] Workforce training records
- [ ] Contingency plan / disaster recovery
- [ ] Breach Notification runbook

### GDPR
- [ ] DPA with customer
- [ ] Sub-processor list with change notification
- [ ] SCCs for cross-border
- [ ] Transfer Impact Assessment
- [ ] DPIA (Data Protection Impact Assessment) for high-risk processing
- [ ] Privacy Notice with AI disclosures
- [ ] DPO contact if required

### FedRAMP
- [ ] ATO (Authority to Operate) letter
- [ ] SSP (System Security Plan)
- [ ] Continuous monitoring evidence
- [ ] POA&M (Plan of Action & Milestones) if applicable

### ISO 27001
- [ ] Current certification
- [ ] Statement of Applicability
- [ ] Risk treatment plan

## Living Document

Update this matrix quarterly. Compliance is not a snapshot — it's a running program.
