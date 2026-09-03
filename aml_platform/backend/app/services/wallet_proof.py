"""
Address-control proofs (AWI TASK-044).

Proves that an onboarding applicant controls an on-chain address by
verifying a signature over a platform-issued, single-use challenge:

  EVM    — EIP-191 `personal_sign`: keccak256("\\x19Ethereum Signed Message:\\n"
           + len + challenge), secp256k1 ECDSA recovery (eth-keys).
  Solana — Ed25519 over the UTF-8 challenge bytes (TASK-045 parity).

Challenges are single-use with a TTL; a completed or expired challenge can
never be replayed. Every outcome (success/failure/replay) is recorded with
a proof reference for the wallet_authorization registry.
"""

import hashlib
import secrets
import time
from typing import Optional

from app.core.exceptions import ValidationAppError

CHALLENGE_TTL_SECONDS = 600
_CHALLENGES: dict = {}  # challenge -> {address, expires_at, used}


def issue_challenge(address: str, blockchain: str = "ETHEREUM") -> dict:
    """Issue a single-use challenge bound to a specific address."""
    normalized = normalize_address(address, blockchain)
    challenge = f"AML-WALLET-BINDING:{blockchain}:{normalized}:{secrets.token_hex(16)}"
    _CHALLENGES[challenge] = {
        "address": normalized,
        "blockchain": blockchain,
        "expires_at": time.time() + CHALLENGE_TTL_SECONDS,
        "used": False,
    }
    # Opportunistic pruning of expired entries
    now = time.time()
    for key in [k for k, v in _CHALLENGES.items() if v["expires_at"] < now]:
        _CHALLENGES.pop(key, None)
    return {"challenge": challenge, "expires_in": CHALLENGE_TTL_SECONDS}


def normalize_address(address: str, blockchain: str) -> str:
    value = str(address or "").strip()
    if blockchain in ("ETHEREUM", "POLYGON", "TRON"):
        if not value or len(value) > 64:
            raise ValidationAppError("Invalid address for chain")
        return value.lower()
    if not value or len(value) > 64:
        raise ValidationAppError("Invalid address for chain")
    return value


def _consume_challenge(challenge: str, address: str) -> dict:
    entry = _CHALLENGES.get(challenge)
    if entry is None:
        raise ValidationAppError("Unknown or expired challenge")
    if entry["used"]:
        # Replay: burn it for everyone, then refuse.
        _CHALLENGES.pop(challenge, None)
        raise ValidationAppError("Challenge already used (replay rejected)")
    if time.time() > entry["expires_at"]:
        _CHALLENGES.pop(challenge, None)
        raise ValidationAppError("Challenge expired")
    if address != entry["address"]:
        raise ValidationAppError("Challenge was issued for a different address")
    entry["used"] = True
    return entry


def proof_ref(challenge: str, address: str) -> str:
    digest = hashlib.sha256(f"{challenge}:{address}".encode()).hexdigest()
    return f"sig:{digest[:32]}"


def verify_evm_signature(challenge: str, signature_hex: str) -> dict:
    """Verify an EIP-191 personal_sign signature over the challenge.

    Returns {address, proof_ref} on success; raises ValidationAppError on any
    failure (wrong key, replay, expired, malformed).
    """
    from eth_keys import keys
    from eth_utils import keccak, to_checksum_address

    sig_hex = str(signature_hex or "").removeprefix("0x").removeprefix("0X")
    if len(sig_hex) != 130:
        raise ValidationAppError("Signature must be 65-byte hex (r||s||v)")
    try:
        sig_bytes = bytes.fromhex(sig_hex)
    except ValueError:
        raise ValidationAppError("Signature is not valid hex")

    # EIP-191 personal_sign pre-image
    message = f"\x19Ethereum Signed Message:\n{len(challenge)}{challenge}".encode()
    digest = keccak(message)

    # normalize v (0/1 or 27/28) to recovery flag 0/1
    v = sig_bytes[64]
    if v in (27, 28):
        v = v - 27
    if v not in (0, 1):
        raise ValidationAppError("Invalid recovery id in signature")

    try:
        signature = keys.Signature(vrs=(v, int.from_bytes(sig_bytes[:32], "big"),
                                        int.from_bytes(sig_bytes[32:64], "big")))
        public = signature.recover_public_key_from_msg_hash(digest)
    except Exception:
        raise ValidationAppError("Signature recovery failed")

    address = public.to_checksum_address()
    entry = _consume_challenge(challenge, address.lower())
    return {
        "address": address,
        "blockchain": entry["blockchain"],
        "proof_ref": proof_ref(challenge, address.lower()),
    }


def verify_solana_signature(challenge: str, signature_base58: str, address: str) -> dict:
    """Verify an Ed25519 signature over the raw challenge bytes (TASK-045)."""
    import base64

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        sig = base58_decode(str(signature_base58))
        pub = base58_decode(str(address))
    except Exception:
        raise ValidationAppError("Invalid base58 signature/address")

    normalized = normalize_address(address, "SOLANA")
    entry = _consume_challenge(challenge, normalized)
    try:
        Ed25519PublicKey.from_public_bytes(pub).verify(sig, challenge.encode())
    except Exception:
        raise ValidationAppError("Ed25519 signature verification failed")
    return {"address": address, "blockchain": "SOLANA", "proof_ref": proof_ref(challenge, normalized)}


_BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def base58_decode(value: str) -> bytes:
    num = 0
    for ch in value:
        num = num * 58 + _BASE58_ALPHABET.index(ch)
    raw = num.to_bytes((num.bit_length() + 7) // 8, "big")
    pad = len(value) - len(value.lstrip("1"))
    return b"\x00" * pad + raw
