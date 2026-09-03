# Graph-Profile Unification & v5 Migration Mapping (AWI TASK-060)

Date: 2026-09-03 · Status: Decision recorded · Parents: ADR-0001
(unified detection engine), ADR-0002 (authorized-wallet integration),
gap-plan §7.

## 1. The two deployed graphs

| | `aml_network` | `tap_and_go_network` |
|---|---|---|
| Rails | fiat + chains (`system` property) | fiat only (constant `FIAT`) |
| Accounts | `Entity|SuperNode` | `Customer|Counterparty|Merchant` |
| Currency | USD | HKD |
| Party dimension | ✅ `Party`/`OWNED_BY`/`UBO_OF` | ❌ none |
| Authorization dimension (P2) | ✅ `authorized`/`ever_authorized` props | ❌ none |
| Pipeline | manual `run_batch.py` + loaders | Dagster (compose-deployed) |

## 2. Decision (ADR-0001 amendment-style note)

**Do NOT extend the authorization (or party) dimension onto
`tap_and_go_network`.** The tap-and-go rail is a single fiat SVF graph whose
nodes are customer/merchant identifiers with **no wallet addresses** — the
authorized-wallet registry (`app.wallet_authorization`) and the credential
lifecycle are wallet-centric and cannot attach to it. The abstract engine
already handles this correctly: capability-gated scenarios (`SCN_AUTH_DRIFT_01`,
`SCN_CROSS_RAIL_LAYER_01`) are skipped on profiles that lack the dimension
(engine `missing_capabilities` gate, verified by tests).

If a future rail (e.g. a second crypto corridor) is deployed, it gets its own
`GraphProfile` carrying the `AUTHORIZATION_DIMENSION` capability — the
registry/render/engine need no changes, only a profile.

## 3. What changed in P2 (this task)

- `Capability.AUTHORIZATION_DIMENSION` added to the contract
  (`aml_detection/contract.py`).
- `AuthorizationDimension(auth_prop, ever_auth_prop)` capability object;
  `Capabilities.supports()` extended.
- `aml_network` profile advertises the dimension
  (`profiles/aml_network.py`).
- `<<auth_prop>>` / `<<ever_auth>>` render tokens + validation
  (`render.py`).
- `SCN_AUTH_DRIFT_01` registered (TASK-052) — gated to auth-capable
  profiles.
- Graph-projection contract: nodes of authorized wallets carry
  `authorized` (current) and `ever_authorized` (set at first approval,
  never cleared) booleans, snapshotted from `app.wallet_authorization` by
  the projection/revocation path (aml_network-side `sp_attach_auth_metadata`
  + registry mirror, TASK-050).

## 4. v5 converged-model migration mapping (v2 → aml_core)

Committed beside the schema in `07-authorization-model.sql` and reproduced
here so it cannot drift:

| v2 (this repo) | v5 converged model (`aml_core`) | Notes |
|---|---|---|
| `app.party.party_id` | `aml_core.party.party_id` | identity of the wallet owner |
| `app.party.did` | `aml_core.party.did` | credential subject DID |
| `app.party.onboarding_channel` | `aml_core.party.onboarding_channel` | enum incl. `iAM_SMART` |
| `app.party_instrument` | `aml_core.account_party_link` | role OWNER etc. |
| `app.party_ubo` | `aml_core.beneficial_owner` | ≥25% UBO chains |
| `app.party_credential.credential_id` | `aml_core.account_party_link` + credential columns | evidence hash retained |
| `app.wallet_authorization.blockchain` | `aml_core.account.blockchain_network` | enum parity |
| `app.wallet_authorization.wallet_address` | `aml_core.account.blockchain_address` | PII-masked at API |
| `app.wallet_authorization.custody_type` | `aml_core.account.wallet_custody_type` / `is_hosted_wallet` | HOSTED/UNHOSTED/… |
| `app.wallet_authorization.authorized*` | `party_wallet.is_verified` + `verification_tx`/proof refs | policy-capped validity |
| `app.credential_check_dlq` | batch_job/job-run DLQ pattern | nightly T1_CREDENTIAL_STATUS |

Mapping rationale: the v5 account model splits "instrument" from "party
link", which is exactly the v2 `party_instrument` split; the authorization
registry's `authorized_until` maps to a policy cap on `party_wallet`
verification, not a new column class.

## 5. Verification

- `aml_detection/` suite green (56 tests) incl. capability gating +
  drift rendering.
- `backend/tests/` suite green (114) incl. gate ordering, risk factors,
  identity panels.
- Live AGE execution of the drift scenario remains deployment-time
  verification (no AGE runtime in this environment) — see ADR-0001's
  standing caveat.
