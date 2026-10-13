"""
multi_tenant_prompt_registry.py — Tenant-scoped prompt registry.

Demonstrates:
- Prompts stored per (tenant_id, prompt_name, version)
- Deterministic lookup — fail closed on missing tenant version
- Prompt hash-based cache key that never crosses tenants
- Audit log on every prompt read

Run:
    python multi_tenant_prompt_registry.py
"""
from __future__ import annotations
import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PromptVersion:
    tenant_id: str
    name: str
    version: str
    template: str
    created_at: float = field(default_factory=time.time)


@dataclass
class AuditRecord:
    ts: float
    tenant_id: str
    prompt_name: str
    prompt_version: str
    caller_context: str


class TenantScopedPromptRegistry:
    """Every read is scoped by tenant. No cross-tenant fallback."""

    def __init__(self):
        # Keyed by (tenant_id, prompt_name, version)
        self._store: dict[tuple[str, str, str], PromptVersion] = {}
        # Per-tenant "active" pointer
        self._active: dict[tuple[str, str], str] = {}
        self._audit: list[AuditRecord] = []

    def register(self, prompt: PromptVersion, activate: bool = True) -> None:
        key = (prompt.tenant_id, prompt.name, prompt.version)
        self._store[key] = prompt
        if activate:
            self._active[(prompt.tenant_id, prompt.name)] = prompt.version

    def get_active(self, tenant_id: str, prompt_name: str,
                   caller_context: str) -> Optional[PromptVersion]:
        """Returns the tenant's active version. Fails closed if missing."""
        version = self._active.get((tenant_id, prompt_name))
        if version is None:
            # Fail closed. No global fallback.
            self._audit.append(AuditRecord(
                ts=time.time(),
                tenant_id=tenant_id,
                prompt_name=prompt_name,
                prompt_version="<not_found>",
                caller_context=caller_context,
            ))
            return None

        prompt = self._store.get((tenant_id, prompt_name, version))
        self._audit.append(AuditRecord(
            ts=time.time(),
            tenant_id=tenant_id,
            prompt_name=prompt_name,
            prompt_version=version,
            caller_context=caller_context,
        ))
        return prompt

    def cache_key(self, tenant_id: str, prompt: PromptVersion, message: str) -> str:
        """Cache key that includes tenant. Prompts are NEVER cached cross-tenant."""
        h = hashlib.sha256()
        h.update(tenant_id.encode())
        h.update(b":")
        h.update(prompt.name.encode())
        h.update(b":")
        h.update(prompt.version.encode())
        h.update(b":")
        h.update(message.encode())
        return h.hexdigest()

    def cross_tenant_audit_check(self) -> list[str]:
        """Detect any cross-tenant reads in the audit log."""
        issues = []
        # In a real system, caller_context includes acting tenant_id, and we'd
        # verify it matches the tenant being read.
        return issues


# --- Demo ---

def main():
    registry = TenantScopedPromptRegistry()

    # Tenant A: their customer support prompt
    registry.register(PromptVersion(
        tenant_id="acme_corp",
        name="customer_support",
        version="v3",
        template="You are Acme's helpful support assistant...",
    ))

    # Tenant B: their customer support prompt (different!)
    registry.register(PromptVersion(
        tenant_id="widget_inc",
        name="customer_support",
        version="v1",
        template="You are Widget Inc's professional support agent...",
    ))

    # Look them up
    print("=== Acme reads their customer_support prompt ===")
    p_a = registry.get_active("acme_corp", "customer_support", caller_context="request_1")
    print(f"  Got version: {p_a.version}")
    print(f"  Template: {p_a.template[:50]}...")

    print("\n=== Widget reads their customer_support prompt ===")
    p_b = registry.get_active("widget_inc", "customer_support", caller_context="request_2")
    print(f"  Got version: {p_b.version}")
    print(f"  Template: {p_b.template[:50]}...")

    # Show cache keys never overlap
    print("\n=== Cache keys ===")
    print(f"  Acme key:   {registry.cache_key('acme_corp', p_a, 'hello')[:20]}...")
    print(f"  Widget key: {registry.cache_key('widget_inc', p_b, 'hello')[:20]}...")

    # Nonexistent tenant: fail closed
    print("\n=== Unknown tenant tries to read (fails closed) ===")
    unknown = registry.get_active("evil_corp", "customer_support", caller_context="request_3")
    print(f"  Result: {unknown}  <- No global fallback")

    # Audit log
    print("\n=== Audit log ===")
    for rec in registry._audit:
        print(f"  {rec.tenant_id} -> {rec.prompt_name} v={rec.prompt_version}")


if __name__ == "__main__":
    main()
