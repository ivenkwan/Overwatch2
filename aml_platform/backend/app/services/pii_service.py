"""
PII masking service (TASK-005).

Role-based, field-level masking applied at the API response layer:

- Roles are ranked: JUNIOR_ANALYST < SENIOR_INVESTIGATOR < DEPARTMENT_HEAD < ADMIN.
- Each sensitive field declares the minimum role allowed to see it raw and a
  masking strategy applied to everyone below that rank:
    * ``redact``  — replace with ***REDACTED***
    * ``partial`` — keep a short prefix/suffix (wallet-style UI practice)
    * ``hash``    — deterministic SHA-256 token (same value -> same token, so
                    analysts can still correlate rows without seeing the value)
- SENIOR_INVESTIGATOR and above see raw values for all sensitive fields;
  call sites are responsible for the audited-unmask trail
  (audit_service.log_unmasking_event) as before.
"""

import hashlib
from typing import Any, Dict, List, Union

ROLE_RANK = {
    "JUNIOR_ANALYST": 1,
    "SENIOR_INVESTIGATOR": 2,
    "DEPARTMENT_HEAD": 3,
    "ADMIN": 4,
}

# field -> (min_role_for_raw, strategy)
FIELD_POLICY: Dict[str, tuple] = {
    "entity_name": ("SENIOR_INVESTIGATOR", "hash"),
    "wallet_address": ("SENIOR_INVESTIGATOR", "partial"),
    "sender_wallet": ("SENIOR_INVESTIGATOR", "partial"),
    "receiver_wallet": ("SENIOR_INVESTIGATOR", "partial"),
    "email": ("SENIOR_INVESTIGATOR", "hash"),
    "phone_number": ("SENIOR_INVESTIGATOR", "redact"),
    "sender_account": ("SENIOR_INVESTIGATOR", "partial"),
    "receiver_account": ("SENIOR_INVESTIGATOR", "partial"),
    "customer_num": ("JUNIOR_ANALYST", "hash"),
    "counterparty_id": ("JUNIOR_ANALYST", "hash"),
    # Credential-claim fields (AWI TASK-041)
    "givenName": ("SENIOR_INVESTIGATOR", "redact"),
    "nationality": ("SENIOR_INVESTIGATOR", "redact"),
    "jurisdiction": ("SENIOR_INVESTIGATOR", "redact"),
    "vaspLicenseRef": ("SENIOR_INVESTIGATOR", "partial"),
    "walletAddressHash": ("JUNIOR_ANALYST", "hash"),
    "proofRef": ("SENIOR_INVESTIGATOR", "partial"),
}

# Backwards-compatible set (previous callers referenced SENSITIVE_FIELDS)
SENSITIVE_FIELDS = set(FIELD_POLICY)


def _role_rank(user_role: str) -> int:
    return ROLE_RANK.get(user_role, 0)


def mask_value(field: str, value: Any) -> Any:
    """Apply the field's masking strategy to one value."""
    if not value or not isinstance(value, str):
        return value
    strategy = FIELD_POLICY.get(field, ("", "redact"))[1]
    if strategy == "partial":
        if len(value) > 10:
            return f"{value[:6]}...{value[-4:]}"
        return "***REDACTED***"
    if strategy == "hash":
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
        return f"sha256:{digest}"
    return "***REDACTED***"


def mask_pii(data: Union[Dict[str, Any], List[Dict[str, Any]], Any], user_role: str) -> Any:
    """Recursively mask PII in dicts/lists based on the role/field policy.

    SENIOR_INVESTIGATOR and above receive data untouched; everyone else gets
    each sensitive field masked per its strategy.
    """
    if _role_rank(user_role) >= ROLE_RANK["SENIOR_INVESTIGATOR"]:
        return data

    if isinstance(data, list):
        return [mask_pii(item, user_role) for item in data]

    if isinstance(data, dict):
        masked_item = {}
        for k, v in data.items():
            if k in FIELD_POLICY:
                min_role = FIELD_POLICY[k][0]
                masked_item[k] = (
                    v if _role_rank(user_role) >= ROLE_RANK[min_role] else mask_value(k, v)
                )
            elif isinstance(v, (dict, list)):
                masked_item[k] = mask_pii(v, user_role)
            else:
                masked_item[k] = v
        return masked_item

    return data
