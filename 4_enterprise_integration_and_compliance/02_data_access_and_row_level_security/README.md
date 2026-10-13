# 🔒 Data Access & Row-Level Security — The SharePoint Problem, Solved

> *"We ingested the entire SharePoint into the vector store."*
>
> *"With what permissions?"*
>
> *"...it was open to us at ingestion time."*
>
> *"So the model can now retrieve anything anyone in the company can read anywhere."*
>
> *"...yes."*

This section is the highest-leverage topic in this entire folder.

Vector stores don't understand permissions. Retrieval is similarity, not authorization. Which means: if your permission model isn't baked in at the retrieval layer, your enterprise RAG is a permission time bomb.

Every quarter, a Fortune 500 discovers that their AI assistant surfaced a document to someone who shouldn't have seen it. Every one of those incidents was preventable with the patterns in this section.

---

## The Failure Mode

**How every enterprise RAG leaks:**

1. Ingestion pipeline crawls SharePoint / Google Drive / Confluence with admin credentials
2. Documents flow into embeddings, then into a shared vector index with `tenant_id` metadata
3. At query time, retrieval filters by `tenant_id` but not by user-level ACLs
4. User Bob queries "compensation planning" — retrieval returns Alice's confidential HR doc because it's semantically similar
5. LLM synthesizes an answer citing content Bob shouldn't have access to
6. Bob screenshots. Bob's manager sees. Legal gets involved.

**The failure isn't the LLM.** The LLM did its job. The failure is that the retrieval layer surfaced a document without checking whether *this specific user* has access to *this specific document*.

**In a normal database this doesn't happen.** Postgres has row-level security. SharePoint has ACLs. Google Drive has sharing permissions. The source systems know.

**The RAG index throws that away.** By default.

**Your job is to preserve it.**

---

## The Four Layers of Access Enforcement

Every enterprise RAG needs authorization at four layers. Skip any and you have a leak.

### Layer 1: Ingestion Filtering

Only embed content the AI feature is *allowed* to embed.

**Not:** "we have API access, therefore we can embed."
**But:** "for this tenant, this AI feature, this data classification — we can embed these documents."

**Practical:** ingestion pipeline takes as input a tenant configuration that specifies:
- Which source systems are in scope (SharePoint site X, GDrive folder Y, DB schema Z)
- Which data classifications are allowed (public, internal, confidential — restricted is blocked)
- Which document types are excluded (payroll docs, medical records unless HIPAA-covered feature)
- Which time ranges are in scope (last 2 years, not the 20-year archive)

If a document doesn't match this filter, it doesn't enter the index. Ever.

### Layer 2: Permission Capture at Ingestion

For every document that *does* enter the index, capture the source-system permissions as index metadata.

**Data model:**
```
document {
  id: str
  tenant_id: str
  content_embedding: vector
  source_system: "sharepoint" | "gdrive" | "confluence" | ...
  source_id: str  # ID in the source system
  # PERMISSION CAPTURE
  visibility: "public" | "internal" | "team" | "individual"
  authorized_users: [user_id, ...]
  authorized_groups: [group_id, ...]
  authorized_roles: [role, ...]
  authorized_departments: [dept, ...]
  classification: "public" | "internal" | "confidential" | "restricted"
  # PROVENANCE
  ingested_at: timestamp
  source_updated_at: timestamp
  acl_synced_at: timestamp  # when did we last check ACLs?
}
```

The permissions are captured as they exist in the source system at ingestion time. This is the seed for retrieval-time enforcement.

### Layer 3: Retrieval-Time Enforcement (The Critical Layer)

Every retrieval query includes the user's identity context and filters based on the document metadata.

**The wrong pattern — post-filter:**
```python
# BAD: retrieve first, filter after
results = vector_db.search(query_embedding, top_k=10)
authorized = [r for r in results if user_can_access(user, r)]
return authorized[:5]  # may return fewer than requested
```

This has two problems:
- If most top-10 results are unauthorized, you return fewer or empty results silently — UX degrades and users escalate
- You paid to retrieve documents you can't use — cost and index load
- Race condition: user permissions changed between retrieval and filter

**The right pattern — pre-filter:**
```python
# GOOD: filter during the search
user_context = get_user_context(user_id)  # groups, department, role, etc.

results = vector_db.search(
    query_embedding=query_embedding,
    top_k=5,
    filter={
        "tenant_id": user_context.tenant_id,
        "$or": [
            {"visibility": "public"},
            {"visibility": "internal", "tenant_id": user_context.tenant_id},
            {"authorized_users": {"$contains": user_id}},
            {"authorized_groups": {"$in": user_context.groups}},
            {"authorized_departments": {"$in": [user_context.department]}},
        ],
        "classification": {"$lte": user_context.max_classification_level},
    }
)
```

**Requires filter-aware ANN.** Pinecone, Qdrant, Weaviate, Milvus support this. Naive HNSW with post-filter does not.

**Performance note:** filter-aware search on a large index with a highly selective filter can degrade to near-linear scan. For high-cardinality filters (thousands of authorized groups), use hybrid indexing: partition by tenant_id first, then filter within.

### Layer 4: Post-Retrieval Sanitization

Even with pre-filter, do one final check on the fetched results before passing to the LLM:

**Verify:**
- All returned documents match user's current permissions (not just at retrieval time — right now)
- No document exceeds user's max classification
- Documents haven't been quarantined since retrieval (DLP flag, legal hold)

**Emit:** retrieval audit event with `(user_id, query_hash, returned_doc_ids, filter_applied, permission_check_result)`.

**Alert on:** any document that would fail the post-check that got past the pre-filter. This is a bug — investigate immediately.

---

## The Permission Sync Problem

Source-system permissions change constantly:
- Alice leaves the team → she no longer has access to the team's Confluence
- A document is reclassified from "internal" to "confidential"
- A group is renamed or restructured

**Your vector index doesn't automatically know.**

**The failure mode:** ex-employee Alice queries her old team's docs a week after leaving. Her queries are authenticated (SSO didn't fully propagate), her permission metadata in your index is stale, she gets her old docs.

**The mitigation patterns:**

### Pattern A: Real-time ACL check at retrieval

Every retrieval calls the source system to verify the user still has access to each candidate doc.

**Pros:** always current.
**Cons:** massive latency and cost; source system rate limits; only works if source systems have queryable ACL APIs.

**When to use:** high-stakes, low-volume features (legal, compliance).

### Pattern B: Periodic ACL resync

Background job resyncs document permissions from source systems every N minutes/hours.

**Pros:** bounded staleness; predictable cost.
**Cons:** window of vulnerability; complex reconciliation for permission changes.

**Best practice:** 15-minute resync for standard, 5-minute for sensitive tenants, real-time invalidation on webhook events from source systems.

### Pattern C: Event-driven invalidation

Subscribe to source-system change events (webhooks, change feeds, log tailers) and invalidate index entries immediately.

**Pros:** near-real-time; efficient.
**Cons:** requires source system to emit events; harder for legacy systems.

**When to use:** modern SaaS integrations (Slack, Notion, Google Workspace all emit change events).

### The recommended hybrid

- **Event-driven for supported sources** (immediate invalidation on delete, permission change)
- **Periodic resync as safety net** (every 15 min, reconciles missed events)
- **Real-time verification for the most sensitive documents** (marked with a flag, verified per retrieval)

Add: **explicit user-side re-auth requirement** for accessing anything more than 24 hours old — protects against the ex-employee case while SSO/SCIM catches up.

---

## Permission-Aware Embeddings

**A frontier pattern.** Instead of one shared vector space, train embeddings that also encode permission topology.

**The idea:** documents that Alice can access embed to "closer" locations in her personal semantic space than documents she can't. Retrieval naturally surfaces authorized content.

**Reality in 2026:** promising research (Reimers 2024ish — verify citation), not yet standard practice. Most enterprise RAG relies on metadata filtering, not embedding-level permission encoding.

**When you'd consider it:** ultra-high-scale deployments where metadata filtering becomes expensive, or where permission relationships are extremely complex (e.g., legal firm with case-by-case attorney-client privilege).

For most enterprises today: **stick with metadata filtering.** It's understood, auditable, and sufficient.

---

## Handling Sensitive Data In Prompts

Permission-aware retrieval keeps unauthorized documents out of the retrieved context. But sensitive data can still enter the LLM call in other ways:

**User's own query:** "Summarize John's medical history for me" — user has a legitimate reason but the query itself contains PHI.

**Injected via previous turn:** conversation history containing sensitive fields.

**Tool result contamination:** a tool returns a full customer record including PII.

**Mitigations:**

- **Input DLP:** scan user messages for PII/PHI/PCI patterns. Redact or block per policy.
- **Output DLP:** scan LLM outputs before returning to user. Prevent LLM from including sensitive fields it saw.
- **Structured tool outputs:** tools return only the fields the LLM needs, not the full record.
- **Prompt-level redaction:** replace `SSN=123-45-6789` with `SSN=<REDACTED>` before the model sees it.
- **Sensitive context flags:** if the context includes PHI, mark the response for enhanced audit and shorter retention.

**Enterprise DLP integrations:** Symantec DLP, Forcepoint, Microsoft Purview, Google Cloud DLP. Most have APIs you can call from the BFF.

---

## Field-Level and Cell-Level Security

Some data isn't row-scoped — it's field-scoped or cell-scoped.

**Field-level example:** the "salary" column of the employees table is visible only to HR and the employee themselves. Retrieval of an employee record for a non-HR user should return the record *without* the salary field.

**Cell-level example:** in a shared spreadsheet, specific cells (formulas, sensitive numbers) are visible only to certain users.

**How this hits AI features:**

- **Structured data RAG (querying a DB via LLM):** LLM sees the table schema — must not see restricted columns
- **Document parsing:** if a Word document has permission-scoped comments or tracked changes, those must be filtered before embedding
- **Spreadsheet ingestion:** cell-level permissions must be respected

**The pattern:** ingestion pipeline knows the field/cell permission model of the source and either:
- Redacts the fields at embedding time (per user or per role — creates multiple embedding variants)
- Attaches field-level metadata so retrieval can filter fields from the returned content

Redaction is safer. Attaching metadata is more efficient. Choose based on scale and sensitivity.

---

## The Attorney-Client, Doctor-Patient Cases

Some permission structures don't fit standard ACLs.

**Attorney-client privilege:** documents shared between an attorney and a specific client are protected from other clients (even if both are clients of the same firm) and from opposing counsel.

**Doctor-patient confidentiality:** patient records are visible to their care team but not to unrelated clinicians.

**Bank-customer confidentiality:** customer financial data visible to their relationship manager and specific supporting roles.

**These require:**
- Relationship graphs (who is whose client, patient, customer)
- Time-bounded access (attorney can see docs from period they were engaged)
- Purpose limitation (data usable for care but not marketing)
- Split-brain retrieval (same firm, different clients — must not cross-contaminate)

**Practical pattern:** treat each relationship as a "sub-tenant." Documents are scoped not to the firm-tenant but to the specific relationship. Retrieval requires (firm, relationship_id, user_id) all three matching.

**This is where enterprise AI gets genuinely hard.** Off-the-shelf RAG platforms rarely support this natively — you build it.

---

## Files In This Folder

| File | Concept |
|---|---|
| [`ingestion_filtering.py`](ingestion_filtering.py) | Tenant-scoped ingestion with data classification enforcement |
| [`permission_capture.py`](permission_capture.py) | Extracting ACLs from SharePoint, GDrive, Confluence at ingestion |
| [`retrieval_pre_filter.py`](retrieval_pre_filter.py) | Filter-aware vector search with tenant + ACL predicates |
| [`acl_sync_patterns.py`](acl_sync_patterns.py) | Event-driven + periodic resync + real-time verification |
| [`field_level_security.py`](field_level_security.py) | Column and cell-level permissions in structured data RAG |
| [`relationship_based_access.py`](relationship_based_access.py) | Attorney-client and doctor-patient permission graphs |

---

## The Staff Interview Question

*"You're building a legal AI assistant that searches across firm documents. Different attorneys have different clients. Different clients cannot see each other's documents. Some documents are subject to attorney-client privilege. How do you handle this?"*

**The wrong answer:** "Tag each document with client_id and filter."

**The right answer:**
*"Multi-layered access control that mirrors the firm's privilege structure. Ingestion filtering — the pipeline knows which matter documents to ingest per relationship, respecting the firm's document management system permissions. Permission capture — for each document, store the full ACL including relationship_id, attorney assignments, client identity, matter_id, and privilege classification. Retrieval pre-filter — every query must include (firm_id, requesting_attorney_id, active_matter_ids) and the vector search filters based on: document belongs to a matter where this attorney is engaged, client_id matches allowed clients for this attorney, and privilege_level is compatible. Post-retrieval verification — even after pre-filter, re-check that the current attorney-matter engagement is still active before passing to the LLM. Real-time ACL check on documents marked as privileged — cannot risk staleness there. Retrieval audit — every query logs the full permission evaluation for later privilege log review. And critically — sub-tenanting the vector store: instead of one firm-tenant index, we have one namespace per matter. Prevents any query from a wrong matter from ever seeing another matter's documents even if permission logic has a bug. Belt and suspenders. Now for the LLM call itself — model provider gets a scrubbed prompt with only the retrieved matter documents. Prompt cache is per-matter to prevent cross-matter leakage through provider-side caching. Response audit includes matter_id for privilege log. That's the architecture."*

That answer wins a principal-level interview.

---

*Previous: [← Identity & Access Control](../01_identity_and_access_control/README.md) · Return to [folder README](../README.md) · Next: [Compliance Frameworks →](../03_compliance_frameworks/README.md)*
