# Overwatch AML — Developer Quickstart (TASK-026)

Goal: run the platform locally in under an hour.

## 1. Prerequisites

- Python 3.12+, Docker + Compose v2, Node 20+, Maven 3.9+ / JDK 17 (didvc only)

## 2. Environment

```bash
cd aml_platform
cp .env.example .env      # fill secrets: openssl rand -hex 32
export $(grep -v '^#' .env | xargs)   # or use docker compose --env-file
```

Required variables (compose fail-fast when missing): `POSTGRES_PASSWORD`,
`AML_API_PASSWORD`, `AML_ETL_PASSWORD`, `KEYCLOAK_DB_PASSWORD`,
`KEYCLOAK_ADMIN_PASSWORD`; backend needs `JWT_SECRET_KEY` when
`AUTH_MODE=local`.

## 3. Database

```bash
cd aml_platform
docker compose up -d age_db        # init scripts create app/core schemas + AGE graphs
docker compose logs -f age_db      # wait for "database system is ready"
```

Port: `127.0.0.1:5433` (user `postgres`, password from `POSTGRES_PASSWORD`).

## 4. Backend (local mode)

```bash
cd aml_platform/backend
uv venv .venv && uv pip install -r requirements.txt   # or pip
export AUTH_MODE=local JWT_SECRET_KEY="$(openssl rand -hex 32)"
export DATABASE_URL="postgresql://aml_api_role:$AML_API_PASSWORD@127.0.0.1:5433/age_prod_01"
uv run uvicorn app.main:app --port 8000
```

- Swagger: http://127.0.0.1:8000/docs · Health: /health
- **Seed a login user** (local mode reads `public.users`; the app also needs
  `app.app_users` + an active `tenant_memberships` row for tenant context):
  see `Implementation_Plan/20260903_didvc_phase1.md` or the P2 walkthrough
  seed SQL in the git history (test_session_cookie.py shows the shape).
- didvc identity features need the edge (below); onboarding endpoints return
  503 "identity provider not configured" until then.

## 5. didvc edge (authorized-wallet features)

```bash
cd Overwatch2
mvn -f didvc/pom.xml -DskipTests package        # once
aml_platform/backend/scripts/run_didvc_edge_pilot.sh   # boots pilot on :8090
# then export DIDVC_EDGE_* from /tmp/didvc_pilot.env into the backend env:
export IDENTITY_PROVIDER_URL="http://127.0.0.1:8090"
export IDENTITY_PROVIDER_API_KEY="$(grep DIDVC_EDGE_M2M_API_KEYS /tmp/didvc_pilot.env | cut -d= -f2)"
export IDENTITY_PROVIDER_TENANT=aml
# restart uvicorn
```

## 6. Frontend

```bash
cd aml_platform/frontend
npm ci && npm run dev        # http://127.0.0.1:3000 (use 3000-free port if busy)
```

Login page at `/login`; wallet console at `/admin/onboarding` (admin role).

## 7. Tests

```bash
cd aml_detection && python -m pytest .           # detection engine
cd aml_platform/backend && pytest tests/ -q --ignore=tests/e2e
cd didvc && mvn -f pom.xml -B -q -pl didvc-services -am test
cd aml_platform/frontend && npx tsc --noEmit
# type gate: mypy --config-file pyproject.mypy.toml aml_detection/
```

## 8. Troubleshooting (from the debug history)

| Symptom | Cause / fix |
|---|---|
| Backend 500 on startup | Missing env secret — the app fails fast; see `.env.example` |
| `LOAD 'age'` permission denied | Role must be superuser (dev) or AGE preloaded (prod) |
| Feed 500 "not JSON serializable" | Fixed in alerts.py `_jsonable` — update the DB schema first |
| Cypher syntax near `|` | AGE rejects label unions; single-label profile/fallback renderer |
| SKIP syntax error | openCypher order: `SKIP n LIMIT m` |
| Edge container not healthy | Rebuild after `mvn package` (jar changed) |
| Port 3000 busy | Another service owns it; run `next dev -p 3010` and set CORS/API origin accordingly |
