# Threat Model — didvc Adoption (AWI TASK-035)

Date: 2026-09-03 · Scope: the M2M verification path between the Overwatch AML
platform (`aml-backend`) and `didvc-edge`, plus the wallet-binding flow built
on it. Method: STRIDE over the trust boundary; vendor assessment per
SECURITY.md §3.5/§6.

## 1. System boundary

```
Analyst/Operator ──HTTPS──> aml-backend ──API-key (+future mTLS)──> didvc-edge /{tenant}/m2m/verify
                                │                                        │
                                ▼                                        ▼
                     PostgreSQL (party, wallet_authorization,    didvc platform (trust registry,
                     audit chain)                                status lists, hash-chained audit)
Applicant ── signs challenge with on-chain key ──> aml-backend (address-control proof)
```

Assets: KYC/KYB credential authenticity; wallet-authorization decisions;
trust registry integrity; PII in claims; audit chains.

## 2. STRIDE findings

| # | Threat | Vector | Impact | Controls (task) | Residual |
|---|--------|--------|--------|-----------------|----------|
| T1 | **Credential forgery** | Attacker crafts SD-JWT, hopes signature checks are skipped | Unauthorized wallet | Edge validates RS256 signature + issuer trust registry on every verify (TASK-037 relies on edge; edge behaviour test-covered) | Low |
| T2 | **Replay of stolen credential** | Reuses a captured token | Unauthorized wallet | `exp` enforced; per-verification status-list check revokes stolen credentials; M2M API-key protects the channel (TASK-048 nightly re-check shrinks window) | Medium until event-driven re-check (TASK-051) |
| T3 | **Issuer compromise / trust-registry poisoning** | A trusted issuer's keys are stolen, or rogue trust entries inserted | Fleet-wide false "verified" | Trust entries maker-checker + admin role (TASK-056); registry is didvc-side ADMIN-gated; revocation of issuer invalidates its credentials at next verify | Medium — depends on didvc ops discipline |
| T4 | **API-key leakage (backend→edge)** | Key in logs/config/commits | Unauthorized verification calls | Keys env/vault only, no literals (enforced); audit metering records every verify; mTLS + rotation (TASK-055) | Low after mTLS |
| T5 | **Address-control bypass** | Applicant binds an address they don't control (no signature check) | False attribution | Challenge nonce single-use + TTL + signature verification (TASK-044/045); binding level recorded | Low |
| T6 | **PII leakage via claims** | Over-broad claim collection | PDPO exposure | `claim_level_response`/minimal claims; PII matrix masks claim fields (TASK-041); unmask audited | Low |
| T7 | **Revocation lag** | Wallet revoked between nightly checks | Stale authorization ≤24h | Nightly batch (TASK-048) mirrors sanctions re-screen SLA; high-value/EDD path can re-verify synchronously | Accepted (documented) |
| T8 | **Denial of service on edge** | Edge unreachable at onboarding | Onboarding blocked (not safety) | Circuit breaker + timeouts in client (TASK-037); fail-closed = wallet stays unauthorized | Availability only |
| T9 | **SQL injection via binding data** | Malformed ids into local queries | Data corruption | `$n` bind parameters + UUID validation (TASK-003 discipline, TASK-038) | Low |
| T10 | **Audit tampering** | DBA edits audit rows | Evidentiary loss | Append-only triggers + hash chain both sides + `/api/v1/audit/verify` (TASK-004) | Requires privileged DB compromise |

## 3. Vendor assessment (SECURITY.md §3.5)

- **Provenance**: in-group module (HKT Trusted-Identity CDP), Apache-2.0
  licensed, 220 tests green in this repo's build (2026-09-03).
- **Security posture**: `didvc/docs/security-review.md` lists open findings
  F-7, F-8, F-9, F-10, F-12 — **all must close, with regression tests, plus a
  third-party penetration test, before any production dependency**
  (TASK-034 gates TASK-059 E2E / production sign-off).
- **Cryptographic posture**: Ed25519/ES256 issuance, HSM (PKCS#11) support,
  RFC 9901 SD-JWT vectors pass; `ldp_vc` is JWS-wrapped (documented
  limitation — not used by this integration).
- **Supply chain**: dependencies resolved from Maven Central + Apache
  snapshots; pin versions for production builds (follow-up noted in
  `didvc/BUILD.md`).

## 4. Acceptance

Residual risks T2 (until event-driven re-check) and T3 (issuer ops) are
**accepted in writing** by Platform engineering, conditional on the Phase-4
controls above landing before production traffic.
