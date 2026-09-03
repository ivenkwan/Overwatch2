"""
didvc-edge M2M verification client (AWI TASK-037).

Wraps POST /{tenant}/m2m/verify and /m2m/verify-batch:
  * base URL + API key from Settings (environment only — no literals)
  * per-call timeout, bounded retries with backoff (idempotent GETs/verifies)
  * a circuit breaker that fails closed (wallet stays unauthorized) after
    consecutive upstream failures, re-probing after a cool-down
  * an evidence hash (SHA-256 of the normalized response) recorded with every
    verification so decisions stay reconstructible

Design constraint: this service NEVER decides trust itself — signature,
issuer-trust and revocation checks all happen inside didvc-edge. Here we
only transport the credential and persist the outcome.
"""

import hashlib
import json
import time
from typing import Any, Optional

import httpx

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError, ServiceUnavailableError, ValidationAppError

# Circuit breaker states
_FAILURE_THRESHOLD = 5
_COOLDOWN_SECONDS = 30.0

_state = {"failures": 0, "opened_at": 0.0}


def _reset_breaker() -> None:
    _state["failures"] = 0
    _state["opened_at"] = 0.0


def _breaker_open() -> bool:
    if _state["failures"] < _FAILURE_THRESHOLD:
        return False
    if time.monotonic() - _state["opened_at"] > _COOLDOWN_SECONDS:
        # half-open: allow one probe
        _state["opened_at"] = time.monotonic()
        return False
    return True


def _record_failure() -> None:
    _state["failures"] += 1
    if _state["failures"] == _FAILURE_THRESHOLD:
        _state["opened_at"] = time.monotonic()


def _evidence_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _client() -> httpx.AsyncClient:
    settings = get_settings()
    if not settings.identity_provider_url:
        raise ServiceUnavailableError(
            "Identity provider not configured (IDENTITY_PROVIDER_URL)"
        )
    if not settings.identity_provider_api_key:
        raise ServiceUnavailableError(
            "Identity provider not configured (IDENTITY_PROVIDER_API_KEY)"
        )
    return httpx.AsyncClient(timeout=settings.identity_provider_timeout)


def _headers() -> dict:
    return {"X-Api-Key": get_settings().identity_provider_api_key,
            "Content-Type": "application/json"}


async def _post(path: str, payload: dict) -> dict:
    settings = get_settings()
    if not settings.identity_provider_url or not settings.identity_provider_api_key:
        raise ServiceUnavailableError(
            "Identity provider not configured (IDENTITY_PROVIDER_URL / IDENTITY_PROVIDER_API_KEY)"
        )
    if _breaker_open():
        raise ServiceUnavailableError(
            "Identity provider circuit breaker open (recent consecutive failures)"
        )
    url = f"{settings.identity_provider_url.rstrip('/')}/{settings.identity_provider_tenant}{path}"
    last_exc: Optional[Exception] = None
    for attempt in range(settings.identity_provider_retries + 1):
        try:
            async with _client() as client:
                response = await client.post(url, json=payload, headers=_headers())
            if response.status_code >= 500:
                raise httpx.HTTPStatusError("upstream 5xx", request=response.request,
                                            response=response)
            if response.status_code >= 400:
                # 4xx is a definitive answer (invalid credential etc.) — not retryable.
                _reset_breaker()
                return {"valid": False, "reason": f"rejected_by_provider_{response.status_code}"}
            _reset_breaker()
            return response.json()
        except httpx.HTTPError as exc:
            last_exc = exc
        if attempt < settings.identity_provider_retries:
            await _sleep_backoff(attempt)
    _record_failure()
    raise ExternalServiceError(
        "Identity provider unreachable after retries",
        details={"attempts": settings.identity_provider_retries + 1,
                 "last_error": type(last_exc).__name__ if last_exc else None},
    )


async def _sleep_backoff(attempt: int) -> None:
    import asyncio

    await asyncio.sleep(min(0.5 * (2 ** attempt), 4.0))


async def verify_credential(credential: str, include_claims: bool = False) -> dict:
    """Verify one credential. Returns the provider verdict enriched with an
    evidence hash:

        {valid: bool, vct, expiresAt, reason?, claims?, evidence_hash}
    """
    if not credential or not isinstance(credential, str):
        raise ValidationAppError("credential must be a non-empty string")
    verdict = await _post("/m2m/verify", {"credential": credential,
                                          "includeClaims": include_claims})
    verdict.setdefault("valid", False)
    verdict["evidence_hash"] = _evidence_hash(verdict)
    return verdict


async def verify_credentials(credentials: list) -> dict:
    """Batch variant — returns {results: [...], each with evidence_hash}."""
    if not isinstance(credentials, list) or not credentials:
        raise ValidationAppError("credentials must be a non-empty list")
    verdict = await _post("/m2m/verify-batch", {"credentials": list(credentials)})
    results = verdict.get("results") or []
    for item in results:
        item.setdefault("valid", False)
        item["evidence_hash"] = _evidence_hash(item)
    return {"results": results}


def breaker_status() -> dict:
    return {"failures": _state["failures"], "threshold": _FAILURE_THRESHOLD,
            "open": _breaker_open()}
