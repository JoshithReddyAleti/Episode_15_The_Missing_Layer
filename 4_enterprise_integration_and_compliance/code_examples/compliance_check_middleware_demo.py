"""
compliance_check_middleware_demo.py — Compliance middleware for the BFF.

Demonstrates:
- Pre-flight policy checks (identity, tenant, region, MFA, DLP)
- Multi-framework enforcement in one middleware chain
- Fail-closed semantics
- Clear reason strings on rejection
- Compliance evidence generation

Run:
    python compliance_check_middleware_demo.py
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class Request:
    user_id: str
    tenant_id: str
    user_region: str
    feature: str
    message: str
    mfa_verified: bool = False
    contains_pii_estimate: bool = False


@dataclass
class TenantConfig:
    tenant_id: str
    allowed_regions: list
    require_mfa: bool
    require_baa: bool
    data_classification: str  # 'general', 'phi', 'financial'
    provider_baa_signed: bool = True


@dataclass
class PolicyDecision:
    allowed: bool
    reasons: list
    frameworks_evaluated: list
    evidence: dict


def check_identity(req: Request, tenant: TenantConfig) -> Optional[str]:
    if not req.user_id:
        return "SOC 2 CC6.1: unauthenticated request rejected"
    if req.tenant_id != tenant.tenant_id:
        return f"SOC 2 CC6.1: user tenant mismatch (user={req.tenant_id}, expected={tenant.tenant_id})"
    return None


def check_mfa(req: Request, tenant: TenantConfig) -> Optional[str]:
    if tenant.require_mfa and not req.mfa_verified:
        return "SOC 2 CC6.1 / HIPAA 164.312(d): MFA required but not verified"
    return None


def check_region(req: Request, tenant: TenantConfig) -> Optional[str]:
    if req.user_region not in tenant.allowed_regions:
        return f"GDPR Art 44-49: user region '{req.user_region}' not in allowed regions {tenant.allowed_regions}"
    return None


def check_baa(req: Request, tenant: TenantConfig) -> Optional[str]:
    if tenant.data_classification == "phi":
        if not tenant.require_baa or not tenant.provider_baa_signed:
            return "HIPAA: PHI processing requires signed BAA with provider — not present"
    return None


def check_dlp_input(req: Request, tenant: TenantConfig) -> Optional[str]:
    if tenant.data_classification == "phi" and req.contains_pii_estimate:
        return "HIPAA 164.312(e)(1): input contains PII patterns; must route through DLP scrubber first"
    return None


CHECKS: list[tuple[Callable, str]] = [
    (check_identity, "identity"),
    (check_mfa, "mfa"),
    (check_region, "residency"),
    (check_baa, "baa"),
    (check_dlp_input, "dlp"),
]


def evaluate(req: Request, tenant: TenantConfig) -> PolicyDecision:
    reasons = []
    evidence = {}
    for fn, name in CHECKS:
        result = fn(req, tenant)
        if result is None:
            evidence[name] = "passed"
        else:
            reasons.append(result)
            evidence[name] = f"failed: {result}"

    frameworks = []
    for r in reasons:
        if "SOC 2" in r and "SOC 2" not in frameworks:
            frameworks.append("SOC 2")
        if "HIPAA" in r and "HIPAA" not in frameworks:
            frameworks.append("HIPAA")
        if "GDPR" in r and "GDPR" not in frameworks:
            frameworks.append("GDPR")

    return PolicyDecision(
        allowed=(len(reasons) == 0),
        reasons=reasons,
        frameworks_evaluated=frameworks or ["SOC 2", "HIPAA", "GDPR"],
        evidence=evidence,
    )


def print_decision(scenario: str, decision: PolicyDecision):
    print(f"\n=== {scenario} ===")
    status = "✓ ALLOWED" if decision.allowed else "✗ REJECTED"
    print(f"  {status}")
    if decision.reasons:
        print("  Reasons:")
        for r in decision.reasons:
            print(f"    • {r}")
    print("  Evidence:")
    for k, v in decision.evidence.items():
        marker = "✓" if v == "passed" else "✗"
        print(f"    {marker} {k}: {v}")


def main():
    # Tenant config: US healthcare with strict requirements
    healthcare_tenant = TenantConfig(
        tenant_id="acme_hospital",
        allowed_regions=["us-east-1", "us-east-2"],
        require_mfa=True,
        require_baa=True,
        data_classification="phi",
        provider_baa_signed=True,
    )

    # Scenario 1: correct request
    req1 = Request(
        user_id="usr_dr_alice",
        tenant_id="acme_hospital",
        user_region="us-east-1",
        feature="clinical_notes_copilot",
        message="Summarize patient history",
        mfa_verified=True,
        contains_pii_estimate=False,
    )
    print_decision("Scenario 1: Legit clinician request", evaluate(req1, healthcare_tenant))

    # Scenario 2: no MFA
    req2 = Request(
        user_id="usr_dr_bob",
        tenant_id="acme_hospital",
        user_region="us-east-1",
        feature="clinical_notes_copilot",
        message="Summarize",
        mfa_verified=False,
    )
    print_decision("Scenario 2: Clinician without MFA", evaluate(req2, healthcare_tenant))

    # Scenario 3: wrong region
    req3 = Request(
        user_id="usr_dr_charlie",
        tenant_id="acme_hospital",
        user_region="eu-west-1",  # US healthcare tenant, but user in EU
        feature="clinical_notes_copilot",
        message="Summarize",
        mfa_verified=True,
    )
    print_decision("Scenario 3: US healthcare user from EU region", evaluate(req3, healthcare_tenant))

    # Scenario 4: PII contamination in input
    req4 = Request(
        user_id="usr_dr_dana",
        tenant_id="acme_hospital",
        user_region="us-east-1",
        feature="clinical_notes_copilot",
        message="Patient SSN 123-45-6789 has issue",
        mfa_verified=True,
        contains_pii_estimate=True,
    )
    print_decision("Scenario 4: PII in raw input (DLP should scrub first)", evaluate(req4, healthcare_tenant))

    print()
    print("=" * 60)
    print("Reading the Result")
    print("=" * 60)
    print()
    print("Every check maps to specific framework controls.")
    print("Rejections cite the applicable framework and control.")
    print("Evidence per-check provides audit trail for compliance review.")
    print("Fail-closed: any single check failing rejects the whole request.")


if __name__ == "__main__":
    main()
