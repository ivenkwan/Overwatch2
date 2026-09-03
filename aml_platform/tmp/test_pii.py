import sys
import os

# Mock the app structure for testing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from app.services.pii_service import mask_pii

# Test Data
test_alerts = [
    {
        "id": 1,
        "entity_name": "John Doe",
        "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
        "severity": "HIGH",
        "metadata": {
            "email": "john@example.com",
            "phone": "555-0199"
        }
    }
]

def test_junior_masking():
    print("--- Testing JUNIOR_ANALYST ---")
    masked = mask_pii(test_alerts, "JUNIOR_ANALYST")
    alert = masked[0]
    
    assert alert["entity_name"] == "***REDACTED***"
    assert alert["wallet_address"] == "0x1234...5678" # 0x + 4 chars ... 4 chars
    # Nested check (mock service doesn't handle all nested keys but let's see)
    print(f"Masked Alert: {alert}")
    print("SUCCESS: Junior masking verified.")

def test_senior_unmasking():
    print("\n--- Testing SENIOR_INVESTIGATOR ---")
    unmasked = mask_pii(test_alerts, "SENIOR_INVESTIGATOR")
    alert = unmasked[0]
    
    assert alert["entity_name"] == "John Doe"
    assert alert["wallet_address"] == "0x1234567890abcdef1234567890abcdef12345678"
    print(f"Unmasked Alert: {alert}")
    print("SUCCESS: Senior unmasking verified.")

if __name__ == "__main__":
    try:
        test_junior_masking()
        test_senior_unmasking()
        print("\nALL PII TESTS PASSED.")
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
