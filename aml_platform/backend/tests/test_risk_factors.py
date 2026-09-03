"""AWI TASK-051: verification-state risk factors (pure computation)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.risk_factors import compute_factors

NOW = datetime(2026, 9, 3, tzinfo=timezone.utc)


def _auth(**over):
    row = {
        "wallet_address": "0xabc",
        "authorized": True,
        "binding_level": "ADDRESS_PROOF_VERIFIED",
        "custody_type": "UNHOSTED",
        "binding_credential": "cred_1",
    }
    row.update(over)
    return row


def _cred(**over):
    row = {
        "credential_id": "cred_1",
        "issuer_did": "did:web:issuer.hkt",
        "status": "ACTIVE",
        "expires_at": NOW + timedelta(days=365),
        "jurisdiction": "HK",
        "revocation_history": [],
    }
    row.update(over)
    return row


def test_well_verified_hosted_wallet_is_low_risk():
    factors = compute_factors(_auth(binding_level="ISSUER_ATTESTED", custody_type="HOSTED"),
                              _cred(), now=NOW,
                              accredited_issuers={"did:web:issuer.hkt"})
    d = factors.to_dict()
    assert d["verification_level"] == 0.0
    assert d["issuer_risk"] == 0.0
    assert d["custody_risk"] == 0.1
    assert d["jurisdiction_risk"] == 0.0
    assert d["expiry_proximity"] == 0.0
    assert d["revocation_history"] == 0.0


def test_revoked_credential_maximises_expiry_and_history():
    factors = compute_factors(_auth(), _cred(status="REVOKED", revocation_history=["2026-08-01"]),
                              now=NOW)
    assert factors.expiry_proximity == 1.0
    assert factors.revocation_history == 1.0
    assert factors.composite() > 0.4  # clearly elevated vs the clean baseline (0.13)


def test_expiry_ramp_over_final_90_days():
    factors = compute_factors(_auth(), _cred(expires_at=NOW + timedelta(days=30)), now=NOW)
    assert 0.0 < factors.expiry_proximity < 1.0
    assert factors.expiry_proximity == pytest.approx(1.0 - 30 / 90)

    factors_expired = compute_factors(_auth(), _cred(expires_at=NOW - timedelta(days=1)), now=NOW)
    assert factors_expired.expiry_proximity == 1.0


def test_unaccredited_issuer_raises_issuer_risk():
    factors = compute_factors(_auth(), _cred(issuer_did="did:web:rogue.example"),
                              now=NOW, accredited_issuers={"did:web:issuer.hkt"})
    assert factors.issuer_risk == 1.0


def test_missing_rows_are_risk_raising_not_risk_free():
    factors = compute_factors(None, None, now=NOW)
    # Unknown everything: verification level + custody default upward.
    assert factors.verification_level == 0.8
    assert factors.custody_risk == 0.7
    assert factors.composite() > 0.4


def test_high_risk_jurisdiction_flag():
    factors = compute_factors(_auth(), _cred(jurisdiction="XX"),
                              now=NOW, high_risk_jurisdictions={"XX"})
    assert factors.jurisdiction_risk == 1.0


def test_no_typology_suppression_path_exists():
    """ADR-0002 invariant: risk factors only modulate; the module must not
    expose any skip/suppress decision (docstrings are stripped — they state
    the policy in prose)."""
    import inspect
    import app.services.risk_factors as rf

    source = inspect.getsource(rf)
    if rf.__doc__:
        source = source.replace(inspect.cleandoc(rf.__doc__), "")
    for forbidden in ("suppress", "skip_rule", "exempt", "bypass", "def skip"):
        assert forbidden not in source.lower(), f"risk_factors must not {forbidden!r}"
