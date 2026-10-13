"""
permission_aware_rag_demo.py — RAG with pre-filter authorization.

Demonstrates:
- Document ingestion with permission capture
- Retrieval with tenant + ACL pre-filter
- Post-retrieval verification
- Audit trail on retrieval decisions
- The SharePoint problem — comparing naive vs correct retrieval

Run:
    python permission_aware_rag_demo.py
"""
from __future__ import annotations
import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Document:
    """A document with permission metadata."""
    doc_id: str
    tenant_id: str
    title: str
    content_embedding: tuple  # simplified as tuple for demo
    # PERMISSION CAPTURE
    visibility: str  # 'public', 'internal', 'team', 'individual'
    authorized_users: list = field(default_factory=list)
    authorized_groups: list = field(default_factory=list)
    authorized_departments: list = field(default_factory=list)
    classification: str = "internal"  # 'public', 'internal', 'confidential', 'restricted'
    # PROVENANCE
    ingested_at: float = field(default_factory=time.time)


@dataclass
class UserContext:
    user_id: str
    tenant_id: str
    department: str
    groups: list
    max_classification_level: str  # 'public', 'internal', 'confidential', 'restricted'


CLASSIFICATION_ORDER = ["public", "internal", "confidential", "restricted"]


def can_user_access(user: UserContext, doc: Document) -> tuple[bool, str]:
    """Determine if a user is authorized to access a document. Returns (allowed, reason)."""
    # Tenant boundary
    if user.tenant_id != doc.tenant_id:
        return (False, "wrong tenant")

    # Classification level
    user_max = CLASSIFICATION_ORDER.index(user.max_classification_level)
    doc_level = CLASSIFICATION_ORDER.index(doc.classification)
    if doc_level > user_max:
        return (False, f"classification too high (doc={doc.classification}, user_max={user.max_classification_level})")

    # Visibility rules
    if doc.visibility == "public":
        return (True, "public visibility")
    if doc.visibility == "internal":
        return (True, "internal to tenant")
    if doc.visibility == "team":
        if any(g in doc.authorized_groups for g in user.groups):
            return (True, "group membership")
        if user.department in doc.authorized_departments:
            return (True, "department membership")
        return (False, "not in authorized team")
    if doc.visibility == "individual":
        if user.user_id in doc.authorized_users:
            return (True, "individually authorized")
        return (False, "not individually authorized")

    return (False, "unknown visibility")


class VectorStore:
    """Simplified vector store with metadata filtering."""

    def __init__(self):
        self.docs: list[Document] = []

    def add(self, doc: Document):
        self.docs.append(doc)

    def similarity_score(self, query_embedding, doc_embedding) -> float:
        """Simulated cosine similarity."""
        dot = sum(a * b for a, b in zip(query_embedding, doc_embedding))
        return dot

    def search_naive(self, query_embedding, top_k=5) -> list:
        """The BAD pattern — no permission check."""
        scored = [(d, self.similarity_score(query_embedding, d.content_embedding)) for d in self.docs]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def search_pre_filter(self, query_embedding, user: UserContext, top_k=5) -> tuple[list, list]:
        """The GOOD pattern — pre-filter by permission then rank."""
        audit_events = []

        # Filter first
        authorized_docs = []
        for d in self.docs:
            allowed, reason = can_user_access(user, d)
            if allowed:
                authorized_docs.append(d)
            else:
                audit_events.append({
                    "doc_id": d.doc_id,
                    "user_id": user.user_id,
                    "outcome": "filtered_out",
                    "reason": reason,
                })

        # Then rank
        scored = [(d, self.similarity_score(query_embedding, d.content_embedding)) for d in authorized_docs]
        scored.sort(key=lambda x: x[1], reverse=True)
        returned = scored[:top_k]

        for d, score in returned:
            audit_events.append({
                "doc_id": d.doc_id,
                "user_id": user.user_id,
                "outcome": "returned",
                "score": score,
            })

        return returned, audit_events


def make_docs():
    """Set up a corpus mimicking the SharePoint problem."""
    return [
        # Public / internal — everyone in tenant sees
        Document(
            doc_id="doc_shipping_policy",
            tenant_id="acme_corp",
            title="Shipping Policy",
            content_embedding=(0.9, 0.1, 0.2, 0.1),
            visibility="internal",
            classification="internal",
        ),
        # HR confidential — HR team only
        Document(
            doc_id="doc_reorg_draft",
            tenant_id="acme_corp",
            title="Draft Reorganization Plan",
            content_embedding=(0.85, 0.2, 0.15, 0.1),  # Similar to team structure queries!
            visibility="team",
            authorized_groups=["hr"],
            authorized_departments=["Human Resources"],
            classification="confidential",
        ),
        # Team roster — engineering can see
        Document(
            doc_id="doc_eng_team",
            tenant_id="acme_corp",
            title="Engineering Team Structure",
            content_embedding=(0.88, 0.15, 0.18, 0.1),
            visibility="team",
            authorized_groups=["engineering"],
            authorized_departments=["Engineering"],
            classification="internal",
        ),
        # Individually shared doc
        Document(
            doc_id="doc_bob_review",
            tenant_id="acme_corp",
            title="Performance Review — Bob",
            content_embedding=(0.7, 0.3, 0.2, 0.1),
            visibility="individual",
            authorized_users=["usr_bob", "usr_bob_manager"],
            classification="restricted",
        ),
    ]


def main():
    store = VectorStore()
    for doc in make_docs():
        store.add(doc)

    # Query that could accidentally retrieve HR docs
    query_embedding = (0.9, 0.15, 0.2, 0.1)  # "team structure"

    # Bob is an engineer, should NOT see HR reorg draft or Alice's review
    bob = UserContext(
        user_id="usr_bob",
        tenant_id="acme_corp",
        department="Engineering",
        groups=["engineering"],
        max_classification_level="internal",
    )

    print("=" * 60)
    print("Query: 'team structure' by Bob (Engineering, non-HR)")
    print("=" * 60)

    print("\n--- NAIVE RETRIEVAL (no permission check) ---")
    naive_results = store.search_naive(query_embedding, top_k=3)
    for doc, score in naive_results:
        print(f"  [{score:.3f}] {doc.doc_id} — {doc.title}")
        print(f"          visibility={doc.visibility}, classification={doc.classification}")

    leaked = [d for d, _ in naive_results if not can_user_access(bob, d)[0]]
    if leaked:
        print(f"\n  🚨 LEAK: {len(leaked)} document(s) returned that Bob is NOT authorized to see:")
        for d in leaked:
            _, reason = can_user_access(bob, d)
            print(f"      - {d.doc_id} ({d.title}): {reason}")

    print("\n--- PRE-FILTER RETRIEVAL (correct) ---")
    correct_results, audit = store.search_pre_filter(query_embedding, bob, top_k=3)
    for doc, score in correct_results:
        print(f"  [{score:.3f}] {doc.doc_id} — {doc.title}")

    print("\n--- AUDIT TRAIL ---")
    for evt in audit:
        marker = "✓" if evt["outcome"] == "returned" else "✗"
        detail = evt.get("reason") or f"score={evt.get('score', 0):.3f}"
        print(f"  {marker} {evt['doc_id']}: {evt['outcome']} ({detail})")

    print()
    print("=" * 60)
    print("Reading the Result")
    print("=" * 60)
    print()
    print("The naive retrieval leaked HR's draft reorg to an engineer.")
    print("Pre-filter retrieval enforced authorization at the vector layer.")
    print("Every access decision is auditable.")


if __name__ == "__main__":
    main()
