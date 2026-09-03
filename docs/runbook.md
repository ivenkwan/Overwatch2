# Overwatch AML — Operations Runbook (TASK-027)

Incident response, recovery and escalation for the platform services.

## Service map

| Service | Container | Port | Healthcheck |
|---|---|---|---|
| PostgreSQL + Apache AGE | aml-age-db | 5433 | `pg_isready` |
| FastAPI backend | aml-fastapi-backend | 8000 | `GET /health` (DB pool status) |
| Next.js frontend | aml-nextjs-frontend | 3000 | HTTP probe |
| Keycloak | aml-keycloak | 8080 | HTTP probe |
| Flowable | aml-flowable | 8081 | HTTP probe |
| Dagster | aml-dagster-etl | 3001 | HTTP probe |
| didvc edge | didvc-edge (profile `awi`) | 8090 | `/demo/issuer-kid` (pilot) |

## Alerting & monitoring

- `GET /metrics` on the backend exposes request counters/durations in
  Prometheus text format (TASK-022). Grafana dashboards and alert rules are
  configured out-of-band; the metric names to alert on:
  `aml_http_requests_total`, `aml_http_request_duration_seconds_*`.
- Audit integrity: `GET /api/v1/audit/verify` (admin) recomputes the
  hash chain — schedule it nightly; alert when `valid=false`.

## Incident response

1. **Classify**: Sev1 (data/security/availability), Sev2 (degraded), Sev3 (cosmetic).
2. **Record**: every action lands in the audit trail (operator = system when
   no user session applies).
3. **Contain → diagnose → recover → verify → document**.

### P0 playbooks

| Scenario | Detection | Immediate action | Recovery |
|---|---|---|---|
| Backend down | health 503 / 500s | `docker compose ps`; `docker logs aml-fastapi-backend` | Fix env (missing secret = fail-fast at boot); restart |
| DB down/crash | AGE "interrupted" in logs; health degraded | Do NOT delete the volume | Postgres auto-recovers on start; if not: restore from `scripts/restore_db.sh` (RTO<4h target, hourly backups RPO<1h) |
| Keycloak unavailable | login 502 | Confirm `keycloak` container + DB | Realm is reproducible from `keycloak/aml-realm.json` (export first in prod) |
| Identity edge down | onboarding 503/circuit breaker open | Check `didvc-edge` container; breaker auto-resets after 30 s | Restart; onboarding fails closed (wallets stay unauthorized) — safe |
| Audit chain broken | `/audit/verify` invalid | Freeze changes to audited flows | Investigate DB write access; restore from backup; re-verify |
| Failed workflow stuck | `GET /api/v1/cases/workflow/stale` | Identify case; check Flowable task | Complete or cancel task via Flowable admin; update `workflow_status` |

### Security incidents

- Suspected credential exposure → rotate `JWT_SECRET_KEY` / Keycloak
  client secrets / edge API keys (rotation procedures in
  `didvc/docs/operator-runbook.md`), revoke sessions, audit-export the
  window.
- Tampering evidence → preserve logs + `audit/export`; run `/audit/verify`;
  involve compliance before any restore (chain-of-evidence).

## Escalation matrix

| Level | Owner | Time |
|---|---|---|
| L1 | Platform engineering (on-call) | 24×7 |
| L2 | Backend/DB owner | business hours, Sev1 immediate |
| Compliance/MLRO | STR/audit issues | per policy (TASK-058 sign-off pending) |
| Legal | data breach | per incident policy |

## Backups

`aml_platform/scripts/backup_db.sh` (hourly cron; SHA-256 manifest;
retention 7 d). Restore: `restore_db.sh` (checksum-verified, typed
confirmation). Monthly restore drill is a standing ops task.

## Change & verification

After any deploy: run the CI suites (backend pytest, aml_detection,
didvc mvn, frontend tsc), hit `/health` + `/metrics`, and run one
authorized-wallet smoke (register→approve) against the edge.
