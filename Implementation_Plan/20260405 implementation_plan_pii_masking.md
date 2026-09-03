# Implementation Plan: Role-Based PII Masking

Implement a security layer that masks sensitive Personal Identifiable Information (PII) in API responses based on the user's role (`JUNIOR_ANALYST` vs. `SENIOR_INVESTIGATOR`).

## User Review Required

> [!IMPORTANT]
> **Masking Logic**: Junior Analysts will see redacted strings (e.g., `***REDACTED***` or `0xabc...efg`) for sensitive fields like `entity_name` and `wallet_address`. Senior Investigators will see full data, but every access will be logged in the audit trail.

## Proposed Changes

### Backend: PII Service & Middleware

#### [NEW] [pii_service.py](file:///z:/GITHUB/Overwatch/aml_platform/backend/app/services/pii_service.py)
- Create a utility service to mask sensitive fields in dictionaries or lists of dictionaries.
- Define "Sensitive Fields": `entity_name`, `wallet_address`, `email`, `phone_number`.

#### [MODIFY] [alerts.py](file:///z:/GITHUB/Overwatch/aml_platform/backend/app/api/v1/alerts.py)
- Integrate `mask_pii` into the `get_alerts` and `get_alert_detail` endpoints.
- Pass the `current_user` role to the masking service.

#### [MODIFY] [graph.py](file:///z:/GITHUB/Overwatch/aml_platform/backend/app/api/v1/graph.py)
- Ensure node data returned for visual investigation is masked for non-senior roles.

#### [MODIFY] [auth.py](file:///z:/GITHUB/Overwatch/aml_platform/backend/app/core/auth.py)
- Add a helper to log "Unmasking Events" when a senior investigator views raw PII.

## Verification Plan

### Automated Tests
- Create a scratch script `test_pii_masking.py` to:
    1. Simulate a `JUNIOR_ANALYST` request and verify fields are masked.
    2. Simulate a `SENIOR_INVESTIGATOR` request and verify fields are clear.
    3. Verify an audit log entry is created for the senior request.

### Manual Verification
- Test via `curl` using the mock tokens defined in `auth.py`:
    - `compliance_analyst_token` (Junior)
    - `senior_investigator_token` (Senior)
