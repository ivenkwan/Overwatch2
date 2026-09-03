# Third-Party Issuer Onboarding & Trust-Registry Operations (AWI TASK-056)

Date: 2026-09-03 · Status: Procedure published · Applies to: didvc trust
registry + AML platform consuming tenants

## 1. Purpose

Defines how the platform accredits EXTERNAL KYC/KYB credential issuers
(VASPs, banks, iAM Smart/RealDID-anchored providers) so their credentials
are accepted by the relying tenants (notably `aml`), and how trust entries
are operated afterwards. First-party (in-group CDP) issuance is already
registered per TASK-033; this guide covers expansion to third parties.

## 2. Accreditation workflow (maker-checker)

Trust entries are created/updated/revoked through the didvc admin surface
(`/didvc/trust-entries`, ADMIN role) ONLY via a two-person control:

1. **Maker** submits the trust-entry proposal:
   - `verifierTenantId` (e.g. `aml`), `issuerDid`, `vct`, `accreditationLevel`,
     validity window, and an evidence reference (licence number, registry
     extract, audit report).
2. **Checker** (a different ADMIN) reviews and approves; the entry becomes
   `active`. A single role can never activate an issuer.
3. Every create/update/revoke is written to the hash-chained audit log
   (actor, justification, evidence ref).

## 3. Issuer due-diligence checklist (per SECURITY.md §3.5)

Before an external issuer is accredited, the compliance/ops intake must
confirm:

- [ ] Legal identity and regulatory status (licence/authorisation number,
      regulator) for the jurisdiction(s) the issuer serves.
- [ ] KYC/KYB assurance level actually delivered (identity proofing,
      sanctions screening at onboarding, refresh cadence).
- [ ] Key custody posture (HSM/PKCS#11 or equivalent; no private material
      in app memory) and key-rotation policy.
- [ ] Revocation responsiveness (how quickly a subject's credential is
      revoked after a trigger event).
- [ ] Credential schema hygiene: the vct's claim set is minimal and the
      issuer enforces the whitelist (no raw PII beyond the contract).
- [ ] Data-protection adequacy for the jurisdictions involved (PDPO/HK and
      the issuer's home regime).

## 4. Periodic review

- Trust entries are **reviewed quarterly** (validity windows are capped at
  12 months and must be renewed by re-issuing the entry — renewal is
  another maker-checker pair).
- Issuer revocation (e.g. licence loss) must be processed within 24 hours:
  revoke the trust entry(s); the next M2M verification of any credential
  from that issuer then fails closed (trust check runs on every verify).

## 5. Registry operations (performance — feasibility R7)

- `TrustRegistryServiceImpl` now serves lookups from a refresh-on-write
  snapshot cache instead of a full persistence scan on every
  `isTrusted()` call. The cache is rebuilt on save/delete/update only, so
  the per-verification cost is O(registry-in-memory), not O(persistence).
- **Parity guarantee**: `TrustRegistryServiceImplTest` seeds a mixed
  registry (multiple tenants/issuers/vcts + revoked/expired entries) and
  asserts the cached result equals the full-scan result for 80 tenant ×
  issuer × vct query combinations, plus refresh-on-update and
  refresh-on-delete cases (11 tests green).
- On a scaled fleet the cache is per-instance; entries change rarely, so
  cross-instance staleness is bounded by the admin surface (single writer)
  — if multi-writer is ever needed, the refresh should move to a cache
  invalidation topic.

## 6. Sign-off

Procedure owner: Platform engineering (didvc ops). Compliance review of
the DD checklist: pending first external-issuer intake.
