"""
audit_trail_schema_demo.py — Audit event schema with tamper-evident chain.

Demonstrates:
- Structured audit event schema for LLM calls
- Cryptographic hash chain for tamper evidence
- Chain verification (detecting tampering)
- Content/metadata split (hashes in audit, plaintext elsewhere)

Run:
    python audit_trail_schema_demo.py
"""
from __future__ import annotations
import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Optional


def sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


@dataclass
class Identity:
    user_id: str
    tenant_id: str
    auth_method: str
    mfa_verified: bool
    session_id: str
    roles: list
    groups: list


@dataclass
class RequestBlock:
    feature: str
    prompt_version: str
    user_message_hash: str
    user_message_tokens: int
    retrieved_doc_ids: list
    contains_pii: bool


@dataclass
class ProcessingBlock:
    model: str
    provider: str
    provider_region: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int


@dataclass
class ResponseBlock:
    response_hash: str
    response_tokens: int
    tool_calls_made: int
    guardrail_flags: list


@dataclass
class PolicyBlock:
    rbac_result: str
    abac_result: str
    dlp_input_result: str
    dlp_output_result: str


@dataclass
class AuditEvent:
    event_id: str
    event_type: str
    timestamp: str
    identity: Identity
    request: RequestBlock
    processing: ProcessingBlock
    response: ResponseBlock
    policy: PolicyBlock
    prev_event_hash: str = ""
    self_hash: str = ""

    def compute_self_hash(self) -> str:
        # Serialize everything except self_hash
        d = asdict(self)
        d.pop("self_hash", None)
        canonical = json.dumps(d, sort_keys=True)
        return sha256(canonical)


class AuditLog:
    """Append-only audit log with hash chain."""

    def __init__(self):
        self._events: list[AuditEvent] = []
        self._genesis_hash = "0" * 64

    def append(self, event: AuditEvent) -> AuditEvent:
        # Link to previous
        event.prev_event_hash = self._events[-1].self_hash if self._events else self._genesis_hash
        # Compute self hash
        event.self_hash = event.compute_self_hash()
        self._events.append(event)
        return event

    def verify_chain(self) -> tuple[bool, list]:
        """Verify the hash chain integrity. Returns (valid, list_of_issues)."""
        issues = []
        prev_hash = self._genesis_hash
        for i, event in enumerate(self._events):
            # Check chain link
            if event.prev_event_hash != prev_hash:
                issues.append(f"Event {i} ({event.event_id}): broken chain link. Expected prev={prev_hash[:16]}..., got {event.prev_event_hash[:16]}...")
            # Check self hash
            expected_self = event.compute_self_hash()
            if event.self_hash != expected_self:
                issues.append(f"Event {i} ({event.event_id}): self hash mismatch. Event has been modified after logging.")
            prev_hash = event.self_hash
        return (len(issues) == 0, issues)

    def query(self, user_id: str = None, since: str = None) -> list:
        results = self._events
        if user_id:
            results = [e for e in results if e.identity.user_id == user_id]
        if since:
            results = [e for e in results if e.timestamp >= since]
        return results


def make_sample_event(event_num: int, user_id: str) -> AuditEvent:
    """Create a plausible audit event."""
    user_message = f"query number {event_num} from {user_id}"
    response = f"response to query {event_num}"
    return AuditEvent(
        event_id=f"evt_{event_num:04d}",
        event_type="llm.call",
        timestamp=f"2026-08-11T14:{event_num:02d}:00Z",
        identity=Identity(
            user_id=user_id,
            tenant_id="acme_corp",
            auth_method="saml_okta",
            mfa_verified=True,
            session_id=f"sess_{event_num}",
            roles=["member"],
            groups=["engineering"],
        ),
        request=RequestBlock(
            feature="code_copilot",
            prompt_version="v3.2",
            user_message_hash=sha256(user_message),
            user_message_tokens=len(user_message.split()),
            retrieved_doc_ids=["doc_a", "doc_b"],
            contains_pii=False,
        ),
        processing=ProcessingBlock(
            model="gpt-4o",
            provider="openai",
            provider_region="us-east-1",
            input_tokens=1200,
            output_tokens=340,
            cost_usd=0.0064,
            latency_ms=1450,
        ),
        response=ResponseBlock(
            response_hash=sha256(response),
            response_tokens=340,
            tool_calls_made=1,
            guardrail_flags=[],
        ),
        policy=PolicyBlock(
            rbac_result="allow",
            abac_result="allow",
            dlp_input_result="clean",
            dlp_output_result="clean",
        ),
    )


def main():
    log = AuditLog()

    # Append 5 events
    for i in range(1, 6):
        user = "usr_alice" if i % 2 == 0 else "usr_bob"
        log.append(make_sample_event(i, user))

    print("=" * 60)
    print("Audit Log: 5 Events Written")
    print("=" * 60)
    for e in log._events:
        print(f"  {e.event_id}  user={e.identity.user_id}  hash={e.self_hash[:16]}...")

    # Verify chain
    print("\n=== Chain Verification (before tampering) ===")
    valid, issues = log.verify_chain()
    print(f"  Chain valid: {valid}")
    if issues:
        for issue in issues:
            print(f"  {issue}")

    # Query
    print("\n=== Query: Alice's activity ===")
    alice_events = log.query(user_id="usr_alice")
    for e in alice_events:
        print(f"  {e.event_id}  at {e.timestamp}  cost=${e.processing.cost_usd:.4f}")

    # Attempt to tamper — modify an event in place
    print("\n=== Attempting Tamper (change Bob's tokens) ===")
    log._events[2].processing.output_tokens = 99999  # tamper!
    print(f"  Modified event {log._events[2].event_id} in place.")

    print("\n=== Chain Verification (after tampering) ===")
    valid, issues = log.verify_chain()
    print(f"  Chain valid: {valid}")
    for issue in issues:
        print(f"  🚨 {issue}")

    print()
    print("=" * 60)
    print("Reading the Result")
    print("=" * 60)
    print()
    print("Every event chained to prior via sha256(prev + content).")
    print("Any post-hoc modification breaks the chain and is detectable.")
    print("Regulators accept this as tamper-evident storage when combined")
    print("with WORM storage (S3 Object Lock, etc.) for at-rest protection.")


if __name__ == "__main__":
    main()
