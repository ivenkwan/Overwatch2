# Overwatch AML Platform — Complete Codebase Analysis

## 1. Project Overview

**Overwatch** is an Anti-Money Laundering (AML) investigation platform for Hong Kong regulatory compliance (HKMA/JFIU). It detects and visualizes fund flows across **fiat (SWIFT)** and **Web3 (on-chain/crypto)** using a hybrid relational-graph architecture.

**Tech Stack:**
- **Database**: PostgreSQL 16 + Apache AGE (openCypher graph extension)
- **Backend**: Python 3.12 / FastAPI with asyncpg
- **Frontend**: Next.js 16 (App Router) + TypeScript + Tailwind CSS + Cytoscape.js
- **ETL**: Dagster orchestration + Polars data processing
- **Deployment**: Docker Compose (Kubernetes planned)

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js Frontend                      │
│         (Dark dashboard, 7 modules, Cytoscape.js)       │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API (port 8000)
┌──────────────────────▼──────────────────────────────────┐
│                  FastAPI Backend                         │
│     (asyncpg pool, JWT auth, RBAC, PII masking)         │
└──────────────────────┬──────────────────────────────────┘
                       │ SQL / openCypher
┌──────────────────────▼──────────────────────────────────┐
│          PostgreSQL 16 + Apache AGE                      │
│     (Relational tables + Property graph)                 │
└─────────────────────────────────────────────────────────┘
         ▲                              ▲
         │                              │
┌────────┴─────────┐          ┌─────────┴──────────┐
│  Dagster ETL     │          │  Standalone API    │
│  (Polars→PG→AGE) │          │  api/server.py     │
│  docker-compose  │          │  (MVP/legacy)      │
│  port 5433       │          └────────────────────┘
└──────────────────┘
```

---

## 3. Component Breakdown

### 3.1 ETL Pipeline (`etl/` + `aml_platform/etl/`)

**Dagster DAG** (`etl/assets/`):
| Asset | Purpose |
|-------|---------|
| `raw_ledger_data` | Reads CSV with Polars, renames columns |
| `cleaned_ledger_data` | Deduplicates, SHA-256 hashes transactions, cleans counterparty names |
| `load_relational_tables` | Upserts into `core.customers`, `core.counterparties`, `core.transactions` |
| `update_age_graph` | Projects relational data into Apache AGE graph via PL/pgSQL loop |

**Additional ETL scripts** (`aml_platform/etl/`):
| File | Purpose |
|------|---------|
| `rule_engine.py` | Cypher-based rule engine for laundering typologies |
| `typologies.py` | Circular flow, smurfing, rapid movement detection |
| `graph_loader.py` | Loads screened data into AGE graph |
| `run_batch.py` | Batch orchestration runner |
| `data_gen_bulk.py` | Synthetic data generator |
| `bulk_synthetic_data.sql` | SQL-based bulk synthetic data insertion |

**Schema** (`etl/sql/init_schema.sql`):
- Creates `core.customers`, `core.counterparties`, `core.transactions` tables
- Initializes Apache AGE graph `tap_and_go_network` with Customer, Counterparty, Merchant vertex labels and TRANSFERRED, PAID edge labels

### 3.2 Backend API (`aml_platform/backend/app/`)

**11 Python files organized as:**

| Layer | Files | Purpose |
|-------|-------|---------|
| Entry | `main.py` | FastAPI app, CORS, lifespan, router registration |
| DB | `db/session.py` | asyncpg connection pool (min 2, max 20), AGE extension loading |
| Auth | `core/auth.py` | JWT (HS256), bcrypt, RBAC scopes, audit logging |
| Schemas | `schemas/user.py` | Pydantic models: UserCreate, UserOut, Token |
| Services | `services/pii_service.py` | Role-based PII masking (wallet prefix/suffix, full redaction) |
| Services | `services/graph_service.py` | Apache AGE Cypher queries → Cytoscape.js format |
| Routes | `api/v1/auth.py` | POST /login → JWT token |
| Routes | `api/v1/alerts.py` | GET /feed, GET /, GET /{id}, POST /{id}/{action} |
| Routes | `api/v1/graph.py` | GET /network, GET /explore/{entity_id} |
| Routes | `api/v1/admin.py` | POST /users (ADMIN only) |
| Routes | `api/v1/reports.py` | GET /monthly (DEPARTMENT_HEAD only) |

**API Endpoints Summary:**

| Endpoint | Auth Required | Role Required | Status |
|----------|--------------|---------------|--------|
| `POST /api/v1/auth/login` | No | — | Working |
| `GET /api/v1/alerts/feed` | Yes | Any (alert.read) | Working |
| `GET /api/v1/alerts/` | Yes | Any | Working (dummy — uses core.transactions) |
| `GET /api/v1/alerts/{id}` | Yes | Any | Working |
| `POST /api/v1/alerts/{id}/assign` | Yes | Any | **Stub** |
| `POST /api/v1/alerts/{id}/propose-close` | Yes | Any | **Stub** |
| `POST /api/v1/alerts/{id}/approve` | Yes | SENIOR_INVESTIGATOR | **Stub** |
| `POST /api/v1/alerts/{id}/reject` | Yes | SENIOR_INVESTIGATOR | **Stub** (validates notes length) |
| `GET /api/v1/graph/network` | **No** | — | Working (unauthenticated!) |
| `GET /api/v1/graph/explore/{id}` | Yes | SENIOR_INVESTIGATOR | Working (but ignores params) |
| `POST /api/v1/admin/users` | Yes | ADMIN | Broken (sync DB calls) |
| `GET /api/v1/reports/monthly` | Yes | DEPARTMENT_HEAD | Broken (sync DB calls) |
| `GET /health` | No | — | Working |

**RBAC Role Hierarchy:**

| Role | Scopes | Access |
|------|--------|--------|
| JUNIOR_ANALYST | `alert.read` | Monitoring feed, alert views |
| SENIOR_INVESTIGATOR | `alert.read`, `graph.explore` | + graph exploration, approve/reject |
| DEPARTMENT_HEAD | `alert.read`, `graph.explore` | + monthly reports |
| ADMIN | `alert.read`, `graph.explore` | + user management |

### 3.3 Frontend (`aml_platform/frontend/`)

**Single-page application** at route `/` with 7 module views:

| Module | Component | API Integration | Status |
|--------|-----------|-----------------|--------|
| NETWORK | GraphExplorer + Dashboard shell | `GET /graph/network` | Live |
| MONITORING | MonitoringFeed | `GET /alerts/feed` | Live |
| ALERTS | AlertWorkbench | None | **Static dummy data** |
| CASES | CaseManagement | None | **Static dummy data** |
| STR | STRPreparation | None | **Static placeholder** |
| SCREENING | ScreeningModule | None | **Static placeholder** |
| GOVERNANCE | GovernanceMIS | None | **Static dummy data** |

**File inventory (14 source files, ~1,089 LOC):**
- `src/app/page.tsx` (260 lines) — Dashboard shell with sidebar, module switching, graph layer
- `src/app/layout.tsx` — Layout with Geist fonts
- `src/components/GraphExplorer.tsx` — Cytoscape.js wrapper (force-directed cose layout, Discovery/Fast modes)
- `src/components/KPICard.tsx` — Reusable KPI display
- `src/components/modules/` — 7 module components (MonitoringFeed, AlertWorkbench, CaseManagement, STRPreparation, ScreeningModule, GovernanceMIS)
- `src/services/api.ts` — 2 API methods only (fetchFeed, fetchGraphNetwork)
- `src/types/models.ts` — TypeScript interfaces (Channel, Customer, Payment, Alert, Case)

### 3.4 Database Schema

**Relational tables** (from `init-scripts/`):
| Table | Purpose |
|-------|---------|
| `staging_fiat_raw` | Fiat SWIFT transfer staging |
| `staging_crypto_raw` | Crypto on-chain transaction staging |
| `ofac_blocklist` | Sanctions screening list |
| `fatf_rules` | Travel Rule restrictions by jurisdiction |
| `alerts` | Alert queue (OFAC matches, typology hits) |
| `dead_letter_queue` | Failed ingestion records |
| `super_nodes` | Excluded high-connectivity nodes (exchanges, omnibus) |
| `public.users` | Auth users with bcrypt passwords, role enum |
| `core.customers` | Normalized customer records |
| `core.counterparties` | Normalized counterparty records |
| `core.transactions` | Normalized transaction records |

**Apache AGE graph** (`aml_network`):
- Vertices: Entity, SuperNode
- Edges: Transfer

**Stored procedures:**
- `sp_screen_ofac()` — Screens staging data against OFAC blocklist, generates CRITICAL alerts, transitions status to SCREENED

### 3.5 Legacy/MVP API (`aml_platform/api/server.py`)

A standalone 99-line FastAPI server with hardcoded credentials (`password="secure_password_123"`), mock RBAC via header check, and incomplete graph traversal. This appears to be an earlier prototype superseded by the modular backend in `backend/app/`.

---

## 4. Critical Issues Found

### CRITICAL — Security Vulnerabilities

1. **Hardcoded JWT Secret** (`core/auth.py:13`):
   ```python
   SECRET_KEY = "aml_super_secret_key_change_me"
   ```
   Anyone reading the source can forge JWT tokens for any role.

2. **Unauthenticated Graph Endpoint** (`api/v1/graph.py:9`):
   `GET /api/v1/graph/network` has **no auth dependency** — exposes entire network topology including all wallet addresses and entity relationships.

3. **Wildcard CORS with Credentials** (`main.py:24`):
   ```python
   allow_origins=["*"], allow_credentials=True
   ```
   This is an invalid and dangerous combination.

4. **Hardcoded DB Credentials** (`api/server.py:24`):
   ```python
   password="secure_password_123"
   ```

### HIGH — Runtime Bugs

5. **Sync/Async DB API Mismatch** — `auth.py:16-17`, `admin.py:19-30`, `reports.py:15-31` use `db.cursor()`, `cursor.execute()`, `db.commit()` on **asyncpg** connections. These will **crash at runtime**. Only `alerts.py` correctly uses `await db.fetch()`.

6. **Stub Alert Lifecycle** (`api/v1/alerts.py:59-77`): All 4 workflow endpoints (assign, propose-close, approve, reject) return hardcoded responses with zero DB operations.

7. **Graph Neighborhood Ignores Parameters** (`graph_service.py:69-71`):
   ```python
   async def get_neighborhood(db, entity_id, depth):
       return await get_full_network(db, 100)
   ```
   Every exploration returns the same full network regardless of entity or depth.

### MEDIUM — Code Quality

8. **SQL Injection via f-string** (`graph_service.py:13`): `LIMIT {limit}` interpolated directly into Cypher query.

9. **PII Masking Bypass** (`graph.py:20`): Network endpoint hardcodes `"ADMIN"` role for masking, but the endpoint is unauthenticated anyway.

10. **Unused Pydantic v1 syntax** (`schemas/user.py:19`): `orm_mode = True` should be `from_attributes = True` for Pydantic v2.

11. **Audit logs not persisted** — Only go to Python stdout logger, not to tamper-evident storage.

### FRONTEND Issues

12. **Single-page monolith** — No URL routing, no bookmarking, no deep linking.

13. **6 unused dependencies** — `axios`, `framer-motion`, `clsx`, `tailwind-merge`, `shadcn-ui`, `@tanstack/react-query` all in package.json but never imported.

14. **5 of 7 modules are static** — No API integration for alerts, cases, STR, screening, or governance.

15. **No frontend authentication** — No session management, no auth headers on API calls, no protected routes.

16. **Generic metadata** — `layout.tsx` still has `"Generated by create next app"`.

---

## 5. Summary Metrics

| Metric | Value |
|--------|-------|
| Total Python files | 25 |
| Backend API files | 11 |
| Frontend source files | 14 (~1,089 LOC) |
| SQL schema files | 6 |
| API endpoints | ~13 (5 are stubs, 2 broken) |
| Live frontend modules | 2 of 7 |
| Database | PostgreSQL 16 + Apache AGE |
| Auth | JWT (HS256) + bcrypt + 4-role RBAC |
| ETL | Dagster DAG (4 assets) |
| Docker Compose files | 2 (ETL + main platform) |

**State**: MVP/prototype with solid architectural foundation but critical security vulnerabilities, runtime bugs, and significant non-functional portions.