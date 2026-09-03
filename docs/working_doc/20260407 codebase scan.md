# Overwatch AML Platform — Complete Codebase Analysis

**Generated:** 2026-04-07  
**Scope:** Full repository analysis of all Python, TypeScript, SQL, and configuration files

---

## 1. Project Overview

**Overwatch** is an Anti-Money Laundering (AML) investigation platform designed for Hong Kong regulatory compliance (HKMA/JFIU). It detects and visualizes networked fund flows across **fiat (SWIFT)** and **Web3 (on-chain/crypto)** environments using a hybrid relational-graph architecture.

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Database | PostgreSQL 16 + Apache AGE (openCypher graph extension) |
| Backend | Python 3.12 / FastAPI with asyncpg |
| Frontend | Next.js 16 (App Router) + TypeScript + Tailwind CSS + Cytoscape.js |
| ETL | Dagster orchestration + Polars data processing |
| Deployment | Docker Compose (Kubernetes planned) |

### Business Purpose

- **Data Ingestion & Normalization**: T+1 batch processing mapped to unified property graph
- **Regulatory Gate**: Pre-graph screening against OFAC, FATF, and internal blocklists
- **Automated Analytics**: Cypher rule engine for Circular Flow, Smurfing, Rapid Movement typologies
- **Investigation Workspace**: Alert dashboard with visual graph explorer for node neighborhood expansion
- **HKMA Compliance**: JFIU-ready STR narratives, maker-checker workflow, full audit trail

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

## 3. Directory Structure

```
Overwatch/
├── aml_platform/
│   ├── backend/app/           # FastAPI modular backend
│   │   ├── main.py            # App entry, CORS, lifespan, routers
│   │   ├── api/v1/            # Route handlers
│   │   │   ├── auth.py        # Login endpoint
│   │   │   ├── alerts.py      # Alert feed + lifecycle (5 stubs)
│   │   │   ├── graph.py       # Apache AGE graph queries
│   │   │   ├── admin.py       # User creation (ADMIN only)
│   │   │   └── reports.py     # KPI aggregation (DEPT_HEAD only)
│   │   ├── core/auth.py       # JWT, bcrypt, RBAC, audit logging
│   │   ├── db/session.py      # asyncpg connection pool
│   │   ├── schemas/user.py    # Pydantic models
│   │   └── services/
│   │       ├── pii_service.py     # Role-based PII masking
│   │       └── graph_service.py   # AGE → Cytoscape conversion
│   ├── frontend/src/          # Next.js 16 SPA
│   │   ├── app/page.tsx       # Dashboard shell (260 lines)
│   │   ├── components/        # GraphExplorer, KPICard
│   │   ├── components/modules/ # 7 AML modules
│   │   ├── services/api.ts    # 2 API methods
│   │   └── types/models.ts    # TypeScript interfaces
│   ├── api/server.py          # Legacy MVP API (99 lines)
│   ├── init-scripts/          # SQL schema initialization
│   │   ├── 01-init.sql        # Core tables + AGE graph
│   │   ├── 02-regulatory-procedures.sql  # OFAC screening
│   │   ├── 03-graph-schema.sql           # Super-node config
│   │   └── 04-users-and-workflow.sql     # Users + alert workflow
│   ├── etl/                   # Legacy ETL scripts
│   │   ├── rule_engine.py     # Cypher typology detection
│   │   ├── typologies.py      # Circular flow, smurfing, rapid movement
│   │   ├── graph_loader.py    # Graph projection
│   │   ├── run_batch.py       # Batch runner
│   │   ├── data_gen_bulk.py   # Synthetic data generator
│   │   └── bulk_synthetic_data.sql
│   ├── docker-compose.yml     # Main platform compose
│   └── requirements.txt       # Backend dependencies
├── etl/                       # Dagster ETL pipeline
│   ├── assets/
│   │   ├── ledger_ingest.py   # CSV → Polars → PostgreSQL
│   │   └── graph_projection.py # Relational → AGE graph
│   ├── sql/init_schema.sql    # ETL schema init
│   ├── repo.py                # Dagster repository definition
│   ├── workspace.yaml         # Dagster workspace config
│   ├── dagster.yaml           # Dagster config
│   ├── Dockerfile             # ETL container
│   ├── docker-compose.etl.yml # ETL compose (AGE + Dagster)
│   └── history/               # Dagster run history
├── input_data/                # Sample transaction CSVs
├── AML_spec.md                # Technical specification
├── SECURITY.md                # Security policy (ISO 27001, PCI-DSS, OWASP)
└── README.md                  # Full documentation (365 lines)
```

---

## 4. Component Analysis

### 4.1 ETL Pipeline

#### Dagster DAG (`etl/assets/`)

| Asset | Input | Output | Purpose |
|-------|-------|--------|---------|
| `raw_ledger_data` | CSV file | Polars DataFrame | Reads CSV, renames columns (`customer num` → `customer_num`, etc.), infers schema |
| `cleaned_ledger_data` | raw_ledger_data | Polars DataFrame | Drops nulls, SHA-256 hashes transactions, strips counterparty prefixes |
| `load_relational_tables` | cleaned_ledger_data | None (side effect) | Upserts into `core.customers`, `core.counterparties`, `core.transactions` via psycopg2 |
| `update_age_graph` | load_relational_tables | None (side effect) | PL/pgSQL loop projects relational data into Apache AGE graph via MERGE |

**DAG Flow:**
```
raw_ledger_data → cleaned_ledger_data → load_relational_tables → update_age_graph
```

#### Legacy ETL Scripts (`aml_platform/etl/`)

| File | Purpose |
|------|---------|
| `rule_engine.py` | Cypher-based rule engine for laundering typologies |
| `typologies.py` | Circular flow, smurfing, rapid movement detection logic |
| `graph_loader.py` | Loads screened staging data into AGE graph |
| `run_batch.py` | Batch orchestration runner |
| `data_gen_bulk.py` | Synthetic data generator for testing |
| `bulk_synthetic_data.sql` | SQL-based bulk synthetic data insertion |

#### ETL Schema (`etl/sql/init_schema.sql`)

```sql
-- Relational tables
core.customers        (customer_num PK)
core.counterparties   (counterparty_id PK, counterparty_name, is_merchant)
core.transactions     (txn_hash PK, FK→customers, FK→counterparties, 12 columns)
raw.wallet_ledger_dlq (Dead Letter Queue for failed ingestion)

-- Apache AGE graph: tap_and_go_network
-- Vertex labels: Customer, Counterparty, Merchant
-- Edge labels: TRANSFERRED, PAID
```

#### Docker Compose (ETL)

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `age_db` | apache/age | 5433→5432 | PostgreSQL + Apache AGE |
| `dagster_etl` | Custom (python:3.12-slim) | 3001→3000 | Dagster webserver |

---

### 4.2 Backend API (`aml_platform/backend/app/`)

#### Application Entry (`main.py`)

- FastAPI app with async lifespan management (init/close asyncpg pool)
- CORS middleware: `allow_origins=["*"]` with `allow_credentials=True`
- 5 router registrations: auth, admin, alerts, graph, reports
- Health check endpoint: `GET /health`

#### Database Layer (`db/session.py`)

- **Driver**: asyncpg (async PostgreSQL)
- **Connection pool**: min 2, max 20 connections
- **Init hook**: `LOAD 'age'` + `SET search_path = ag_catalog, "$user", public`
- **DI pattern**: `get_db()` async generator yields connection from pool
- **Global state**: `DatabaseState` singleton holds pool reference

#### Authentication & RBAC (`core/auth.py`)

| Component | Detail |
|-----------|--------|
| JWT Algorithm | HS256 |
| Token Expiry | 60 minutes |
| Password Hashing | bcrypt via passlib |
| Secret Key | **HARDCODED**: `"aml_super_secret_key_change_me"` |
| Audit Logger | Python logger `"aml_audit"` → stdout only |

**Role → Scope Mapping:**

| Role | Scopes | Accessible Endpoints |
|------|--------|---------------------|
| JUNIOR_ANALYST | `alert.read` | Feed, alert views |
| SENIOR_INVESTIGATOR | `alert.read`, `graph.explore` | + graph exploration, approve/reject |
| DEPARTMENT_HEAD | `alert.read`, `graph.explore` | + monthly reports |
| ADMIN | `alert.read`, `graph.explore` | + user management |

**RBAC Enforcement:**
- `get_current_user()` — decodes JWT, builds scope list
- `get_current_user_with_scope(required_scope)` — factory function, checks scope or role match, raises 403

#### API Endpoints

| Method | Endpoint | Auth | Role Required | Status | Notes |
|--------|----------|------|---------------|--------|-------|
| POST | `/api/v1/auth/login` | No | — | Working | Returns JWT token |
| GET | `/api/v1/alerts/feed` | Yes | alert.read | Working | 150 latest transactions, PII masked |
| GET | `/api/v1/alerts/` | Yes | alert.read | Working | Dummy — queries core.transactions |
| GET | `/api/v1/alerts/{id}` | Yes | alert.read | Working | Logs PII unmask for senior roles |
| POST | `/api/v1/alerts/{id}/assign` | Yes | alert.read | **Stub** | Returns `{"status": "assigned"}` |
| POST | `/api/v1/alerts/{id}/propose-close` | Yes | alert.read | **Stub** | Accepts notes, ignores them |
| POST | `/api/v1/alerts/{id}/approve` | Yes | SENIOR_INVESTIGATOR | **Stub** | Returns `{"status": "approved"}` |
| POST | `/api/v1/alerts/{id}/reject` | Yes | SENIOR_INVESTIGATOR | **Stub** | Validates notes length ≥ 5 |
| GET | `/api/v1/graph/network` | **No** | — | Working | **Unauthenticated!** Full topology |
| GET | `/api/v1/graph/explore/{id}` | Yes | SENIOR_INVESTIGATOR | Working | Ignores entity_id and depth |
| POST | `/api/v1/admin/users` | Yes | ADMIN | **Broken** | Sync DB calls on asyncpg |
| GET | `/api/v1/reports/monthly` | Yes | DEPARTMENT_HEAD | **Broken** | Sync DB calls on asyncpg |
| GET | `/health` | No | — | Working | Hardcoded response |

#### Services

**PII Masking Service** (`services/pii_service.py`):

| Sensitive Field | Masking Strategy |
|----------------|-----------------|
| `wallet_address`, `sender_wallet`, `receiver_wallet` | First 6 + `...` + last 4 chars |
| `entity_name`, `email`, `phone_number`, `sender_account`, `receiver_account` | `***REDACTED***` |

- Only `SENIOR_INVESTIGATOR` role sees unmasked data
- All other roles (including ADMIN, DEPARTMENT_HEAD) get masked data
- Recursive masking for nested dicts and lists

**Graph Service** (`services/graph_service.py`):

| Function | Purpose | Status |
|----------|---------|--------|
| `get_full_network(db, limit)` | Queries AGE graph, parses agtype, builds Cytoscape elements | Working (f-string SQL injection) |
| `get_neighborhood(db, entity_id, depth)` | Should explore subgraph | **Broken** — ignores all params, returns full network |

#### Pydantic Schemas (`schemas/user.py`)

```python
UserBase:     username, email (EmailStr), role
UserCreate:   inherits UserBase + password
UserOut:      inherits UserBase + id, is_active, created_at (orm_mode = True — v1 syntax)
Token:        access_token, token_type
TokenData:    username?, role?, id? (unused)
```

---

### 4.3 Frontend (`aml_platform/frontend/`)

#### Application Structure

| File | Lines | Purpose |
|------|-------|---------|
| `src/app/page.tsx` | 260 | Dashboard shell — top nav, sidebar, main workspace, right sidebar |
| `src/app/layout.tsx` | 33 | Root layout with Geist Sans + Geist Mono fonts |
| `src/app/globals.css` | 26 | Tailwind imports, unused CSS variables |
| `src/services/api.ts` | 21 | 2 API methods: fetchFeed(), fetchGraphNetwork() |
| `src/types/models.ts` | 65 | TypeScript interfaces: Channel, Customer, Payment, Alert, Case |
| `src/components/GraphExplorer.tsx` | 105 | Cytoscape.js wrapper with Discovery/Fast modes |
| `src/components/KPICard.tsx` | 50 | Reusable KPI display card |
| `src/components/modules/MonitoringFeed.tsx` | 93 | Transaction ledger table (live API) |
| `src/components/modules/AlertWorkbench.tsx` | 90 | L1/L2 review UI (static dummy data) |
| `src/components/modules/CaseManagement.tsx` | 103 | Investigation case view (static dummy data) |
| `src/components/modules/STRPreparation.tsx` | 70 | JFIU STR form (static placeholder) |
| `src/components/modules/ScreeningModule.tsx` | 79 | Sanctions screening UI (static placeholder) |
| `src/components/modules/GovernanceMIS.tsx` | 88 | HKMA KPI dashboard (static dummy data) |

**Total: 14 source files, ~1,089 lines of code**

#### Module Status

| Module | Component | API Calls | Data Source | Status |
|--------|-----------|-----------|-------------|--------|
| NETWORK | GraphExplorer + Dashboard | `GET /graph/network` | Backend AGE graph | **Live** |
| MONITORING | MonitoringFeed | `GET /alerts/feed` | Backend core.transactions | **Live** |
| ALERTS | AlertWorkbench | None | Hardcoded dummy data | **Static** |
| CASES | CaseManagement | None | Hardcoded dummy data | **Static** |
| STR | STRPreparation | None | Placeholder textareas | **Static** |
| SCREENING | ScreeningModule | None | Hardcoded dummy data | **Static** |
| GOVERNANCE | GovernanceMIS | None | Hardcoded dummy data | **Static** |

#### State Management

- **No global state library** (no Redux, Zustand, Context API)
- Local `useState` per component
- Lifted state in `page.tsx`: `activeModule`, `selectedEntity`, `isFastMode`, `graphData`
- `@tanstack/react-query` in package.json but **never used**
- `useEffect` + `fetch` for data fetching (no axios despite being in dependencies)

#### Styling

- **Tailwind CSS v4** with `@tailwindcss/postcss`
- **Dark theme only**: `bg-slate-950` base, slate/blue palette
- **Icons**: `lucide-react` (comprehensive usage)
- **Fonts**: Geist Sans + Geist Mono (Google Fonts)
- **Unused dependencies**: `framer-motion`, `clsx`, `tailwind-merge`, `shadcn-ui`

---

### 4.4 Database Schema

#### Relational Tables

**Staging Layer:**
| Table | Columns | Purpose |
|-------|---------|---------|
| `staging_fiat_raw` | transfer_id PK, sender/receiver accounts + routing, amount_usd, timestamp, status | Fiat SWIFT ingestion |
| `staging_crypto_raw` | tx_hash PK, sender/receiver wallets, asset_id, volume_native, volume_usd, network, timestamp, status | Crypto on-chain ingestion |

**Regulatory Layer:**
| Table | Columns | Purpose |
|-------|---------|---------|
| `ofac_blocklist` | entity_id PK, entity_type, entity_name, wallet_address, program, last_updated | Sanctions screening |
| `fatf_rules` | rule_id PK, sending/receiving jurisdiction, min_threshold_usd, required_info JSONB, active | Travel Rule |
| `dead_letter_queue` | error_id PK, source_table, raw_payload JSONB, error_message, inserted_at | Failed ingestion |
| `super_nodes` | node_id PK, infrastructure_type, description, date_added | Excluded high-connectivity nodes |

**Workflow Layer:**
| Table | Columns | Purpose |
|-------|---------|---------|
| `alerts` | alert_id PK, alert_type, severity, trigger_entity, related_transactions JSONB, status, created_at, resolved_at, assigned_to, maker_id, checker_id, resolution_notes, checker_notes | Alert queue with maker-checker |
| `public.users` | id PK, username, email, hashed_password (bcrypt), role ENUM, is_active, created_at | Auth users |

**Core Layer (ETL):**
| Table | Columns | Purpose |
|-------|---------|---------|
| `core.customers` | customer_num PK, created_at | Normalized customers |
| `core.counterparties` | counterparty_id PK, counterparty_name, is_merchant, created_at | Normalized counterparties |
| `core.transactions` | txn_hash PK, customer_num FK, counterparty_id FK, txn_date, txn_ref_no, txn_country, txn_currency, txn_currency_amount, txn_amount_in_hkd, cdi_code, txn_type, source_filename, loaded_at | Normalized transactions |

#### Apache AGE Graph

**Graph:** `aml_network`
| Element | Labels | Properties |
|---------|--------|-----------|
| Vertices | Entity, SuperNode | id, entity_name, wallet_address, etc. |
| Edges | Transfer | txn_hash, amount, timestamp, etc. |

**Graph:** `tap_and_go_network` (ETL)
| Element | Labels | Properties |
|---------|--------|-----------|
| Vertices | Customer, Counterparty, Merchant | id |
| Edges | TRANSFERRED, PAID | txn_hash, amount |

#### Stored Procedures

**`sp_screen_ofac()`** (`02-regulatory-procedures.sql`):
1. Screens `staging_fiat_raw` against `ofac_blocklist` (sender/receiver account match)
2. Screens `staging_crypto_raw` against `ofac_blocklist` (sender/receiver wallet match)
3. Inserts CRITICAL alerts for any matches
4. Transitions status from PENDING → SCREENED

---

### 4.5 Legacy/MVP API (`aml_platform/api/server.py`)

A standalone 99-line FastAPI server that appears to be an earlier prototype:

| Issue | Detail |
|-------|--------|
| Hardcoded credentials | `password="secure_password_123"` on line 24 |
| Mock RBAC | Header check: `Authorization: Bearer compliance_analyst_token` |
| Incomplete graph | Cypher query executed but results not parsed (line 89: `pass`) |
| Superseded | The modular backend in `backend/app/` replaces this |

---

## 5. Security Vulnerability Analysis

### CRITICAL

| # | Issue | File:Line | Impact |
|---|-------|-----------|--------|
| 1 | **Hardcoded JWT Secret** | `core/auth.py:13` | Anyone can forge tokens for any role. Secret: `"aml_super_secret_key_change_me"` |
| 2 | **Unauthenticated Graph Endpoint** | `api/v1/graph.py:9` | Full network topology exposed — all wallet addresses, entity relationships visible to anyone |
| 3 | **Wildcard CORS with Credentials** | `main.py:24` | `allow_origins=["*"]` + `allow_credentials=True` — invalid and dangerous combination |
| 4 | **Hardcoded DB Credentials** | `api/server.py:24` | `password="secure_password_123"` in legacy API |

### HIGH

| # | Issue | File:Line | Impact |
|---|-------|-----------|--------|
| 5 | **Sync/Async DB API Mismatch** | `auth.py:16-17`, `admin.py:19-30`, `reports.py:15-31` | Uses `db.cursor()`, `cursor.execute()`, `db.commit()` on asyncpg connections — **crashes at runtime** |
| 6 | **Stub Alert Lifecycle** | `alerts.py:59-77` | 4 workflow endpoints return hardcoded responses — assign, propose-close, approve, reject all non-functional |
| 7 | **Graph Neighborhood Ignores Parameters** | `graph_service.py:69-71` | `get_neighborhood()` returns full network regardless of `entity_id` or `depth` |

### MEDIUM

| # | Issue | File:Line | Impact |
|---|-------|-----------|--------|
| 8 | **SQL Injection via f-string** | `graph_service.py:13` | `LIMIT {limit}` interpolated directly into Cypher query |
| 9 | **PII Masking Bypass** | `graph.py:20` | Network endpoint hardcodes `"ADMIN"` role for masking, but endpoint is unauthenticated |
| 10 | **Pydantic v1 Syntax** | `schemas/user.py:19` | `orm_mode = True` should be `from_attributes = True` for Pydantic v2 |
| 11 | **Audit Logs Not Persisted** | `core/auth.py:74-91` | Only writes to Python stdout logger — not tamper-evident storage |
| 12 | **No Password Complexity Validation** | `schemas/user.py` | UserCreate accepts any password string |
| 13 | **No Rate Limiting on Login** | `auth.py` | No brute-force protection on login endpoint |
| 14 | **No Input Validation on Notes** | `alerts.py:65` | `propose_close` accepts notes but never uses them |

---

## 6. Frontend Code Quality Issues

| # | Issue | Severity | Detail |
|---|-------|----------|--------|
| 1 | **Single-page monolith** | Medium | No URL routing — can't bookmark, deep-link, or use browser history |
| 2 | **6 unused dependencies** | Low | `axios`, `framer-motion`, `clsx`, `tailwind-merge`, `shadcn-ui`, `@tanstack/react-query` in package.json but never imported |
| 3 | **5 of 7 modules static** | High | AlertWorkbench, CaseManagement, STRPreparation, ScreeningModule, GovernanceMIS have zero API integration |
| 4 | **No TypeScript on API layer** | Medium | `api.ts` returns untyped `any[]`; `models.ts` interfaces only used for dummy data |
| 5 | **No error boundaries** | Low | Single component crash takes down entire app |
| 6 | **No form validation** | Medium | STR and AlertWorkbench textareas have no validation or submission handlers |
| 7 | **No frontend authentication** | High | No auth headers on API calls, no session management, no protected routes |
| 8 | **Copy-pasted styling** | Low | Every module repeats identical card wrapper classes |
| 9 | **`any[]` typing in GraphExplorer** | Low | `data` prop loses type safety |
| 10 | **Generic metadata** | Low | `layout.tsx` still has `"Generated by create next app"` |
| 11 | **No loading skeletons** | Low | Full-screen spinner instead of skeleton UI |
| 12 | **`isMounted` anti-pattern** | Low | Should use AbortController with fetch |
| 13 | **No tests** | Medium | Zero test files in entire project |
| 14 | **No environment file** | Low | No `.env.example`; API URL falls back to `127.0.0.1:8000` |

---

## 7. Deployment Configuration

### Main Platform (`aml_platform/docker-compose.yml`)

| Service | Build Context | Port | Environment |
|---------|--------------|------|-------------|
| `aml-backend` | `./backend` | 8000→8000 | `DATABASE_URL` → `host.docker.internal:5433` |
| `aml-frontend` | `./frontend` | 3000→3000 | `NEXT_PUBLIC_API_URL` → `http://localhost:8000/api/v1` |

**Note:** No database service in main compose — depends on ETL compose's `age_db` running on port 5433.

### ETL Pipeline (`etl/docker-compose.etl.yml`)

| Service | Image/Build | Port | Volumes |
|---------|------------|------|---------|
| `age_db` | apache/age | 5433→5432 | `age_pg_data`, `init_schema.sql` mount |
| `dagster_etl` | Custom build | 3001→3000 | `./etl`, `./input_data` mounts |

---

## 8. Summary Metrics

| Metric | Value |
|--------|-------|
| Total Python files | 25 |
| Backend API files | 11 |
| Frontend source files | 14 (~1,089 LOC) |
| SQL schema files | 6 |
| Docker Compose files | 2 |
| API endpoints | ~13 (5 stubs, 2 broken at runtime) |
| Live frontend modules | 2 of 7 |
| Database engines | PostgreSQL 16 + Apache AGE |
| Auth mechanism | JWT (HS256) + bcrypt + 4-role RBAC |
| ETL framework | Dagster DAG (4 assets) |
| Security scan files | 1 (SECURITY_SCAN_20260403.md) |
| Documentation files | 3 (README.md, AML_spec.md, SECURITY.md) |

---

## 9. Assessment

**State:** MVP/Prototype

**Strengths:**
- Well-designed database schema with proper normalization
- Clean modular FastAPI architecture with lifespan management
- Comprehensive HKMA/JFIU compliance design in documentation
- Proper RBAC role hierarchy and scope-based access control
- PII masking service with role-based redaction
- Apache AGE integration for graph-based fund flow analysis
- Dagster ETL pipeline with idempotent data loading

**Critical Gaps:**
- 4 critical security vulnerabilities (hardcoded secrets, unauthenticated endpoints)
- Runtime crashes from sync/async DB API mismatch in 3 endpoints
- 5 of 7 frontend modules are non-functional static placeholders
- Alert lifecycle workflow completely unimplemented
- Graph exploration ignores entity and depth parameters
- Audit logs not persisted to tamper-evident storage

**Recommended Priority Fixes:**
1. Move JWT secret to environment variable
2. Add authentication to `GET /api/v1/graph/network`
3. Fix sync/async DB calls in `auth.py`, `admin.py`, `reports.py`
4. Implement alert lifecycle endpoints (assign, propose, approve, reject)
5. Fix `get_neighborhood()` to use entity_id and depth parameters
6. Restrict CORS to specific origins
7. Persist audit logs to database or tamper-evident log sink
```

