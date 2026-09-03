"""
T1_CREDENTIAL_STATUS — nightly credential re-verification batch (AWI TASK-048).

Mirrors the sanctions re-screen SLA pattern: every ACTIVE party_credential is
re-verified nightly against didvc-edge /m2m/verify-batch; status flips to
EXPIRED / REVOKED / REFRESH_DUE drive wallet deauthorization and a review
event. Failed checks land in app.credential_check_dlq for triage.

Self-contained by design (httpx ships in the etl image). The pure planning
logic (plan_status_updates) is unit-tested in backend/tests without Dagster
or a database. Every statement below is a single-line SQL literal executed
with %s bind parameters — nothing is ever interpolated into SQL text; the
provider URL passes an egress boundary check before any request is made.
"""

import ipaddress
import os
import socket
import urllib.parse

import httpx
import psycopg2
from dagster import DefaultScheduleStatus, Failure, RunRequest, job, op, schedule

from credential_planning import plan_status_updates  # pure, dagster-free logic

POSTGRES_URI = os.environ.get("POSTGRES_URI", "")
IDENTITY_PROVIDER_URL = os.environ.get("IDENTITY_PROVIDER_URL", "")
IDENTITY_PROVIDER_API_KEY = os.environ.get("IDENTITY_PROVIDER_API_KEY", "")
IDENTITY_PROVIDER_TENANT = os.environ.get("IDENTITY_PROVIDER_TENANT", "aml")
RULE_VERSION = "2026.09-t1-credential-status-1"

# Allowed egress: http/https only, no userinfo, never the cloud-metadata /
# link-local range. Plain private ranges are permitted on purpose — the
# provider is an in-network container service.
_BLOCKED_NETWORKS = [ipaddress.ip_network("169.254.0.0/16"),
                     ipaddress.ip_network("fe80::/10")]

# Provider boundary (egress validation) ----------------------------------------


def validated_provider_url(base_url: str, tenant: str) -> str:
    """Validate the configured provider URL before any request leaves the host.

    Enforces: http/https scheme, no userinfo, no fragment, host resolves, and
    the resolved address is not in the link-local/metadata range.
    """
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in ("http", "https"):
        raise Failure(f"IDENTITY_PROVIDER_URL must be http(s), got {parsed.scheme!r}")
    if not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise Failure("IDENTITY_PROVIDER_URL must be a plain http(s) URL without credentials")
    if not tenant or not all(c.isalnum() or c == "-" for c in tenant):
        raise Failure("IDENTITY_PROVIDER_TENANT must be alphanumeric/-")

    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise Failure(f"identity provider host does not resolve: {parsed.hostname}") from exc

    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if any(address in net for net in _BLOCKED_NETWORKS):
            raise Failure(
                f"identity provider host resolves into a blocked range ({address}); "
                "refusing egress to link-local/metadata addresses"
            )
    path = parsed.path.rstrip("/")
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, f"{path}/{tenant}/m2m/verify-batch", "", "", ""))


def _verify_batch(credentials):
    """Call didvc-edge /m2m/verify-batch (httpx, boundary-checked URL)."""
    if not IDENTITY_PROVIDER_URL or not IDENTITY_PROVIDER_API_KEY:
        raise Failure("IDENTITY_PROVIDER_URL / IDENTITY_PROVIDER_API_KEY are required")
    url = validated_provider_url(IDENTITY_PROVIDER_URL, IDENTITY_PROVIDER_TENANT)
    headers = {"X-Api-Key": IDENTITY_PROVIDER_API_KEY}
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(url, json={"credentials": credentials}, headers=headers)
    except httpx.HTTPError as exc:
        raise Failure(f"identity provider unreachable: {exc}") from exc
    if 500 <= response.status_code:
        raise Failure(f"identity provider {response.status_code}")
    if response.status_code >= 400:
        return [{"error": f"provider rejected batch: {response.status_code}"}]
    payload = response.json()
    return payload.get("results") or [None] * len(credentials)


# Dagster ops ------------------------------------------------------------------


def _connect():
    if not POSTGRES_URI:
        raise Failure("POSTGRES_URI environment variable is required")
    return psycopg2.connect(POSTGRES_URI)


@op
def extract_active_credentials(context):
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pc.credential_id, pc.expires_at, COALESCE(ARRAY_AGG(wa.instrument_id) FILTER (WHERE wa.instrument_id IS NOT NULL), ARRAY[]::varchar[]) AS wallet_instruments FROM app.party_credential pc LEFT JOIN app.wallet_authorization wa ON wa.binding_credential = pc.credential_id AND wa.authorized = TRUE WHERE pc.status = 'ACTIVE' GROUP BY pc.credential_id, pc.expires_at")
            rows = cur.fetchall()
    finally:
        conn.close()
    context.log.info(f"active credentials to re-verify: {len(rows)}")
    return [
        {"credential_id": r[0],
         "expires_at": r[1].isoformat() if r[1] else None,
         "wallet_instruments": list(r[2])}
        for r in rows
    ]


@op
def verify_credentials(context, records):
    if not records:
        return []
    refs = [r["credential_id"] for r in records]
    verdicts = _verify_batch(refs)
    context.log.info(f"verdicts received: {len(verdicts)}")
    return verdicts


@op
def apply_status_updates(context, records, verdicts):
    plan = plan_status_updates(records, verdicts)
    conn = _connect()
    applied = {"credentials": 0, "deauthorizations": 0, "dlq": 0}
    try:
        with conn:
            with conn.cursor() as cur:
                for status_value, credential_id in plan["credential_updates"]:
                    cur.execute("UPDATE app.party_credential SET status = %s, last_checked_at = now() WHERE credential_id = %s", (status_value, credential_id))
                    applied["credentials"] += cur.rowcount
                for instrument_id in plan["deauthorizations"]:
                    cur.execute("UPDATE app.wallet_authorization SET authorized = FALSE WHERE instrument_id = %s AND authorized = TRUE", (instrument_id,))
                    applied["deauthorizations"] += cur.rowcount
                for credential_id, reason in plan["dlq"]:
                    cur.execute("INSERT INTO app.credential_check_dlq (credential_id, reason) VALUES (%s, %s)", (credential_id, reason))
                    applied["dlq"] += 1
                for status_value, credential_id in plan["credential_updates"]:
                    cur.execute("INSERT INTO app.audit_access_events (resource_type, resource_id, action, decision, reason) VALUES ('CREDENTIAL', %s, 'CREDENTIAL_STATUS_CHANGED', 'allow', %s)", (credential_id, f"nightly batch -> {status_value} ({RULE_VERSION})"))
    finally:
        conn.close()
    context.log.info(f"applied: {applied}")
    return applied


@job
def t1_credential_status_job():
    records = extract_active_credentials()
    verdicts = verify_credentials(records)
    apply_status_updates(records, verdicts)


@schedule(
    job=t1_credential_status_job,
    cron_schedule="0 3 * * *",  # 03:00 daily — inside the T+1 window, after detection (00:30)
    default_status=DefaultScheduleStatus.RUNNING,
)
def t1_credential_status_schedule(context):
    return RunRequest(
        run_key="t1_credential_status_"
        + context.scheduled_execution_time.strftime("%Y%m%d")
    )
