from typing import Any, Dict, List, Union

SENSITIVE_FIELDS = {
    "entity_name",
    "wallet_address",
    "email",
    "phone_number",
    "sender_account",
    "receiver_account",
    "sender_wallet",
    "receiver_wallet"
}

def mask_value(field: str, value: Any) -> Any:
    """
    Apply masking logic to a specific field value.
    """
    if not value or not isinstance(value, str):
        return value
    
    if field in {"wallet_address", "sender_wallet", "receiver_wallet"}:
        # Keep prefix and suffix, mask the middle (standard crypto UI practice)
        if len(value) > 10:
            return f"{value[:6]}...{value[-4:]}"
        return "***REDACTED***"
    
    return "***REDACTED***"

def mask_pii(data: Union[Dict[str, Any], List[Dict[str, Any]]], user_role: str) -> Any:
    """
    Recursively mask PII in dictionaries or lists based on user role.
    Only SENIOR_INVESTIGATOR can see unmasked data.
    """
    if user_role == "SENIOR_INVESTIGATOR":
        return data

    if isinstance(data, list):
        return [mask_pii(item, user_role) for item in data]
    
    if isinstance(data, dict):
        masked_item = {}
        for k, v in data.items():
            if k in SENSITIVE_FIELDS:
                masked_item[k] = mask_value(k, v)
            elif isinstance(v, (dict, list)):
                masked_item[k] = mask_pii(v, user_role)
            else:
                masked_item[k] = v
        return masked_item
    
    return data
