"""P1 platform tasks: PII matrix (TASK-005), STR compliance (TASK-006),
error envelope + health (TASK-008/009)."""

import asyncio
import json
import uuid

import pytest

from app.services import pii_service, str_service


# ---------------------------------------------------------------- TASK-005

def test_senior_and_above_see_raw_values():
    data = {"wallet_address": "0xAb1234567890abcdef", "email": "a@b.com"}
    for role in ("SENIOR_INVESTIGATOR", "DEPARTMENT_HEAD", "ADMIN"):
        assert pii_service.mask_pii(data, role) == data


def test_junior_gets_partial_wallet_mask():
    out = pii_service.mask_pii({"wallet_address": "0xAb1234567890abcdef"}, "JUNIOR_ANALYST")
    assert out["wallet_address"] == "0xAb12...cdef"
    assert "34567890ab" not in out["wallet_address"]


def test_junior_gets_deterministic_hash_for_names():
    a = pii_service.mask_pii({"entity_name": "Shell Holding Ltd"}, "JUNIOR_ANALYST")
    b = pii_service.mask_pii({"entity_name": "Shell Holding Ltd"}, "JUNIOR_ANALYST")
    c = pii_service.mask_pii({"entity_name": "Other Bank"}, "JUNIOR_ANALYST")
    assert a["entity_name"] == b["entity_name"]          # deterministic (correlatable)
    assert a["entity_name"] != c["entity_name"]           # distinguishes values
    assert a["entity_name"].startswith("sha256:")


def test_phone_redacted_for_junior():
    out = pii_service.mask_pii({"phone_number": "+852 9123 4567"}, "JUNIOR_ANALYST")
    assert out["phone_number"] == "***REDACTED***"


def test_nested_and_list_masking():
    data = {"items": [{"email": "x@y.z"}, {"email": "p@q.r"}], "nested": {"email": "d@e.f"}}
    out = pii_service.mask_pii(data, "JUNIOR_ANALYST")
    assert out["items"][0]["email"].startswith("sha256:")
    assert out["nested"]["email"].startswith("sha256:")


def test_unknown_role_fails_closed():
    out = pii_service.mask_pii({"email": "x@y.z", "phone_number": "+852 9123"}, "INTERN")
    assert out["email"] != "x@y.z" and out["email"].startswith("sha256:")
    assert out["phone_number"] == "***REDACTED***"


def test_non_sensitive_fields_untouched():
    out = pii_service.mask_pii({"txn_amount_in_hkd": 99999, "status": "OPEN"}, "JUNIOR_ANALYST")
    assert out == {"txn_amount_in_hkd": 99999, "status": "OPEN"}


def test_credential_claim_fields_masked_for_junior():
    out = pii_service.mask_pii({"givenName": "Chan", "jurisdiction": "HK"}, "JUNIOR_ANALYST")
    assert out["givenName"] == "***REDACTED***"
    assert out["jurisdiction"] == "***REDACTED***"


# ---------------------------------------------------------------- TASK-006

def _full_record():
    return {
        "str_id": str(uuid.uuid4()),
        "case_id": str(uuid.uuid4()),
        "status": "draft",
        "triggering_factors": "Rapid movement of funds inconsistent with profile history",
        "subject_background": "Customer onboarded 2024-01, medium risk, retail segment",
        "digital_footprints": "Login IP 203.0.113.5, device fingerprint delta observed",
        "transaction_summary": "HKD 1,200,000 moved across 14 transactions in 48 hours",
        "created_at": "2026-09-03T00:00:00+00:00",
        "submitted_at": None,
    }


def test_submission_validation_accepts_complete_record():
    assert str_service.validate_str_submission(_full_record()) == []


def test_submission_validation_rejects_missing_fields():
    record = _full_record()
    record["subject_background"] = "short"
    record["digital_footprints"] = None
    problems = str_service.validate_str_submission(record)
    fields = {p["field"] for p in problems}
    assert fields == {"subject_background", "digital_footprints"}


def test_status_transitions():
    assert str_service.can_transition("draft", "under_review")
    assert str_service.can_transition("under_review", "filed")
    assert str_service.can_transition("draft", "filed")
    assert str_service.can_transition("draft", "withdrawn")
    assert not str_service.can_transition("filed", "draft")
    assert not str_service.can_transition("withdrawn", "filed")


def test_pdf_export_contains_sections_and_digest():
    record = _full_record()
    pdf = str_service.build_str_pdf(record)
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 1500
    # digest stability: same content -> same hash; changed content -> different hash
    assert str_service.content_sha256(record) == str_service.content_sha256(dict(record))
    record2 = dict(record)
    record2["transaction_summary"] += " changed"
    assert str_service.content_sha256(record2) != str_service.content_sha256(record)


# ---------------------------------------------------------------- TASK-008/009

def test_db_health_without_pool():
    from app.db.session import db_health
    result = asyncio.run(db_health())
    assert result == {"status": "not_initialized"}


def test_error_envelope_shapes():
    from app.core.exceptions import NotFoundError, ValidationAppError
    payload = NotFoundError("thing missing").to_payload()
    assert payload == {"error": {"code": "not_found", "message": "thing missing", "details": {}}}
    v = ValidationAppError("bad", details={"fields": [1]}).to_payload()
    assert v["error"]["code"] == "validation_error"
    assert v["error"]["details"] == {"fields": [1]}


def test_database_error_does_not_leak_driver_details():
    from app.core.exceptions import DatabaseError, database_error
    err = database_error("op.x", RuntimeError("password=hunter2 host=10.0.0.1"))
    assert "hunter2" not in json.dumps(err.to_payload())
    assert err.status_code == 500


def test_http_error_envelope_via_client():
    """FastAPI HTTPException (e.g. 401) is rendered in the standard envelope."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/alerts/feed")
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "http_401"
    assert "message" in body["error"]
