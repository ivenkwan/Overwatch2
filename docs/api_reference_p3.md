# API Reference — Overwatch AML Platform (TASK-020)

Live interactive docs: FastAPI auto-Swagger at `/docs` (OpenAPI 3.1).
Static artifact: `docs/openapi.json` (43 paths, regenerated with
`python aml_platform/backend/generate_openapi.py` from the repo root).

## Error envelope

Every error response uses one shape (TASK-009):

```json
{ "error": { "code": "<machine_code>", "message": "<human summary>", "details": {} } }
```

## Error-code registry

| code | HTTP | Meaning | Raised by |
|---|---|---|---|
| `http_401` | 401 | Missing/invalid credentials (Bearer or session cookie) | `get_current_user` |
| `http_403` | 403 | Insufficient role/scope | `require_role` / scope checker |
| `http_404` | 404 | Resource not found | routers |
| `request_validation_error` | 422 | Pydantic/query validation failed (`details.errors`) | global handler |
| `validation_error` | 400 | Business validation (e.g. short STR body) | `ValidationAppError` |
| `not_found` | 404 | Business lookup miss | `NotFoundError` |
| `forbidden` | 403 | Maker-checker or tenant-context denial | `AuthorizationAppError` |
| `conflict` | 409 | Illegal state transition (e.g. filing a filed STR) | `ConflictError` |
| `external_service_error` | 502 | Upstream (Keycloak, Flowable, identity provider) | `ExternalServiceError` |
| `service_unavailable` | 503 | Unconfigured dependency / circuit breaker open | `ServiceUnavailableError` |
| `database_error` | 500 | Data-store failure (details carry the operation only) | `database_error()` |
| `internal_error` | 500 | Unhandled exception (server-logged, never leaked) | global handler |

## Endpoint groups

| Prefix | Purpose | Notable routes |
|---|---|---|
| `/api/v1/auth` | Session | `POST /login` (sets `aml_session` httpOnly cookie) · `POST /logout` |
| `/api/v1/alerts` | Monitoring feed + alert triage | `GET /feed` (filters `min_hkd`, `txn_type`) · assign/propose/approve/reject |
| `/api/v1/cases` | Case lifecycle | notes, timeline, `POST /bulk`, `GET /workflow/stale` (case_enhance router) |
| `/api/v1/graph` | AGE graph | `GET /network?limit&offset` (TTL-cached) · `GET /explore/{entity}` |
| `/api/v1/onboarding` | Authorized wallets | challenge · verify · wallets register/approve/revoke · `GET /identity/{party}` |
| `/api/v1/screening` | Sanctions/watchlist | `POST /screen` (name fuzzy + wallet exact) |
| `/api/v1/audit` | Tamper-evident trail | `GET /export` (NDJSON, admin) · `GET /verify` |
| `/api/v1/str` | STR workflow | drafts, versions, `export.pdf` (X-Content-Sha256), review/submit |
| `/api/v1/reports` | MIS | `GET /kpis`, `GET /kpis/history?days=`, `GET /kpis/export.csv` |
| `/api/v1/admin` | Users/roles (Keycloak) | users · roles · role assignment |
| `/health` | Liveness | DB pool status |

## Authentication

`AUTH_MODE=keycloak` (default): Keycloak RS256 access tokens, validated
against the realm JWKS (issuer/expiry/audience enforced). The browser
client authenticates with the `aml_session` httpOnly cookie set at login;
API clients may use `Authorization: Bearer <token>` from `POST /login`.

## TypeScript types

Frontend models live in `aml_platform/frontend/src/types/models.ts`;
client calls are typed in `src/services/api.ts`. Regenerating TS types from
the OpenAPI artifact (openapi-typescript) is a tooling follow-up — the
hand-maintained types are kept in sync with the artifact by the tsc gate.
