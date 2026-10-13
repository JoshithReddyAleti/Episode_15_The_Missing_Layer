# 🔐 Identity & Access Control — The Foundation Everything Else Rests On

> *"Who is making this LLM call?"*
>
> *"Uh... the app."*
>
> *"That's not enterprise ready."*

Every enterprise security review starts here. Every compliance framework requires it. Every audit demands the trace. And most AI-native startups get it wrong because they built for consumer identity first ("email + Google login") and try to bolt on enterprise identity later.

**The identity of the requesting user must propagate into every LLM call, every retrieval, every tool invocation, and every audit event.** Not as a log field. As a first-class object that gates every decision downstream.

This section is how to build that.

---

## The Identity Model

An enterprise identity is not a user ID. It's a rich, verifiable claim structure.

**Minimum required attributes per LLM call:**

- **User principal**: the authenticated identity (`user_id`, `email`, `subject`)
- **Tenant / workspace**: which org this user belongs to (`tenant_id`, `workspace_id`)
- **Roles**: coarse-grained authorization (`admin`, `member`, `viewer`, `guest`)
- **Groups / teams**: for permission inheritance (`groups: [engineering, ai-council]`)
- **Attributes**: for ABAC (`department`, `location`, `clearance_level`, `employment_status`)
- **Session context**: (`session_id`, `mfa_verified`, `device_trust`, `ip_region`)
- **Delegation chain**: if acting on behalf of another user (`impersonation`, `on_behalf_of`)
- **Consent state**: for regulated data (`hipaa_consent`, `ai_processing_consent`)

**This is the object the BFF resolves before any LLM call fires.** Not resolved = call rejected.

---

## Federation: SSO Is Table Stakes

Enterprise buyers do not create local passwords in your app. Their identity provider (IdP) is the source of truth. Your app federates.

### SAML 2.0

The workhorse of enterprise SSO. Still the most common in Fortune 500.

**The flow:**
1. User navigates to your app
2. Your app redirects them to their IdP (Okta, Azure AD, Ping, etc.) with a SAML AuthnRequest
3. User authenticates at the IdP
4. IdP returns a signed SAML assertion containing user attributes
5. Your app validates the signature against the IdP's certificate
6. Your app creates a session and issues its own tokens

**Non-negotiables:**
- Signature validation (RSA-SHA256 minimum; deprecate SHA-1)
- Assertion consumer URL (ACS) must be HTTPS
- Certificate rotation support (IdPs rotate; you must handle both old and new during transition)
- Single Logout (SLO) — enterprise wants revocation to propagate
- Assertion replay prevention (nonce or InResponseTo tracking)
- Encrypted assertions for sensitive attribute release

### OIDC (OpenID Connect)

The modern federation protocol. Preferred for new integrations. Cloud-native IdPs (Auth0, Azure AD, Okta) all support it.

**The flow:**
1. Redirect to IdP with an authorization code request
2. User authenticates
3. IdP redirects back with a code
4. Your app exchanges code for tokens at IdP's token endpoint
5. Get `id_token` (JWT with user claims) and `access_token`
6. Validate `id_token` signature (typically RS256) against IdP's JWKS endpoint

**Advantages over SAML:**
- JSON everywhere, no XML canonicalization pain
- Bearer tokens work across mobile, SPA, native
- Standardized userinfo endpoint
- Refresh tokens for long-lived sessions

**Non-negotiables:**
- JWKS-based key rotation
- `iss`, `aud`, `exp`, `nbf` claim validation
- Token audience matches your app's client ID
- PKCE for public clients (SPAs, mobile)
- Refresh token rotation and revocation

### SCIM (User Provisioning)

Federation gives you *authentication*. SCIM gives you *lifecycle*.

**Why enterprises demand it:**
- New employee joins → automatic account creation
- Employee changes role → automatic group membership update
- Employee leaves → automatic deactivation

**Without SCIM:** ex-employees keep AI access for weeks. Ex-contractors keep tokens. Compliance auditor finds this. Deal at risk.

**SCIM 2.0 endpoints your app implements:**
- `POST /Users` — create user
- `PATCH /Users/{id}` — update attributes, group membership
- `DELETE /Users/{id}` — soft-delete / deactivate
- Same set for `/Groups`

**Practical minimum:** support `active: false` propagation to disable user access within 60 seconds of IdP-side deactivation. That's what auditors check.

---

## RBAC vs ABAC — Which for AI Features?

### RBAC (Role-Based Access Control)

Users have roles. Roles have permissions. Simple, well-understood, easy to audit.

```yaml
roles:
  member:
    permissions:
      - ai.chat.use
      - ai.search.use
  admin:
    permissions:
      - ai.chat.use
      - ai.search.use
      - ai.settings.manage
      - ai.audit.view
  viewer:
    permissions:
      - ai.chat.use  # read-only chat, no history persistence
```

**Wins when:** small number of coarse-grained access levels. Most SaaS products live here.

**Fails when:** access decisions depend on context (which document? which time? which region?).

### ABAC (Attribute-Based Access Control)

Access decisions evaluate attributes of the user, resource, action, and environment.

```
allow_ai_use if
    user.employment_status == "active" AND
    user.department in resource.allowed_departments AND
    user.location.country == resource.data_residency AND
    environment.time between 08:00 and 20:00 user_local AND
    user.mfa_verified == true
```

**Wins when:** context matters. Enterprise AI features almost always need this because access depends on document ownership, data classification, region, etc.

**Fails when:** overused. Complex policies become unauditable. Auditors want to reason about specific access grants; ABAC policies are algorithms.

### The recommended hybrid

**RBAC for feature-level access** (can this user use the AI at all, in this workspace, with these features?).

**ABAC for data-level access** (given the user has feature access, which specific documents can be retrieved, which tools can be invoked with which parameters?).

This maps to the natural split in your architecture: RBAC in the BFF middleware, ABAC in the retrieval layer.

---

## Zero-Trust for LLM Features

Zero-trust is a security posture: **never trust, always verify**. Every request re-evaluated on its own merits regardless of network location.

**How it applies to LLM features:**

1. **Every LLM call is authenticated.** No service-to-service calls without identity. If your background job calls the LLM, it authenticates as a service principal with restricted scope.

2. **Every LLM call is authorized against current policy.** Not "user had access at login" — "user has access *right now* for *this specific* request." Policy changes propagate immediately.

3. **Every LLM call is scoped to least privilege.** The service token to your LLM provider is short-lived, scoped to the specific model/deployment, and rotated regularly. Not a lifetime API key in an env var.

4. **Every LLM call is logged as an authentication event.** Not just "call happened" — "user X authenticated with method Y, was authorized against policy Z, and made call W."

5. **Every LLM call is analyzed for anomalies.** Impossible travel (user logs in from NYC then Tokyo 30 minutes later), unusual query patterns, off-hours access — feed the SIEM.

**Real practice:** most AI-native startups fail #3. They put the provider API key in an env var, use it for every call, and don't rotate. Enterprise pen-testers exfiltrate that key from a leaked container image within a week.

---

## The Provider Credential Problem

Your LLM provider gives you an API key. That key is *your* identity to the provider — but the provider doesn't know or care which of *your* end-users made the call.

**The wrong pattern:**
```
[Client] --> [App] --> uses OPENAI_API_KEY --> [OpenAI]
```

Every call charged to your account. No per-user attribution at the provider. If OpenAI investigates suspicious traffic, they see *your* account, not the user.

**The right pattern — enterprise scale:**

**Option A: Provider-side sub-tenants.** Some providers (Anthropic Bedrock, Azure OpenAI) support sub-tenant billing/tracking via headers or API-key metadata. Attach `user_id` and `tenant_id` metadata to every call.

**Option B: STS-issued short-lived tokens.** For providers on cloud IAM (Bedrock via AWS STS, Vertex AI via GCP Workload Identity), your BFF assumes a role scoped per-tenant and calls with a short-lived token. Provides real audit trail on the provider side.

**Option C: BFF is the identity boundary.** You accept that the provider sees you as one caller and rely on your BFF's audit trail to reconstruct per-user attribution.

**Reality:** most enterprises live in Option C. Bring your own key (BYOK) options and provider sub-tenanting are increasingly common in 2026 but not universal.

**The auditor question:** "Prove that user Alice's request on 2026-03-15 at 14:23 UTC resulted in this specific LLM call." Your BFF audit log must answer this.

---

## Identity Propagation Through The Stack

The identity established at the edge must flow through every downstream call. A concrete pattern:

**1. Edge auth (API Gateway):**
- Validate bearer token
- Extract user claims
- Emit identity context object into request headers (signed, tamper-evident)

**2. BFF middleware:**
- Read signed identity context
- Enrich with tenant config, entitlements, current policy
- Attach identity to all downstream calls (retrieval, LLM, tools)

**3. Retrieval layer:**
- Apply tenant and user ACL filters as pre-filters (not post-filters)
- Audit the retrieval with identity attached

**4. LLM provider call:**
- Include identity metadata where the provider supports it
- Log the call with identity in your audit trail

**5. Tool invocation:**
- Tool calls must re-check authorization for *this specific tool with these parameters and this identity*
- No shared tool tokens; every tool call is user-attributed

**6. Response and audit:**
- Bind response to originating identity
- Emit audit event with full identity chain
- Session state keyed by (tenant_id, user_id) always

**If any layer loses identity context, that layer becomes a compliance gap.**

---

## Delegation and Impersonation

Enterprises frequently need admin-impersonation for support scenarios. A support agent takes over Alice's session to debug an issue.

**The compliance requirement:**
- Delegation is *explicit* — not implicit through shared credentials
- Delegation is *audited* — every action taken during delegation logged as (acting_user, on_behalf_of)
- Delegation is *time-bounded* — sessions expire quickly, require re-authorization
- Delegation preserves data access rules — the delegating user's ACLs apply, not the admin's broader access

**The wrong pattern:** admin has read access to all workspaces, opens Alice's data directly. Audit trail shows "admin accessed data" — but there's no link to the ticket or the business justification.

**The right pattern:** admin opens a "support session" tied to a ticket ID. Session grants time-limited impersonation of Alice, scoped to Alice's normal permissions. Every action logged with `acting_user=admin, on_behalf_of=alice, ticket_id=T123`.

For AI features specifically: LLM calls during impersonation should be marked as such in the audit log. This matters for HIPAA / financial audit trails.

---

## The MFA Question

**Should MFA gate AI features?**

- **General MFA:** already required at the IdP for enterprise; you inherit it.
- **Step-up MFA for high-risk AI actions:** yes, for high-blast-radius operations. E.g., an AI agent about to send an outbound email or make a purchase should trigger MFA re-verification.
- **MFA for reading data:** typically not required beyond initial session MFA.

**The pattern:** MFA verification state flows in the identity context. High-blast-radius LLM tools check `mfa_verified_recently` and reject if stale.

---

## Files In This Folder

| File | Concept |
|---|---|
| [`saml_and_oidc_federation.py`](saml_and_oidc_federation.py) | SAML and OIDC integration patterns with token validation |
| [`scim_provisioning.py`](scim_provisioning.py) | SCIM 2.0 endpoints for user lifecycle |
| [`rbac_and_abac_policies.py`](rbac_and_abac_policies.py) | Hybrid RBAC/ABAC policy evaluation |
| [`identity_propagation.py`](identity_propagation.py) | End-to-end identity flow through the LLM stack |
| [`delegation_and_impersonation.py`](delegation_and_impersonation.py) | Support-session impersonation with audit |
| [`provider_credential_patterns.py`](provider_credential_patterns.py) | STS, sub-tenancy, and provider identity strategies |

---

## The Staff Interview Question

*"How does the identity of an end user propagate into an LLM call that happens on our backend?"*

**The wrong answer:** "We include their user_id in a log."

**The right answer:**
*"The end user authenticates via our SSO federation — SAML for older IdPs, OIDC for modern ones — with SCIM propagating lifecycle changes. At the API gateway, we validate the bearer token and extract claims: user principal, tenant, roles, groups, ABAC attributes, session context including MFA verification and device trust. This becomes a signed identity context that flows in a request header through every downstream service. The BFF middleware enriches it with tenant config and current entitlements — policy evaluation happens per-request against current policy, not cached from login. When we call the LLM provider, if they support sub-tenancy (Bedrock via STS assume-role scoped per tenant, Azure OpenAI with header metadata), we attach the identity; otherwise the BFF is the identity boundary and the audit trail reconstructs attribution. Every LLM call emits an audit event with the full identity chain including delegation state if impersonation is active. High-blast-radius tool calls trigger step-up MFA if the recent verification is stale. The result: any auditor query 'who made this specific LLM call, under what authority, with what data access' can be answered from the audit log with cryptographic assurance. That's the identity story before we talk about anything else."*

That answer wins the staff-level enterprise interview.

---

*Return to [folder README](../README.md) · Next: [Data Access & Row-Level Security →](../02_data_access_and_row_level_security/README.md)*
