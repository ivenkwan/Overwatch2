# Implementation Plan — DID/VC Authorized-Wallet Integration, Phase 1 (AWI TASK-030)

Date: 2026-09-03 · Parent: [ADR-0002](../docs/adr/0002-didvc-authorized-wallet-integration.md) ·
Program: todo.md § 🟣 AWI (TASK-029 … TASK-060) · Feasibility: `docs/feasability.md`

## Objective

Deliver the M2M verification gate and the party-dimension producer: a wallet
owner's KYC/KYB credential is verified against didvc-edge, the party/UBO
tables are populated idempotently, and `SCN_CROSS_RAIL_LAYER_01` executes on
real party data instead of skipping.

## Work items (tracked as todo.md tasks)

| # | Item | Deliverable | Verification |
|---|------|-------------|--------------|
| 1 | Authorization data model (TASK-036) | `init-scripts/07-authorization-model.sql`: `party.did`/`onboarding_channel`, `party_credential`, `wallet_authorization` (+ RLS, indexes) | idempotent re-run; column map to v5 converged model documented |
| 2 | M2M client service (TASK-037) | `app/services/identity_provider.py` wrapping `/m2m/verify[-batch]` (timeouts, retry/backoff, circuit breaker, evidence hash) | unit tests incl. failure paths; no literals |
| 3 | Onboarding API (TASK-038) | `POST /api/v1/onboarding/verify` — ADMIN scope, explicit tenant context, idempotent upserts, audited | tests: idempotency, RLS fail-closed, envelope errors |
| 4 | Party projection wiring (TASK-039) | `party_loader.py` invoked post-onboarding + batch; regression test that cross-rail alert fires on fixture data | automated regression (synthetic party + transfers) |
| 5 | Maker-checker (TASK-040) | Authorization grant/revoke via maker+checker with justification; dual-state sync | test: single-role change rejected |
| 6 | PII claims (TASK-041) | Claim fields in the masking matrix; unmask audited | matrix unit tests |
| 7 | RLS hardening (TASK-042) | Explicit `app.current_tenant` dependency for all AWI endpoints; no `LIMIT 1` shortcuts | cross-tenant fail-closed test |

## Non-goals (Phase 2+)

Wallet-binding schema, address-control proofs, nightly re-verification
batch, OID4VP surface — see todo.md Phases 2–4.

## Verification caveats (honest status)

- All Python-level items are unit-tested against fakes/stubs in
  `backend/tests/` — **no live AGE or didvc runtime is required for Phase 1
  acceptance**.
- End-to-end verification against a real didvc-edge deployment is the
  TASK-059 E2E suite (Phase 4) and is explicitly out of Phase-1 scope.

## Rollout

1. Apply `07-authorization-model.sql` (additive — safe on existing volumes).
2. Deploy backend with `IDENTITY_PROVIDER_URL` + `IDENTITY_PROVIDER_API_KEY`
   configured; onboarding endpoints stay internal until TASK-033 registers
   the tenant and trust entries.
3. Monitor `/api/v1/audit/export` for `ONBOARDING_*` events; nightly
   party_loader run is additive-only (MERGE / ON CONFLICT).
