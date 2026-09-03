"""
Verification-state risk factors (AWI TASK-051).

Consumes the authorized-wallet registry (`app.wallet_authorization`) and the
verified-credential store (`app.party_credential`) to compute counterparty
risk signals for the future unified risk-scoring engine (v5 B.2.3). Pure and
deterministic — no DB here; the caller passes rows.

POLICY (ADR-0002 / feasibility §4.1):
  * these factors only ever modulate ALERT PRIORITY / score inputs;
  * they NEVER suppress typology execution or screening — there is no
    code path here that can skip a rule (asserted by tests);
  * every factor is bounded to [0, 1] so the engine can weight it safely.

Factors returned (0 = lowest risk, 1 = highest):
  verification_level     inverse of binding level (ISSUER_ATTESTED lowest)
  issuer_risk            unaccredited/unknown issuer raises risk
  custody_risk           UNHOSTED > HOSTED (hosted is lower risk)
  jurisdiction_risk      higher-risk jurisdiction flag input (0/1)
  expiry_proximity       days-to-expiry -> 1 when expired/revoked
  revocation_history     any past revocation on the credential raises risk
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

BINDING_LEVEL_RISK = {
    "ISSUER_ATTESTED": 0.0,
    "ADDRESS_PROOF_VERIFIED": 0.15,
    "SELF_ASSERTED": 0.6,
    None: 0.8,
}

CUSTODY_RISK = {
    "HOSTED": 0.1,
    "EXCHANGE_CUSTODIED": 0.2,
    "MULTI_SIG": 0.35,
    "UNHOSTED": 0.5,
    None: 0.7,
}

HIGH_RISK_JURISDICTIONS: frozenset = frozenset()  # populated by policy; empty = no flag


@dataclass(frozen=True)
class VerificationRiskFactors:
    verification_level: float
    issuer_risk: float
    custody_risk: float
    jurisdiction_risk: float
    expiry_proximity: float
    revocation_history: float

    def composite(self) -> float:
        """Unweighted mean — the scoring engine applies its own weights."""
        values = (
            self.verification_level,
            self.issuer_risk,
            self.custody_risk,
            self.jurisdiction_risk,
            self.expiry_proximity,
            self.revocation_history,
        )
        return sum(values) / len(values)

    def to_dict(self) -> dict[str, float]:
        return {
            "verification_level": self.verification_level,
            "issuer_risk": self.issuer_risk,
            "custody_risk": self.custody_risk,
            "jurisdiction_risk": self.jurisdiction_risk,
            "expiry_proximity": self.expiry_proximity,
            "revocation_history": self.revocation_history,
            "composite": self.composite(),
        }


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def compute_factors(
    authorization: Optional[dict[str, Any]],
    credential: Optional[dict[str, Any]],
    *,
    now: Optional[datetime] = None,
    accredited_issuers: Optional[set[str]] = None,
    high_risk_jurisdictions: Optional[set[str]] = None,
) -> VerificationRiskFactors:
    """Compute risk factors for one wallet from its authorization row and
    its active credential row (None when absent = risk-raising unknown)."""
    now = now or datetime.now(timezone.utc)

    # --- verification / binding level -------------------------------------
    binding_level = None
    if authorization:
        binding_level = authorization.get("binding_level") or authorization.get("bindingLevel")
    verification_level = BINDING_LEVEL_RISK.get(binding_level, 0.8)

    # --- issuer accreditation ---------------------------------------------
    issuer_did = (credential or {}).get("issuer_did")
    issuer_risk = 0.0
    if accredited_issuers is not None:
        issuer_risk = 0.0 if issuer_did in accredited_issuers else 1.0
    elif issuer_did is None:
        issuer_risk = 1.0  # unknown issuer
    else:
        issuer_risk = 0.2  # present but accreditation unverified at this layer

    # --- custody ------------------------------------------------------------
    custody = None
    if authorization:
        custody = authorization.get("custody_type") or authorization.get("custodyType")
    custody_risk = CUSTODY_RISK.get(custody, 0.7)

    # --- jurisdiction --------------------------------------------------------
    jurisdiction = None
    if credential:
        jurisdiction = credential.get("jurisdiction")
    jurisdictions = high_risk_jurisdictions or HIGH_RISK_JURISDICTIONS
    jurisdiction_risk = 1.0 if jurisdiction in jurisdictions else 0.0

    # --- expiry proximity ----------------------------------------------------
    expiry_proximity = 0.0
    status = (credential or {}).get("status", "ACTIVE")
    if status in ("REVOKED", "EXPIRED"):
        expiry_proximity = 1.0
    else:
        expires_at = None
        if credential:
            expires_at = credential.get("expires_at")
        if isinstance(expires_at, datetime):
            remaining = (expires_at - now).total_seconds()
            if remaining <= 0:
                expiry_proximity = 1.0
            else:
                # Linear ramp over the final 90 days.
                days_left = remaining / 86400.0
                expiry_proximity = _clamp(1.0 - days_left / 90.0) if days_left <= 90 else 0.0

    # --- revocation history ---------------------------------------------------
    revocation_history = 0.0
    if credential:
        history = credential.get("revocation_history") or []
        if isinstance(history, (list, tuple)) and history:
            revocation_history = 1.0
        elif credential.get("status") == "REVOKED":
            revocation_history = 1.0

    return VerificationRiskFactors(
        verification_level=verification_level,
        issuer_risk=issuer_risk,
        custody_risk=custody_risk,
        jurisdiction_risk=jurisdiction_risk,
        expiry_proximity=expiry_proximity,
        revocation_history=revocation_history,
    )
