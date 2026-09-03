#!/usr/bin/env python3
"""
Load test for the credential edge (T-8.3): drives full issue-then-verify
round trips — internal offer, pre-authorized-code token, key-bound
credential request, OID4VP authorization request and DCQL presentation —
at a configurable concurrency, and reports per-step and end-to-end latency
percentiles. Python port of the original load-test.ts (same protocol and
CLI), using httpx + asyncio and Ed25519 via pyca/cryptography.

Target containment: the edge base URL is validated once at startup
(http/https scheme; the resolved addresses must not be link-local,
unspecified, reserved or multicast) and every request targets that single
declared origin — no arbitrary URLs are ever fetched.

Usage:
  python3 load_test.py [--edge http://localhost:8081] [--iterations 200]
                       [--concurrency 8] [--p95-target-ms 1000]
Environment:
  EDGE_API_KEY  required — the edge's internal API key (no default literal)
"""

import argparse
import asyncio
import base64
import hashlib
import ipaddress
import json
import math
import os
import secrets
import socket
import sys
import time
import urllib.parse

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

GRANT = "urn:ietf:params:oauth:grant-type:pre-authorized_code"


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


class HolderKey:
    def __init__(self):
        self.private = Ed25519PrivateKey.generate()
        self.public_bytes = self.private.public_key().public_bytes_raw()
        self.public_jwk = {"kty": "OKP", "crv": "Ed25519", "x": b64url(self.public_bytes)}

    def sign(self, signing_input: str) -> str:
        signature = self.private.sign(signing_input.encode())
        return f"{signing_input}.{b64url(signature)}"

    def jwt(self, header: dict, payload: dict) -> str:
        signing_input = f"{b64url(json.dumps(header, separators=(',', ':')).encode())}." \
                        f"{b64url(json.dumps(payload, separators=(',', ':')).encode())}"
        return self.sign(signing_input)


def validate_edge_origin(raw: str) -> str:
    """http(s) scheme; DNS-resolved addresses must not be link-local,
    unspecified, reserved or multicast. Loopback/private are allowed on
    purpose: the declared target of this tool is frequently a local edge."""
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise SystemExit(f"edge URL must be http(s) with a host, got {raw!r}")
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise SystemExit(f"edge host does not resolve: {parsed.hostname}") from exc
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if address.is_link_local or address.is_unspecified or address.is_reserved or address.is_multicast:
            raise SystemExit(f"edge host {parsed.hostname} resolves to blocked address {address}")
    return f"{parsed.scheme}://{parsed.netloc}"


class StepTimes(dict):
    KEYS = ("offer", "token", "credential", "authorize", "verify", "total")


async def one_round_trip(client: httpx.AsyncClient, origin: str, credential_issuer: str,
                         api_key: str, holder: HolderKey, worker_id: int, iteration: int) -> StepTimes:
    times = StepTimes({k: 0.0 for k in StepTimes.KEYS})
    headers_json = {"Content-Type": "application/json"}
    started = time.perf_counter()

    # 1. internal offer (pre-authorized code grant)
    t = time.perf_counter()
    kid_response = await client.get(f"{origin}/demo/issuer-kid")
    kid = kid_response.json()["kid"]
    offer_response = await client.post(
        f"{origin}/hkt/internal/offers",
        headers={**headers_json, "X-Api-Key": api_key},
        json={
            "schemaId": "hkt-kyc-v1",
            "vct": "hkt_kyc_v1",
            "subjectId": f"didvc:pairwise:load-{worker_id}-{iteration}",
            "kid": kid,
            "alwaysDisclosedClaims": {"kycLevel": "REMOTE_FULL"},
            "selectivelyDisclosedClaims": {"givenName": "LoadTest", "nationality": "HK"},
        },
    )
    if offer_response.status_code >= 300:
        raise RuntimeError(f"offer failed: {offer_response.status_code} {offer_response.text}")
    offer = offer_response.json()
    times["offer"] = time.perf_counter() - t

    # 2. token exchange
    t = time.perf_counter()
    token_response = await client.post(
        f"{origin}/hkt/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        content=f"grant_type={urllib.parse.quote(GRANT)}&pre-authorized_code="
                f"{urllib.parse.quote(offer['grants'][GRANT]['pre-authorized_code'])}",
    )
    if token_response.status_code >= 300:
        raise RuntimeError(f"token failed: {token_response.status_code} {token_response.text}")
    token = token_response.json()
    times["token"] = time.perf_counter() - t

    # 3. proof + credential request
    t = time.perf_counter()
    proof_payload = {
        "iss": "didvc:pairwise:load-wallet",
        # F-8: the proof audience must be the ADVERTISED credential issuer
        # (discovered from metadata, not assumed from the dialled origin).
        "aud": credential_issuer,
        "iat": int(time.time()),
        "nonce": token["c_nonce"],
    }
    proof_jwt = holder.jwt(
        {"typ": "openid4vci-proof+jwt", "alg": "EdDSA", "jwk": holder.public_jwk},
        proof_payload,
    )
    credential_response = await client.post(
        f"{origin}/hkt/credential",
        headers={**headers_json, "Authorization": f"Bearer {token['access_token']}"},
        json={
            "credential_configuration_id": "hkt_kyc_v1",
            "proof": {"proof_type": "jwt", "jwt": proof_jwt},
        },
    )
    if credential_response.status_code >= 300:
        raise RuntimeError(f"credential failed: {credential_response.status_code} {credential_response.text}")
    credential = credential_response.json()["credential"]
    times["credential"] = time.perf_counter() - t

    # 4. OID4VP authorization request (claims map)
    t = time.perf_counter()
    nonce = f"load-{worker_id}-{iteration}-{secrets.token_hex(8)}"
    authorize_response = await client.post(
        f"{origin}/bank-a/vp/authorize",
        headers=headers_json,
        json={"client_id": "load-verifier", "nonce": nonce,
              "claims": {"hkt_kyc_v1": ["givenName"]}},
    )
    if authorize_response.status_code >= 300:
        raise RuntimeError(f"authorize failed: {authorize_response.status_code} {authorize_response.text}")
    # The state for direct_post is the server-issued requestId carried in
    # the returned request_uri (.../vp/request/{requestId}) — NOT the client
    # nonce (the original TS tool had drifted here).
    request_uri = authorize_response.json()["request_uri"]
    state = request_uri.rsplit("/", 1)[-1]
    times["authorize"] = time.perf_counter() - t

    # 5. key-binding JWT + presentation (RFC 9901 §4.3.1 sd_hash over the
    #    full pre-KB presentation, trailing tilde included)
    t = time.perf_counter()
    kb_jwt = holder.jwt(
        {"alg": "EdDSA", "typ": "kb+jwt"},
        {
            "nonce": nonce,
            "aud": "load-verifier",
            "iat": int(time.time()),
            "sd_hash": b64url(hashlib.sha256(credential.encode()).digest()),
        },
    )
    direct_post = await client.post(
        f"{origin}/bank-a/vp/direct_post",
        headers=headers_json,
        json={"state": state, "nonce": nonce, "vp_token": credential + kb_jwt},
    )
    if direct_post.status_code >= 300:
        raise RuntimeError(f"direct_post failed: {direct_post.status_code} {direct_post.text}")
    verification = direct_post.json()
    if verification.get("valid") is not True:
        raise RuntimeError(f"verification not valid: {json.dumps(verification)}")
    times["verify"] = time.perf_counter() - t

    times["total"] = time.perf_counter() - started
    return times


def percentile(sorted_values: list, p: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, math.ceil((p / 100.0) * len(sorted_values)) - 1)
    return sorted_values[max(0, idx)]


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edge", default="http://localhost:8081")
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--p95-target-ms", type=int, default=1000)
    args = parser.parse_args()

    api_key = os.environ.get("EDGE_API_KEY")
    if not api_key:
        print("Missing required environment variable EDGE_API_KEY", file=sys.stderr)
        return 1

    origin = validate_edge_origin(args.edge)
    print(f"edge={origin} iterations={args.iterations} concurrency={args.concurrency} "
          f"p95Target={args.p95_target_ms}ms")

    holders = [HolderKey() for _ in range(args.concurrency)]
    samples: list = []
    failures: list = []
    cursor = 0
    lock = asyncio.Lock()

    started_all = time.perf_counter()
    async with httpx.AsyncClient(timeout=30) as client:
        metadata_response = await client.get(f"{origin}/hkt/.well-known/openid-credential-issuer")
        metadata_response.raise_for_status()
        credential_issuer = metadata_response.json()["credential_issuer"]

        async def worker(worker_id: int) -> None:
            nonlocal cursor
            while True:
                async with lock:
                    iteration = cursor
                    cursor += 1
                if iteration >= args.iterations:
                    return
                try:
                    sample = await one_round_trip(client, origin, credential_issuer,
                                                  api_key, holders[worker_id],
                                                  worker_id, iteration)
                    samples.append(sample)
                except Exception as exc:  # noqa: BLE001 — report per-iteration failures
                    failures.append(f"#{iteration}: {exc}")

        await asyncio.gather(*(worker(w) for w in range(args.concurrency)))
    wall_clock = time.perf_counter() - started_all

    if not samples:
        print("no successful round trips; failures:", failures[:5], file=sys.stderr)
        return 1

    def step_values(name: str) -> list:
        return sorted(s[name] * 1000.0 for s in samples)

    def fmt(sorted_ms: list) -> str:
        return (f"p50={percentile(sorted_ms, 50):.0f}ms "
                f"p95={percentile(sorted_ms, 95):.0f}ms "
                f"p99={percentile(sorted_ms, 99):.0f}ms")

    print("\n| step | latency |")
    print("|---|---|")
    for name in StepTimes.KEYS:
        print(f"| {name} | {fmt(step_values(name))} |")
    verify_p95 = percentile(step_values("verify"), 95)
    print(f"\nthroughput={len(samples) / (wall_clock / 1000):.1f} roundtrips/s "
          f"wall={wall_clock:.1f}s ok={len(samples)} failed={len(failures)}")
    verdict = "PASS" if verify_p95 <= args.p95_target_ms else "FAIL"
    print(f"verification p95={verify_p95:.0f}ms (target <= {args.p95_target_ms}ms): {verdict}")
    if failures:
        print("failures (first 10):")
        for failure in failures[:10]:
            print("  " + failure)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
