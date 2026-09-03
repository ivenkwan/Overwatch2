# Overwatch AML Platform — Backend

FastAPI backend for the Overwatch AML platform (fiat + stablecoin transaction monitoring, alert/case/STR workflow) over PostgreSQL + Apache AGE.

## Security configuration (P0 hardening — TASK-001/002/004)

The application **refuses to start** when required secrets are missing or weak. All credentials come exclusively from environment variables — there are no fallback literals in the codebase.

### Authentication modes (`AUTH_MODE`)

| Mode | Use | Mechanism |
|---|---|---|
| `keycloak` (default) | Production | Keycloak-issued RS256 access tokens validated against the realm JWKS — signature, issuer (`iss`), expiry (`exp`/`nbf`) and audience (`aud`/`azp`) are all enforced (fail closed). Realm roles map to platform roles: `aml_admin → ADMIN`, `aml_department_head → DEPARTMENT_HEAD`, `aml_senior_investigator → SENIOR_INVESTIGATOR`, `aml_analyst → JUNIOR_ANALYST`. |
| `local` | Development / tests | HS256 tokens signed with `JWT_SECRET_KEY` (required, ≥ 32 chars, known-weak values rejected) against the `public.users` table. |

There is **no unauthenticated fallback** — requests without a valid Bearer token are rejected with 401 (the former anonymous-admin bypass was removed as part of TASK-002).

`POST /api/v1/auth/login`:
- `keycloak` mode: proxies the resource-owner password grant to Keycloak and returns the Keycloak-issued token.
- `local` mode: verifies credentials locally and issues an HS256 token.

### Environment variables

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | always | PostgreSQL DSN, e.g. `postgresql://aml_api_role:<password>@age_db:5432/age_prod_01`. No default. |
| `AUTH_MODE` | no | `keycloak` (default) or `local`. |
| `JWT_SECRET_KEY` | when `AUTH_MODE=local` | ≥ 32 chars; weak/revoked values rejected at startup. Generate: `openssl rand -hex 32`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | Default 60 (local mode only). |
| `KEYCLOAK_URL` | when `AUTH_MODE=keycloak` | e.g. `http://keycloak:8080`. |
| `KEYCLOAK_REALM` | no | Default `aml`. |
| `KEYCLOAK_AUDIENCE` | no | Expected `aud`/`azp` client; default `aml-portal`. |
| `KEYCLOAK_LEEWAY_SECONDS` | no | Clock-skew leeway; default 30. |
| `KEYCLOAK_ADMIN_USER` / `KEYCLOAK_ADMIN_PASSWORD` | for provisioning endpoints only | Admin client for `/api/v1/admin/*`; no defaults. |

See `../.env.example` for a complete template.

### Graph query hardening (TASK-003)

Apache AGE requires the Cypher body as a single dollar-quoted SQL string, so bind parameters cannot appear inside it. `app/services/graph_service.py` therefore prevents injection by construction:

1. `limit` / `depth` are coerced to `int` and clamped (`1..500`, `1..6`) — they can only render as bounded integer literals.
2. Entity ids must match `^[A-Za-z0-9._:@-]{1,128}$` (`validate_entity_id`) — quotes, dollar signs, semicolons, whitespace and unicode are rejected with HTTP 400 before any query is built.
3. Defence-in-depth: ids are additionally escaped (`escape_cypher_string`) before embedding.

All relational queries throughout the API use asyncpg `$n` bind parameters.

### Audit trail (TASK-004)

Every user action (logins, alert triage actions, graph exploration, PII unmasking, user provisioning, role assignment, STR updates) is persisted to `app.audit_access_events` — an **append-only** table (UPDATE/DELETE blocked by trigger) with a **SHA-256 hash chain** computed by the database triggers in `init_scripts/02_audit_tamper_evidence.sql`. Events are mirrored to the `aml_audit` logger so a trail survives DB outages; audit failures never break the audited request.

Admin-only endpoints:

- `GET /api/v1/audit/export?since=&until=&limit=` — NDJSON export for SIEM ingestion.
- `GET /api/v1/audit/verify` — recomputes the hash chain in SQL and reports integrity (`{valid, checked, broken_records, broken_at}`).

## Deployment

```bash
cd aml_platform
cp .env.example .env          # fill in real values (openssl rand -hex 32)
docker compose up -d --build
```

First boot: `00-roles-from-env.sh` creates the DB roles from the environment; Keycloak imports `keycloak/aml-realm.json` (realm `aml`, client `aml-portal`, realm roles). Create the first realm user in the Keycloak console (master admin comes from `KEYCLOAK_ADMIN_*`) and assign the appropriate `aml_*` realm role.

**Frontend session (2026-09-03):** the browser client uses an **httpOnly-cookie session**. `POST /api/v1/auth/login` sets the `aml_session` cookie (HttpOnly, SameSite=Lax); `get_current_user` accepts it as the bearer fallback, so no token ever lives in `localStorage` and no JavaScript reads it. The frontend (`frontend/src/services/api.ts`) sends `credentials: "include"` on every request; a login page (`/login`) and the wallet-onboarding console (`/admin/onboarding`) are the reference flows. The classic Bearer flow still works for API clients:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d 'username=<user>&password=<pass>' | jq -r .access_token)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/alerts/feed
```

> Existing volumes initialised with the old literal credentials must be recreated (`docker compose down -v`) before the environment-sourced credentials work.

### Running tests

```bash
cd backend
uv venv .venv && uv pip install -r requirements.txt pytest-asyncio   # or pip
pytest tests/ -v
```

Tests cover: fail-fast security config, token validation (local + Keycloak RS256 with issuer/expiry/audience enforcement), graph-input allowlist (injection payloads rejected), audit persistence semantics, the PII role/field matrix, STR compliance (mandatory fields, status transitions, PDF export), and the error envelope.

## Backup & disaster recovery (TASK-028)

Targets: **RTO < 4 hours, RPO < 1 hour.**

- **Hourly backups (RPO)**: cron `0 * * * *` runs `../scripts/backup_db.sh` — `pg_dump` custom format (compressed) + SHA-256 manifest + `pg_restore --list` verification + 7-day retention. Credentials via `PGPASSWORD` from the environment/secret store only.
- **Restore (RTO)**: `../scripts/restore_db.sh <dump> [target_db]` — verifies the manifest checksum, requires an explicit typed confirmation, then `pg_restore --clean --if-exists`. Practice restores into a scratch database monthly and record the measured RTO.
- **Non-database state**: Next.js frontend and Dagster definitions are stateless (rebuild from source); Keycloak realm is reproducible from `keycloak/aml-realm.json` + exported realm backups (`kc.sh export`); Flowable holds only workflow state that the platform can re-derive from PostgreSQL (dual-state design).

## Environment variables (platform P1 additions)

| Variable | Default | Purpose |
|---|---|---|
| `FLOWABLE_REST_URL` | `http://aml-flowable:8080/flowable-rest/service` | Workflow engine base URL |
| `FLOWABLE_USER` / `FLOWABLE_PASSWORD` | — (required when workflows are used) | Workflow engine credentials |
| `FLOWABLE_TIMEOUT` | `10` | Per-call timeout (seconds) to Flowable |
| `DB_POOL_MIN` / `DB_POOL_MAX` | `2` / `20` | Connection pool bounds |
| `DB_QUERY_TIMEOUT_MS` | `30000` | Server-side `statement_timeout` |
| `DB_ACQUIRE_TIMEOUT_S` | `10` | Max wait for a free connection |
| `JSON_LOGS` | `1` | JSON structured logging on stdout |

Error responses use one envelope everywhere: `{"error": {"code", "message", "details"}}` (TASK-009); `GET /health` reports database/pool status (TASK-008).
