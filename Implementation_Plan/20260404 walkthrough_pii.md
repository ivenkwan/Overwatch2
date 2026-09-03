# Walkthrough: Role-Based PII Masking Implementation

I have successfully implemented the **Role-Based PII Masking** layer to ensure data privacy and regulatory compliance in the AML platform.

## Changes Made

### 1. PII Masking Service
Created a new [pii_service.py](file:///z:/GITHUB/Overwatch/aml_platform/backend/app/services/pii_service.py) that provides a recursive redaction engine.
- **Junior Analysts**: Sensitive fields (Name, Wallet, Email) are replaced with `***REDACTED***` or truncated hashes.
- **Senior Investigators**: Data is kept intact for investigations.

### 2. Audit Trail Integration
Modified [auth.py](file:///z:/GITHUB/Overwatch/aml_platform/backend/app/core/auth.py) to include `log_unmasking_event`.
- Every time unmasked data is served to a Senior role, a high-integrity audit event is logged.

### 3. API Router Enforcement
- **Alerts Router**: Redacts sensitive data in both list and detail views.
- **Graph Router**: Redacts neighbor node data and path tracing results.

## Verification Results

I ran a dedicated [test suite](file:///z:/GITHUB/Overwatch/aml_platform/tmp/test_pii.py) to verify the logic:

```bash
--- Testing JUNIOR_ANALYST ---
Masked Alert: {'id': 1, 'entity_name': '***REDACTED***', 'wallet_address': '0x1234...5678', ...}
SUCCESS: Junior masking verified.

--- Testing SENIOR_INVESTIGATOR ---
Unmasked Alert: {'id': 1, 'entity_name': 'John Doe', 'wallet_address': '0x1234567890abcdef...', ...}
SUCCESS: Senior unmasking verified.

ALL PII TESTS PASSED.
```

## Next Steps
- Implement **Production Hardening** (Environment Variables for DB/JWT secrets).
- Enhance **Graph Explorer** to handle node clustering for large datasets ($10,000+$ edges).
