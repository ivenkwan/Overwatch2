# ADR-0002: DID/VC Authorized-Wallet Integration

- **Status**: Accepted
- **Date**: 2026-09-03
- **Deciders**: Platform engineering, Compliance
- **Sources**: [Feasibility study](../../docs/feasability.md) · [ADR-0001](0001-unified-detection-engine.md) · [AWI program tasks](../../todo.md)

## Context

The Overwatch AML platform monitors fiat and stablecoin flows, but wallets are
pseudonymous: the party/UBO dimension (`aml_platform/init-scripts/06-party-ubo-model.sql`)
has no producer, screening is deny-list only, and no risk-scoring engine consumes
identity. The `didvc/` module (unomi-did-vc) provides a substantially built
W3C DID/Verifiable Credentials layer — SD-JWT VC issuance/verification, a
stateless M2M verification API, issuer trust registry, and Bitstring Status
List revocation. The v5 build specification already reserves an upstream
"KYC/KYB Provider (Webhook + REST pull)" seam.

The feasibility study (2026-09-03) concluded: **feasible with conditions**,
recommending a hybrid architecture.

## Decision

Adopt **Option C — hybrid**:

1. **didvc as the upstream KYC/KYB verification provider** consumed through
   `POST /{tenant}/m2m/verify[-batch]` (API-key, stateless) at the reserved
   v5 seam. The AML platform never re-implements credential verification.
2. **Address-control proof performed by the AML platform**: the applicant
   signs a platform-issued challenge with the on-chain wallet key
   (EIP-191 `personal_sign` for EVM; Ed25519 message signature for Solana),
   closing feasibility gap G1 without waiting for did:pkh support upstream.
3. **`hkt_wallet_binding_v1` credential schema** (hash-identified address,
   chain, custody type, binding level, validity) closing gap G2, registered
   in didvc's schema whitelist and verified via the same M2M path.
4. **Authorization is a risk signal, never a control exemption**: verified
   wallets are still screened and still generate typology hits — only alert
   priority and scoring inputs change (feasability.md §4.1).
5. Rollout follows the phased AWI program (Phase 0–4 in todo.md); ADR-0001's
   abstract detection registry hosts any identity-aware scenario, gated on a
   new `AUTHORIZATION_DIMENSION` capability.

## Options considered

| | A — M2M only | B — OID4VP wallet-presented | **C — hybrid (chosen)** |
|---|---|---|---|
| didvc code changes | none | none | + wallet-binding schema |
| Proves address control | ✗ | ✗ | ✓ (challenge signature) |
| Needs holder wallet ecosystem | no | yes | no |
| Time to first value | lowest | high | medium (phased) |

## Consequences

- **Positive**: first real producer for the party/UBO dimension (unblocks
  `SCN_CROSS_RAIL_LAYER_01`); machine-verifiable, revocable, auditable
  identity evidence; strategic fit with the AnchorPoint/HKT identity CDP.
- **Negative / obligations**: cross-stack operation (Java edge beside the
  Python platform); production dependency on didvc is gated on closing its
  security findings (F-7/F-8/F-9/F-10/F-12) and a penetration test; nightly
  credential re-verification adds an operational job; issuer ecosystem
  bootstraps first-party (in-group CDP) before third parties.
- **Guardrails**: authorization changes go through maker-checker and the
  forensic audit trail (Lesson 6: never a single enforcement point);
  credential claims render through the PII masking service.

## Compliance

- `Aml-Platform-Compliance`: HKMA risk-based framing; authorization never
  exempts screening or typology execution — asserted by automated tests
  (TASK-050) and stated in the licence-application architecture brief
  (TASK-058).
