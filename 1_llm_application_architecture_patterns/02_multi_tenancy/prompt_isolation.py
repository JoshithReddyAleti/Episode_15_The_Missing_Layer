"""
Prompt Isolation

Tenant-scoped prompt registry — no cross-tenant reads, deterministic assembly, injection defense

See the section README for the full deep-dive:
  1_llm_application_architecture_patterns/02_multi_tenancy/README.md
"""


def summary() -> str:
    """One-line summary — the README is the source of truth."""
    return "Tenant-scoped prompt registry — no cross-tenant reads, deterministic assembly, injection defense"


if __name__ == "__main__":
    print(summary())
