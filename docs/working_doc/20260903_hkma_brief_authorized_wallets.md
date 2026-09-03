# HKMA Architecture Brief — Authorized-Wallet Mechanism (AWI TASK-058)

Date: 2026-09-03 · Status: **DRAFT for compliance/legal sign-off**
(replaces the earlier brief section referenced in the feasibility study;
the mechanism is described here in full so the stablecoin-licence
application package carries one canonical statement).

## 1. Summary of the mechanism

The platform can onboard "authorized wallets" — fiat accounts and
stablecoin/crypto wallets whose controlling party has completed KYC/KYB —
through a W3C DID/Verifiable-Credentials identity layer (the in-group HKT
Trusted-Identity CDP edge):

1. A KYC/KYB credential issued by an accredited issuer is verified
   machine-to-machine (`/m2m/verify`) against the issuer's signature, the
   trust registry, and the credential's revocation status.
2. Address control is proven by a challenge-signature over the wallet key
   (EVM / Solana).
3. A wallet-binding credential (`hkt_wallet_binding_v1`) binds the subject
   to a hashed address with a custody type and a validity window.
4. The authorization state is **time-bounded** (`authorized_until` = min of
   credential expiry and the policy cap) and **revocable at any time** —
   revocation/expiry is detected by a nightly re-verification batch and by
   status-list checks on every verification, giving kill-switch semantics.

## 2. Risk-signal framing (the regulatory position)

Authorized-wallet status is **one input into risk scoring and alert
priority** — it is deliberately NOT a monitoring exemption. The platform
commits to:

- **Screening always runs.** Sanctions screening (OFAC etc.) and the
  internal revoked-credential blocklist apply to authorized wallets exactly
  as to everyone else. Automated tests assert there is no code path that
  skips screening based on authorization (TASK-050).
- **Typology detection always runs.** Verified wallets still generate
  typology alerts (structuring, circular flow, cross-rail layering,
  authorization drift). Authorization modulates priority and scoring
  inputs only (TASK-051); tests assert no suppression path exists.
- **An alert may only be cleared with documented rationale** (HKMA
  principle in the platform README): an authorization status is evidence
  supporting a clear decision, never a silent dismissal.
- **Bounded validity and revocation.** Every authorization carries an
  explicit expiry; revoked credentials de-authorize the wallet at the next
  verification/batch check and feed the internal blocklist
  (Cap.656-style blacklisting duty), raising a CRITICAL `CREDENTIAL_REVOKED`
  alert at the gate (TASK-049).
- **Full audit trail.** Every onboarding verification, grant, revocation
  and unmask is recorded in the hash-chained audit log with actor,
  evidence hash and justification — reconstructible for HKMA/JFIU review.

## 3. Alignment with the legal framework

| Requirement | How the mechanism supports it |
|---|---|
| AMLO Cap.615 Sch.2 CDD/EDD | Credential from an accredited issuer = corroborating evidence for CDD; platform keeps its own CDD record (spec §1.3: KYC/KYB consumed from provider) |
| Stablecoins Ordinance Cap.656 (unhosted-wallet EDD) | Binding credential records custody type; unhosted wallets stay subject to enhanced monitoring — authorization never downgrades unhosted treatment |
| Cap.656 blacklisting/freezing duty | Revoked credentials → internal blocklist + CRITICAL alert at the pre-graph gate |
| FATF R.15/16 beneficiary verification | Verified counterparty VASPs carry licensed-institution/corporate credentials; trust registry enumerates accredited issuers |
| HKMA record-keeping & audit | Evidence hashes, validity windows, issuer DIDs retained; `audit/verify` recomputes the tamper-evident chain |

## 4. Policy statement (versioned)

> **Authorized-wallet policy v1.0 (2026-09-03).** An authorized wallet is a
> wallet whose controlling party holds a valid, unrevoked KYC/KYB and
> binding credential from an issuer accredited by the platform's trust
> registry, with address control proven by signature. Authorization:
> (a) is time-bounded and revocable; (b) feeds risk scoring and alert
> priority; (c) NEVER exempts a wallet from sanctions screening, internal
> blocklist screening, or typology detection; (d) is granted and revoked
> through maker-checker with documented justification; (e) every step is
> audited. Any change to (b) or (c) requires compliance sign-off and a
> re-issue of this statement.

## 5. Sign-off

| Role | Name | Date | Status |
|---|---|---|---|
| Compliance | — | — | pending |
| Legal | — | — | pending |
| MLRO | — | — | pending |
