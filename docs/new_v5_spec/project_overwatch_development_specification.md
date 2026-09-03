# Project Overwatch — Development Specification

> **Project:** Unified AML Transaction Monitoring Platform — Fiat & Stablecoin  
> **Stablecoins:** AnchorPoint (SCB x HKT x Animoca Brands) · USDC  
> **Jurisdiction:** Hong Kong (HKMA Stablecoins Ordinance, AMLO Cap.615)  
> **Architecture:** On-prem / Hybrid Kubernetes | Event-driven Microservices  
> **Version:** 3.0  
> **Date:** 04 July 2026
>
> **Data Model:** This specification references the converged AML Data Model (27 entities, 6 domains). See Build Specification Section 4 for the complete entity reference, column definitions, and relationship diagram. The authoritative Mermaid ERD is maintained as `6. AML Data Model.mmd` in the project root.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Development Environment](#2-development-environment)
3. [Service Specifications](#3-service-specifications)
   - 3.1 Squad A — Core Platform
   - 3.2 Squad B — Blockchain & Analytics
   - 3.3 Squad C — Compliance UX
   - 3.4 Squad D — Platform & Infra
4. [Database Schemas](#4-database-schemas)
5. [API Contracts](#5-api-contracts)
6. [Kafka Event Map](#6-kafka-event-map)
7. [Infrastructure Configuration](#7-infrastructure-configuration)
8. [CI/CD Pipeline](#8-cicd-pipeline)
9. [Monitoring & Observability](#9-monitoring--observability)
10. [Testing Requirements](#10-testing-requirements)
11. [Task Assignment Matrix](#11-task-assignment-matrix)
12. [Development Timeline & Dependencies](#12-development-timeline--dependencies)
13. [Appendices](#13-appendices)

---

# 1. Architecture Overview

## 1.1 System Context

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          PAYMENTS / REMITTANCE                          │
│                          PLATFORM (EXTERNAL)                            │
└────────────────────────────┬────────────────────────────────────────────┘
                             │ POST /api/v1/transactions/screen
                             ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        AML GATEWAY (ingestion-service)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐ │
│  │ Fiat Ingest  │  │ On-Chain     │  │ Normalisation Engine          │ │
│  │ SWIFT/ISO    │  │ Transfer     │  │ → Canonical Transaction Schema │ │
│  │ 20022 / ACH  │  │ Events (RPC) │  └──────────┬───────────────────┘ │
│  └──────────────┘  └──────────────┘             │                     │
└─────────────────────────────────────────────────┼──────────────────────┘
                                                   │ Kafka Topics
                                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        TRANSACTION MONITORING ENGINE                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐ │
│  │ tme-engine   │  │ tme-ml       │  │ sanctions-service             │ │
│  │ Rules DSL    │  │ XGBoost/ONNX │  │ OFAC SDN + fuzzy match       │ │
│  │ YAML-based   │  │ SHAP         │  │ rapidfuzz                    │ │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────────┘ │
└─────────┼─────────────────┼────────────────────────┼───────────────────┘
          │                 │                        │
          └─────────────────┼────────────────────────┘
                            │
                   ┌────────▼────────┐
                   │  HOLD / APPROVE  │
                   │  / FLAG decision │
                   └────────┬────────┘
                            │
           ┌────────────────┼────────────────┐
           ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│ Payment API  │  │ CMS          │  │ ForensicDB        │
│ (sync reply) │  │ (case mgmt)  │  │ (tamper-proof     │
└──────────────┘  └──────────────┘  │  audit ledger)    │
                                    └──────────────────┘
```

## 1.2 Service Topology

| Service | Language | Framework | DB | Kafka Topics (Publish) | Kafka Topics (Subscribe) |
|---------|----------|-----------|----|----------------------|------------------------|
| `ingestion-service` | Python 3.12 | FastAPI | — | fiat.raw, onchain.raw, fiat.normalised, onchain.normalised, audit.events | — |
| `tme-engine` | Python 3.12 | FastAPI | PostgreSQL (rules) | screening.results, alerts.generated, audit.events | fiat.normalised, onchain.normalised |
| `tme-ml` | Python 3.12 | FastAPI (ONNX) | MinIO (models) | — | — |
| `sanctions-service` | Python 3.12 | FastAPI | — | screening.results, audit.events | screening.requests |
| `blockchain-indexer` | Go 1.22 | net/http | — | onchain.raw | — |
| `wallet-analytics-adapter` | Python 3.12 | FastAPI | Redis (cache) | — | — |
| `risk-scoring-service` | Python 3.12 | FastAPI | PostgreSQL | — | — |
| `travelrule-gateway` | Python 3.12 | FastAPI + Temporal | — | travelrule.results, forensic.events | travelrule.requests |
| `case-management-service` | Python 3.12 | FastAPI + Temporal | PostgreSQL | forensic.events | alerts.generated |
| `regulatory-reporting-service` | Python 3.12 | FastAPI | — | forensic.events | — |
| `forensic-audit-service` | Python 3.12 | FastAPI | PostgreSQL (ForensicDB) | — | forensic.events, audit.events |
| `audit-service` | Python 3.12 | FastAPI | PostgreSQL (audit) | — | audit.events |
| `batch-scanning-service` | Python 3.12 | FastAPI + Airflow | TimescaleDB, MinIO (Parquet) | batch.alerts, batch.results, batch.scan.progress | batch.scan.commands |
| `aml-portal` | TypeScript 5 | Next.js 14 | — | — | — |

## 1.3 Database Topology

| Database | Engine | Purpose | Services with Access |
|----------|--------|---------|---------------------|
| `aml_core` | PostgreSQL 16+ (3-node Patroni) | Primary operational data: customers, txns, screenings, alerts, batch scan results | ingestion (write), tme-engine (read/write), case-management (read/write), risk-scoring (read/write), sanctions (read), batch-scanning-service (read/write) |
| `aml_audit` | PostgreSQL 16+ (2-node, append-only) | Operational audit trail with hash-chain | audit-service (write, sole), case-management (read), forensic-audit (read) |
| `aml_forensic` | PostgreSQL 16+ (2-node, WORM, separate VLAN) | Tamper-proof forensic ledger | forensic-audit-service (write, sole), verifier (read-only replica) |
| `aml_graph` | PostgreSQL 16+ + Apache AGE | Graph relationships, party graph traversal for structuring/layering detection | case-management (read/write), batch-scanning-service (read) |
| `aml_analytics` | TimescaleDB (PG ext) | Time-series metrics, ML features, behavioral baselines, peer group stats | ml-training (write), dashboard (read), batch-scanning-service (read/write) |
| `redis_cache` | Redis 7.2+ | Wallet scores, sanctions index, rate limits, sessions | wallet-analytics-adapter (write), tme-engine (read), sanctions (read), ingestion (read) |
| `minio_store` | MinIO (4-node erasure) | Objects: model artifacts, evidence files, SAR PDFs, backups, batch Parquet data, daily briefings | tme-ml (write), case-management (write/read), regulatory-reporting (write), backup jobs, batch-scanning-service (write/read) |

# 2. Development Environment

## 2.1 Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12+ | Primary backend language |
| Go | 1.22+ | Blockchain indexer |
| Node.js | 20 LTS | Frontend |
| Docker | 24+ | Container images |
| kubectl | 1.30+ | K8s interaction |
| Helm | 3.15+ | Chart management |
| Temporal CLI | 1.24+ | Workflow testing |
| Kafka CLI | 3.7+ | Topic management |
| psql | 16+ | Database interaction |

## 2.2 Local Development Setup

```bash
# Clone repository
git clone <repo-url> project-overwatch
cd project-overwatch

# Create Python virtual environment per service
cd services/ingestion && python3 -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt    # Python services
npm install                        # Frontend (apps/aml-portal)
go mod download                    # Go services (services/blockchain-indexer)

# Run tests
pytest --cov=service --cov-fail-under=85
go test ./...
npm run test
```

## 2.3 Local Services (Docker Compose)

```yaml
# docker-compose.yml
services:
  postgres-aml-core:
    image: postgres:16
    environment:
      POSTGRES_DB: aml_core
      POSTGRES_USER: overwatch
      POSTGRES_PASSWORD: dev_only
    ports: ["5432:5432"]
    volumes: ["./infra/db/aml_core/init.sql:/docker-entrypoint-initdb.d/"]

  kafka:
    image: confluentinc/cp-kafka:7.7
    environment:
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
    ports: ["9092:9092"]

  redis:
    image: redis:7.2
    ports: ["6379:6379"]

  temporal:
    image: temporalio/auto-setup:1.24
    ports: ["7233:7233"]
```

## 2.4 Repository Structure

```
project-overwatch/
├── apps/
│   └── aml-portal/                 # Next.js admin portal
│       ├── src/app/                # App Router pages
│       │   ├── dashboard/
│       │   ├── alerts/
│       │   ├── cases/
│       │   ├── reports/
│       │   ├── config/
│       │   ├── admin/
│       │   ├── audit/
│       │   └── forensic/
│       ├── src/components/         # Shared UI components
│       ├── src/lib/                # Utils, API client, auth
│       ├── tailwind.config.ts
│       └── package.json
├── services/
│   ├── ingestion/                  # Squad A
│   │   ├── src/
│   │   │   ├── api/                # FastAPI routes
│   │   │   ├── normalisers/        # Fiat & on-chain normalisers
│   │   │   ├── kafka/              # Kafka producer config
│   │   │   └── models/             # Pydantic schemas
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── tme-engine/                 # Squad A
│   │   ├── src/
│   │   │   ├── engine/             # Rule evaluation core
│   │   │   ├── rules/              # YAML rule definitions
│   │   │   ├── ml/                 # ML client adapter
│   │   │   └── kafka/              # Kafka consumer/producer
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── tme-ml/                     # Squad A
│   │   ├── src/
│   │   │   ├── inference/          # ONNX runtime wrapper
│   │   │   ├── features/           # Feature engineering
│   │   │   └── models/             # XGBoost model artifacts
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── sanctions-service/          # Squad A
│   │   ├── src/
│   │   │   ├── screening/          # Name & wallet screening
│   │   │   ├── lists/              # Sanctions list management
│   │   │   └── kafka/
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── audit-service/              # Squad A
│   │   ├── src/
│   │   │   ├── consumer/           # Kafka audit event consumer
│   │   │   ├── hashing/            # SHA-256 chain
│   │   │   └── api/                # Read-only query API
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── blockchain-indexer/         # Squad B
│   │   ├── cmd/
│   │   ├── internal/
│   │   │   ├── chain/              # Per-chain worker
│   │   │   │   ├── ethereum/
│   │   │   │   ├── polygon/
│   │   │   │   ├── arbitrum/
│   │   │   │   ├── optimism/
│   │   │   │   ├── base/
│   │   │   │   └── solana/
│   │   │   ├── kafka/               # Kafka producer
│   │   │   └── monitor/             # Health monitoring
│   │   ├── go.mod
│   │   └── Dockerfile
│   ├── wallet-analytics-adapter/   # Squad B
│   │   ├── src/
│   │   │   ├── vendors/            # Adapters: TRM, Chainalysis, Elliptic
│   │   │   ├── cache/              # Redis caching layer
│   │   │   └── circuit/            # Circuit breaker
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── risk-scoring-service/       # Squad B
│   │   ├── src/
│   │   │   ├── scoring/            # Factor implementations
│   │   │   ├── triggers/           # Re-scoring triggers
│   │   │   └── api/
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── travelrule-gateway/         # Squad C
│   │   ├── src/
│   │   │   ├── workflows/          # Temporal workflow definitions
│   │   │   ├── notabene/           # Notabene TRP integration
│   │   │   └── kafka/
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── case-management-service/    # Squad C
│   │   ├── src/
│   │   │   ├── workflows/          # CMS Temporal workflows
│   │   │   ├── api/                # REST API endpoints
│   │   │   ├── state-machine/      # Alert lifecycle enforcement
│   │   │   └── evidence/           # Evidence upload service
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── regulatory-reporting-service/  # Squad C
│   │   ├── src/
│   │   │   ├── templates/          # SAR/STR XML templates
│   │   │   ├── filing/             # JFIU / HKMA submission
│   │   │   └── dags/               # Airflow DAG definitions
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── forensic-audit-service/     # Squad C
│       ├── src/
│       │   ├── consumer/           # Kafka forensic event consumer
│       │   ├── hashing/            # SHA-256 + Merkle tree
│       │   ├── witness/            # External witness publisher
│       │   ├── verifier/           # forensic-verifier CLI
│       │   └── api/                # Read-only query API
│       ├── tests/
│       ├── Dockerfile
│       └── requirements.txt
│   ├── batch-scanning-service/     # Squad C (T+1 Batch)
│       ├── src/
│       │   ├── dags/               # Airflow DAG: t1_batch_scan_pipeline
│       │   ├── jobs/               # 10 K8s Job definitions per analysis
│       │   │   ├── behavioral_baseline/
│       │   │   ├── peer_group_comparison/
│       │   │   ├── structuring_detection/
│       │   │   ├── velocity_pattern_mining/
│       │   │   ├── graph_anomaly_detection/
│       │   │   ├── ensemble_ml_scoring/
│       │   │   ├── rule_effectiveness/
│       │   │   ├── layering_detection/
│       │   │   ├── sanctions_retrospective/
│       │   │   └── sar_pre_population/
│       │   ├── enrichment/         # Customer/profile enrichment
│       │   ├── alerting/           # Batch alert generation + dedup
│       │   ├── briefing/           # Daily AML briefing PDF generator
│       │   └── api/                # REST API (trigger/status/results/history)
│       ├── tests/
│       ├── Dockerfile
│       └── requirements.txt
├── infra/
│   ├── k8s/                        # K8s manifests (Kustomize)
│   │   ├── base/                   # Common resources
│   │   ├── overlays/
│   │   │   ├── dev/
│   │   │   ├── staging/
│   │   │   └── prod/
│   │   └── namespaces/
│   │       ├── ingestion/
│   │       ├── monitoring/
│   │       ├── analytics/
│   │       ├── compliance/
│   │       ├── forensic/
│   │       ├── portal/
│   │       ├── batch/
│   │       ├── audit/
│   │       └── infra/
│   ├── db/                         # Database schemas
│   │   ├── aml_core/
│   │   ├── aml_audit/
│   │   ├── aml_forensic/
│   │   └── aml_graph/
│   ├── ci/                         # CI pipeline templates
│   │   ├── python-template.yml
│   │   ├── ts-template.yml
│   │   └── go-template.yml
│   └── monitoring/                 # Grafana dashboards
│       ├── cluster-overview.json
│       ├── service-metrics.json
│       └── forensic-integrity.json
├── docs/                           # Documentation
│   ├── project_overwatch_todo_build_list.md
│   └── project_overwatch_agent_squad_specs.md
├── docker-compose.yml              # Local dev environment
├── Makefile
└── README.md
```

# 3. Service Specifications

## 3.1 Squad A — Core Platform

**Lead:** Backend Engineer (Python)  
**Repo prefix:** `services/`  
**Start week:** 4 (after platform is provisioned by Squad D)

### 3.1.1 ingestion-service

**Purpose:** Entry point for all transaction data. Normalises heterogeneous sources into canonical schema. Handles synchronous fiat pre-settlement screening and asynchronous on-chain event ingestion.

**Dependencies:**
- **Requires:** Kafka topics provisioned (Squad D, D.DM.01-06), aml_core schema (Squad B/B.1)
- **Provides:** fiat.normalised, onchain.normalised topics consumed by tme-engine

**API Endpoints:**

| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| POST | `/api/v1/transactions/screen` | Submit single txn for pre-settlement screening | `{external_ref, source_type, sender_name, sender_account, amount, currency, ...}` | `{transaction_id, decision, risk_score, rule_triggers[], hold_reason?}` |
| POST | `/api/v1/transactions/batch-screen` | Submit batch for async screening | `{transactions: []}` | `{batch_id, status}` |
| GET | `/api/v1/transactions/batch/{id}/status` | Poll batch status | — | `{batch_id, status, results[]}` |
| POST | `/api/v1/wallets/screen` | Submit wallet(s) for risk scoring | `{wallets: ["0x..."]}` | `{results: [{wallet, risk_score, tags}]}` |
| GET | `/api/v1/transactions/{ref}` | Retrieve screening detail | — | Full canonical txn + all screening results |
| GET | `/api/v1/health` | Health check | — | `{status, version, uptime, dependencies: {kafka, db, ...}}` |
| GET | `/api/v1/forensic/verify` | Public chain verification | — | `{status, last_verified, chain_integrity}` |

**Kafka Topics Published:**
```
fiat.raw          → Key: external_ref     → Partition count: 6
onchain.raw       → Key: chain_id+tx_hash → Partition count: 12
fiat.normalised   → Key: customer_id      → Partition count: 6
onchain.normalised→ Key: customer_id      → Partition count: 12
audit.events      → Key: event_id         → Partition count: 3
```

**Task List (Squad A to execute):**

- [ ] **A.IN.01** — FastAPI application scaffold with health check, Prometheus metrics middleware, structured logging
- [ ] **A.IN.02** — POST /api/v1/transactions/fiat — validate input via Pydantic, normalise to canonical schema, publish to fiat.raw, wait for TME decision (reply-to pattern), return decision to caller
- [ ] **A.IN.03** — Batch file import module: SFTP poller for SWIFT MT/ISO 20022 files; parse, normalise, batch-publish to fiat.raw
- [ ] **A.IN.04** — Async Kafka producer client (aiokafka) — idempotent, retry with backoff, delivery callbacks
- [ ] **A.IN.05** — Fiat normaliser: SWIFT MT103/MT202 → canonical schema; ISO 20022 pacs.008 → canonical schema
- [ ] **A.IN.06** — On-chain normaliser: ERC-20 Transfer event log → canonical schema; Solana SPL Transfer → canonical schema
- [ ] **A.IN.07** — POST /api/v1/transactions/batch-screen — receives batch, returns batch_id, processes asynchronously
- [ ] **A.IN.08** — GET /api/v1/transactions/batch/{id}/status — polls batch processing state; returns results when complete
- [ ] **A.IN.09** — POST /api/v1/wallets/screen — proxies to wallet-analytics-adapter (Squad B); returns aggregated result
- [ ] **A.IN.10** — GET /api/v1/transactions/{ref} — retrieves from aml_core by external_ref
- [ ] **A.IN.11** — GET /api/v1/health — checks Kafka connectivity, DB connectivity, upstream service health
- [ ] **A.IN.12** — GET /api/v1/forensic/verify — proxies to forensic-audit-service
- [ ] **A.IN.13** — Pydantic model definitions for canonical transaction (all 20 fields) + schema validation
- [ ] **A.IN.14** — FX conversion: calls external FX rate API (cached); converts non-USD to USD equivalent
- [ ] **A.IN.15** — OpenAPI 3.1 spec auto-generation via FastAPI; Swagger UI at /docs
- [ ] **A.IN.16** — Rate limiting: 100 req/s per API key; token-bucket per client IP
- [ ] **A.IN.17** — mTLS verification on all incoming requests; client cert → service identity mapping
- [ ] **A.IN.18** — Audit event publishing: log every transaction submission, decision, and error to audit.events
- [ ] **A.IN.19** — Forensic event publishing: log manual overrides/interventions to forensic.events
- [ ] **A.IN.20** — Publish normalised transactions to fiat.normalised / onchain.normalised (enriched with wallet scores)

**Acceptance Criteria:**
- 100 fiat txns/sec throughput; p95 <200ms synchronous
- Batch 10K txns completes <30s
- Canonical schema validated: fiat wire = stablecoin transfer structurally identical
- All audit events published correctly to audit.events

### 3.1.2 tme-engine

**Purpose:** Central decision engine. Consumes normalised transactions, evaluates deterministic rules, incorporates ML scores, produces hold/release/flag decisions.

**Dependencies:**
- **Requires:** fiat.normalised, onchain.normalised topics; PostgreSQL aml_core for rule definitions; wallet-analytics-adapter for risk scores
- **Provides:** screening.results, alerts.generated topics

**API Endpoints (internal):**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/decide` | Evaluate single transaction (sync) |
| POST | `/decide/batch` | Evaluate batch (async) |
| POST | `/config/rules/reload` | Hot-reload rule definitions from DB |
| GET | `/config/rules` | List all rules with current state |
| GET | `/metrics` | Prometheus metrics |

**Rule Definition DSL (YAML):**
```yaml
rules:
  - id: "VELOCITY_SAME_ADDRESS_1H"
    name: "Velocity - Same Address (1 Hour)"
    category: VELOCITY
    enabled: true
    tier_applies_to: ["LOW", "MEDIUM", "HIGH"]
    condition: >
      velocity_count(customer_id, "beneficiary", window_1h) > 5
    score_if_triggered: 45
    action: "FLAG"
    description: ">5 txns to same address within 1 hour"

  - id: "THRESHOLD_HKD_1M"
    name: "Threshold - HKD 1M Single Transfer"
    category: THRESHOLD
    enabled: true
    tier_applies_to: ["MEDIUM", "HIGH"]
    condition: >
      amount_hkd > 1000000
    score_if_triggered: 70
    action: "HOLD"
    description: "Single transfer exceeds HKD 1 million"
```

**Task List:**

- [ ] **A.TM.01** — Kafka consumer for fiat.normalised and onchain.normalised (aiokafka, consumer groups)
- [ ] **A.TM.02** — In-memory sliding window: dict[customer_id] = deque[(timestamp, amount, beneficiary)] per window size; O(1) append/evict; Thread-safe
- [ ] **A.TM.03** — YAML rule definition schema (Pydantic model for rule config); parser with validation on load
- [ ] **A.TM.04** — Sandboxed Python expression evaluator (restricted globals, whitelisted functions: velocity_count, sum_amount, txn_count, etc.)
- [ ] **A.TM.05** — Rule versioning: every rule change creates new snapshot in aml_core.risk_rule_version; hot-reload via POST /config/rules/reload
- [ ] **A.TM.06** — Tier gate logic: function get_rules_for_tier(tier) → filters rule list; LOW = less strict rules, HIGH = all rules
- [ ] **A.TM.07** — Parallel rule evaluation: asyncio.gather for all enabled rules; each rule returns AlertResult {triggered: bool, score: int, details: dict}
- [ ] **A.TM.08** — Composite score: deterministic_score * weight_d + ml_score * weight_m (weights per tier)
- [ ] **A.TM.09** — Decision mapper: score 0-30 → APPROVE, 31-65 → FLAG, 66-100 → HOLD
- [ ] **A.TM.10** — Kafka producer: publish to screening.results; if FLAG or HOLD, publish to alerts.generated
- [ ] **A.TM.11** — POST /decide — synchronous endpoint for external callers (waits for evaluation, returns decision)
- [ ] **A.TM.12** — POST /decide/batch — async; returns batch_id; processes via background tasks
- [ ] **A.TM.13** — Prometheus metrics: decision_counter{decision}, rule_trigger_counter{rule_id}, evaluation_duration_histogram, scores_by_tier
- [ ] **A.TM.14** — Audit event for every decision: transaction_id, decision, score, rule_triggers → audit.events

**Rule Library Tasks:**

- [ ] **A.TM.15** — Velocity rule: >5 txns to same address within 1 hour
- [ ] **A.TM.16** — Velocity rule: >HKD 500K cumulative daily outflow
- [ ] **A.TM.17** — Threshold rule: >HKD 1M single transfer
- [ ] **A.TM.18** — Threshold rule: >500K USDC single transfer
- [ ] **A.TM.19** — Counterparty rule: high-risk jurisdiction (list configurable)
- [ ] **A.TM.20** — Counterparty rule: unhosted wallet above threshold (HKD 100K)
- [ ] **A.TM.21** — Pattern rule: round-dollar amounts in stablecoin (amount % 100 == 0)
- [ ] **A.TM.22** — Pattern rule: structuring detection — count txns under HKD 8,000 in 24hr window > configurable threshold
- [ ] **A.TM.23** — Geographic rule: IP/session country does not match customer registered jurisdiction

**Acceptance Criteria:**
- 100 fiat txns/sec through full pipeline; p95 <500ms
- Rule hot-reload: YAML updated in DB → POST /config/rules/reload → new rules active in <10s
- All 9 rules tested with known input/output pairs
- Composite score weights configurable per tier via YAML

### 3.1.3 tme-ml

**Purpose:** ML-based anomaly detection to complement deterministic rules. Runs in shadow mode initially, graduates to active scoring.

**Dependencies:**
- **Requires:** Features from aml_analytics (TimescaleDB), model artifacts from MinIO
- **Provides:** ML score + SHAP explanations to tme-engine via gRPC or REST

**API Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/predict` | Return anomaly probability + SHAP for a feature vector |
| GET | `/model/current` | Current model metadata (version, training date, metrics) |
| POST | `/model/load` | Load specific model version from MinIO |
| GET | `/health` | Health check |

**Task List:**

- [ ] **A.ML.01** — FastAPI scaffold with ONNX runtime session management (model loaded, inference context)
- [ ] **A.ML.02** — Feature engineering: raw txn data → feature vector {log_amount, freq_1h, freq_24h, freq_7d, z_score, wallet_risk, counterparty_risk, jurisdiction_risk, hour_of_day, day_of_week, amount_ratio_to_baseline}
- [ ] **A.ML.03** — XGBoost classifier: initial training on synthetic labelled data (legitimate + suspicious patterns); eval metric: AUC-ROC >0.85
- [ ] **A.ML.04** — SHAP explainer: TreeExplainer for XGBoost; returns per-feature contribution to anomaly score
- [ ] **A.ML.05** — Shadow mode: model produces score and SHAP values but tme-engine only logs them; does NOT affect decision
- [ ] **A.ML.06** — Versioned model storage: model.xgb + metadata.json pushed to MinIO bucket `model-artifacts/`; versioned by git commit hash
- [ ] **A.ML.07** — Model loading: on startup, load latest model from MinIO; POST /model/load to hot-swap

**Acceptance Criteria:**
- Inference latency <100ms p95
- SHAP explanations returned in response
- Shadow mode: logs predictions vs actual outcomes for offline evaluation

### 3.1.4 sanctions-service

**Purpose:** Real-time and batch sanctions screening of names, entities, and wallet addresses.

**Dependencies:**
- **Requires:** Sanctions list data feed (LexisNexis/Refinitiv SFTP)
- **Provides:** Screening results to screening.results topic

**API Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/screen` | Name + wallet screening (sync) |
| POST | `/screen/wallet` | Wallet hash exact-match (sync) |
| POST | `/screen/batch` | Batch screening (async) |
| GET | `/lists/status` | Current sanctions list version + loaded entries count |

**Task List:**

- [ ] **A.SC.01** — POST /screen — accepts names[] + wallets[]; runs fuzzy matching + wallet exact match; returns matching results
- [ ] **A.SC.02** — POST /screen/wallet — accepts wallet[]; O(1) lookup in in-memory hash map; returns match + list name
- [ ] **A.SC.03** — Fuzzy matching: rapidfuzz library; Levenshtein ratio >0.85 threshold; token-set ratio; Soundex fallback for non-Latin scripts
- [ ] **A.SC.04** — OFAC SDN list loader: download/parse CSV → build in-memory hash map: dict[address] = SdnEntry{list_name, entity_name, sanctions_program}
- [ ] **A.SC.05** — Kafka consumer for screening.requests → batch screening; processes 1000 records/min; publishes results to screening.results
- [ ] **A.SC.06** — Daily SFTP pull: connect to sanctions provider, download latest list, diff against previous version, trigger update
- [ ] **A.SC.07** — Confidence scoring: 0-100; >=80 = BLOCK, 60-79 = REVIEW, <60 = PASS
- [ ] **A.SC.08** — Batch re-screening: upon list update, re-screen all active parties within 24 hours
- [ ] **A.SC.09** — Publish each screening result to screening.results topic
- [ ] **A.SC.10** — Audit: log every list update (old version → new version, additions, removals) to forensic.events

**Acceptance Criteria:**
- OFAC SDN 100K+ entries loaded; exact wallet match <1ms
- Fuzzy match "John Smith" vs "Jon Smith" → 0.92 confidence (PASS threshold config: >0.80)
- Batch re-screen of 10K records completes <5 min
- Daily list update detected; diff logged correctly

### 3.1.5 audit-service

**Purpose:** Immutable operational audit trail. Captures all system-level events with hash-chain integrity verification.

**Dependencies:**
- **Requires:** aml_audit PostgreSQL
- **Provides:** None (internal only; query via DB)

**Task List:**

- [ ] **A.AU.01** — Idempotent Kafka consumer for audit.events topic; dedup by event_id
- [ ] **A.AU.02** — INSERT into aml_audit.audit_event: compute SHA-256(prev_event.record_hash || event_type || json_payload || timestamp)
- [ ] **A.AU.03** — Hash-chain integrity checker (hourly cron): iterate all events since last checkpoint; recompute hashes; report any divergence
- [ ] **A.AU.04** — Read-only REST: GET /audit/events?from=&to=&type=&limit= — query with pagination
- [ ] **A.AU.05** — Prometheus gauge: audit_chain_integrity (1=clean, 0=tampered); alert on 0

**Acceptance Criteria:**
- 10K audit events ingested/min
- Integrity checker detects modified event within 1 hour
- UPDATE/DELETE rejected at DB role level (confirmed via test)

---

## 3.2 Squad B — Blockchain & Analytics

**Lead:** Backend Engineer (Go) + Backend Engineer (Python)  
**Repo prefix:** `services/`  
**Start week:** 6 (blockchain-indexer) / 8 (wallet-analytics) / 6 (risk-scoring)

### 3.2.1 blockchain-indexer

**Purpose:** Real-time on-chain transaction monitoring across 6 EVM chains + Solana for AnchorPoint HKDR and USDC transfers.

**Dependencies:**
- **Requires:** RPC endpoints for each chain
- **Provides:** onchain.raw topic consumed by ingestion-service

**Token Contracts to Monitor:**

| Chain | Chain ID | USDC Contract | AnchorPoint Contract |
|-------|----------|---------------|---------------------|
| Ethereum | 1 | 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 | TBD |
| Polygon | 137 | 0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359 | TBD |
| Arbitrum | 42161 | 0xaf88d065e77c8cC2239327C5EDb3A432268e5831 | TBD |
| Optimism | 10 | 0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85 | TBD |
| Base | 8453 | 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913 | TBD |
| Solana | — | EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v | TBD |

**Task List:**

- [ ] **B.BC.01** — Go project scaffold: module structure, Makefile, linter config
- [ ] **B.BC.02** — Sarama Kafka producer: async producer with callbacks; topic: onchain.raw; key: chain_id+tx_hash
- [ ] **B.BC.03** — Chain worker library: interface `ChainWorker { Start(ctx), Stop(), Health() }` + base implementation: RPC polling, event decoding, configurable interval + confirmations
- [ ] **B.BC.04** — Health monitoring: per-worker goroutine health probe; Prometheus metrics: blocks_behind_head, txns_indexed_total, rpc_errors_total, worker_state(0=stopped,1=running,2=error)
- [ ] **B.BC.05** — EVM transfer parser: eth_getLogs → decode Transfer event (indexed: from, to; data: value); map to TokenTransfer struct
- [ ] **B.BC.06** — Ethereum worker: archive node RPC, 12-block confirmation, poll interval 12s
- [ ] **B.BC.07** — Polygon worker: full node RPC, checkpoint finality, poll interval 5s
- [ ] **B.BC.08** — Arbitrum worker: L2 node RPC, 12-block confirmation, poll interval 3s
- [ ] **B.BC.09** — Optimism worker: L2 node RPC, 12-block confirmation, poll interval 3s
- [ ] **B.BC.10** — Base worker: L2 node RPC, 12-block confirmation, poll interval 3s
- [ ] **B.BC.11** — Solana worker: geyser plugin gRPC or RPC streaming for SPL token transfers
- [ ] **B.BC.12** — Programmable event filter: ConfigMap per chain — contract_addresses[], tracked_wallets[]
- [ ] **B.BC.13** — Backfill: CLI command `blockchain-indexer backfill --chain ethereum --from-block 18000000 --to-block 18500000`; batch writes 10K events/txn
- [ ] **B.BC.14** — Graceful shutdown: SIGTERM → persist last indexed block per chain to PostgreSQL → close Kafka producer → exit
- [ ] **B.BC.15** — On-chain enrichment: before publishing, call wallet-analytics-adapter for sender/recipient risk scores; add to event metadata
- [ ] **B.BC.16** — Lag alert: if chain head age >60s → Prometheus alert; auto-restart worker

**Acceptance Criteria:**
- All 6 chains indexed within 30s of block finality
- Backfill 1M blocks completes <2 hours
- Single chain RPC failure does not affect other workers
- State persisted; resume after restart — no double-publish

### 3.2.2 wallet-analytics-adapter

**Purpose:** Vendor-agnostic blockchain wallet risk scoring with caching and circuit breaking.

**Dependencies:**
- **Requires:** Redis cache, TRM Labs / Chainalysis API keys
- **Provides:** Wallet risk scores to ingestion-service, tme-engine, blockchain-indexer

**Key Contract (Common Output Schema):**
```json
{
  "wallet": "0x1234...",
  "risk_score": 75,
  "risk_level": "HIGH",
  "confidence": 0.92,
  "tags": ["sanctioned_entity", "mixer_interaction"],
  "entity": "Lazarus Group",
  "exposure_hops": 2,
  "total_volume_30d_usd": 15000000,
  "txn_count_30d": 450,
  "top_interactions": [{"address": "0x...", "volume_usd": 5000000, "entity": "Binance"}],
  "last_updated": "2026-07-03T12:00:00Z",
  "vendor": "TRM_LABS"
}
```

**Task List:**

- [ ] **B.WA.01** — Abstract adapter interface: `class VendorAdapter(ABC): async def score(addresses: list[str]) -> list[WalletScore]; async def health() -> VendorHealth;`
- [ ] **B.WA.02** — TRM Labs adapter: REST API integration; API key auth; request batching (100 addresses/batch)
- [ ] **B.WA.03** — Chainalysis KYT adapter: fallback; same interface as TRM
- [ ] **B.WA.04** — POST /score — accepts `{wallets: ["0x..."]}`, returns `{results: [WalletScore]}`
- [ ] **B.WA.05** — POST /batch/score — bulk; 100 addresses max per call
- [ ] **B.WA.06** — Redis cache: key = `wallet:{chain_id}:{address}`; value = WalletScore JSON; TTL = 86400s (static) / 3600s (dynamic); cache-aside pattern
- [ ] **B.WA.07** — N-hop exposure: for wallets above configurable risk threshold, request chain analysis (number of hops configurable 1-3)
- [ ] **B.WA.08** — Vendor rate limiter: token bucket per vendor; `tokens_per_minute` configurable; replenish 1 token/sec
- [ ] **B.WA.09** — Circuit breaker: >5 failures/min → open circuit → skip vendor, return cached score or null → close after 60s cooldown
- [ ] **B.WA.10** — GET /vendors/status — per-vendor: healthy, rate_limit_remaining, circuit_state (open/closed/half-open)
- [ ] **B.WA.11** — Cache warmup: on start, load known wallet addresses from DB → pre-fetch scores
- [ ] **B.WA.12** — GET /cache/status — cache size, hit_rate, miss_rate, expiry_count, top vendor by volume

**Acceptance Criteria:**
- 100 addresses scored <30s with warm cache
- Cache hit rate >90% after 1 hour runtime
- Circuit breaker opens within 30s of vendor failure; closes after cooldown
- Vendor switch (TRM -> Chainalysis) requires config change only, no code change

### 3.2.3 risk-scoring-service

**Purpose:** Real-time customer risk score updates based on transaction behaviour, wallet risk, and compliance signals.

**Dependencies:**
- **Requires:** aml_core PostgreSQL; wallet scores from wallet-analytics-adapter
- **Provides:** Customer risk tier + score for TME decision weighting

**API Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/score/transaction` | Submit txn for live score update |
| GET | `/customer/{id}/risk-profile` | Current risk profile (tier, score, factor breakdown) |
| POST | `/customer/{id}/recalculate` | Manual re-score trigger |

**Task List:**

- [ ] **B.RS.01** — FastAPI scaffold with async SQLAlchemy + PostgreSQL connection
- [ ] **B.RS.02** — POST /score/transaction: receives canonical txn + wallet risk scores; updates customer score; returns score contribution
- [ ] **B.RS.03** — GET /customer/{id}/risk-profile: returns `{tier, score, factors: {velocity, wallet, counterparty, sanctions, pep, adverse_media, jurisdiction, source_of_funds}, history: [{score, reason, timestamp}][]}`
- [ ] **B.RS.04** — Factor implementations: velocity_deviation (z-score), wallet_risk (from adapter), counterparty_risk, sanctions_hit_count, pep_flag, adverse_media_recency (days since -> score), jurisdiction_risk, source_of_funds_consistency
- [ ] **B.RS.05** — Re-score triggers: on new txn → async update; on sanctions list update → re-score all affected customers; on PEP DB update → re-score; on manual POST /recalculate
- [ ] **B.RS.06** — Tier escalation: consecutive high-scoring events counter; 3 events → auto-upgrade LOW→MEDIUM or MEDIUM→HIGH; configurable thresholds
- [ ] **B.RS.07** — Time-decay: factors older than 90 days decay by 0.5% per day; full reset after 180 days of inactivity
- [ ] **B.RS.08** — POST /customer/{id}/recalculate: manual trigger with reason; publishes forensic event with old_score, new_score, reason, operator_id
- [ ] **B.RS.09** — Prometheus metrics: score_distribution{risk_score} histogram, tier_changes_total{tier_from, tier_to}, rescore_duration_seconds

**Acceptance Criteria:**
- Customer score updates within 30s of new transaction
- 3 consecutive HIGH events -> tier escalation
- Manual re-score completes <2s; forensic event recorded
- Time-decay correctly reduces stale scores

---

## 3.3 Squad C — Compliance UX

**Lead:** Backend Engineer (Python) + Frontend Engineer (TypeScript)  
**Repo prefix:** `services/` + `apps/`  
**Start week:** 18 (behind Squad A + B)

### 3.3.1 travelrule-gateway

**Purpose:** Travel Rule compliance for transfers >= HKD 8,000. Handles counterparty discovery, TRP messaging, and unhosted wallet EDD.

**Dependencies:**
- **Requires:** travelrule.requests topic (from tme-engine), Notabene TRP API
- **Provides:** travelrule.results topic

**Temporal Workflow — TravelRuleWorkflow:**

```
Input: {transaction_id, amount, currency, sender_wallet, beneficiary_wallet, chain_id, sender_name, sender_address, beneficiary_name}

1. Counterparty Discovery (Notabene directory):
   - Query beneficiary VASP by wallet address
   - If found -> go to Step 2
   - If not found -> go to Step 4

2. Construct TRP Message:
   - Originator: full_name, address, account_number, jurisdiction
   - Beneficiary: full_name, account_number
   - Send via Notabene TRP API
   - Wait for response (max 5 minutes, 3 retries)

3. On Response:
   - If valid -> publish PASS to travelrule.results
   - If timeout -> go to Step 4

4. Unhosted Wallet / Timeout Path:
   - Create EDD case in case-management-service
   - Check paired fiat account risk
   - Publish MANUAL_REVIEW to travelrule.results
```

**Task List:**

- [ ] **C.TR.01** — Temporal worker scaffold (Python SDK): `temporal_worker = Worker.create(...)`
- [ ] **C.TR.02** — Kafka consumer for travelrule.requests topic; start TravelRuleWorkflow per message
- [ ] **C.TR.03** — Notabene integration: sign JWT with HSM key; call counterparty lookup endpoint; parse response
- [ ] **C.TR.04** — TRP message construction: build IVMS101 Originator + Beneficiary payloads
- [ ] **C.TR.05** — TRP message send: POST to Notabene; await response via callback webhook
- [ ] **C.TR.06** — Timeout + retry: 5 min timeout, 3 retries with exponential backoff; escalate to manual if exhausted
- [ ] **C.TR.07** — Unhosted wallet branch: create case in CMS (POST /cases); set priority HIGH; flag for enhanced monitoring
- [ ] **C.TR.08** — TravelRuleWorkflow Temporal definition: `@workflow.defn` with `@activity.defn` for each step; set retry policy; set timeout
- [ ] **C.TR.09** — Kafka producer: publish PASS/HOLD/MANUAL_REVIEW to travelrule.results
- [ ] **C.TR.10** — Forensic event on manual intervention: log operator_id, transaction_id, action, reason
- [ ] **C.TR.11** — Prometheus metrics: workflow_duration_seconds{status}, counterparty_match_rate, timeout_rate

**Acceptance Criteria:**
- VASP-to-VASP transfer: TravelRuleWorkflow complete <2 min
- Unhosted wallet >= HKD 8,000: triggers EDD path within 30s
- Timeout after 5 min: HOLD decision + manual review case created
- Manual release/block: forensic event recorded

### 3.3.2 case-management-service

**Purpose:** Alert lifecycle management, investigation workspace, evidence management, SAR draft generation.

**Dependencies:**
- **Requires:** alerts.generated topic, PostgreSQL aml_core
- **Provides:** Case management REST API for frontend; forensic events

**Alert Lifecycle State Machine:**

```
NEW → ASSIGNED → UNDER_INVESTIGATION → CLOSED_FALSE_POSITIVE
                                    → CLOSED_MONITORING
                                    → SAR_FILED
All transitions enforced by Temporal workflow (no direct DB mutation)
```

**API Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/alerts` | List alerts (paginated, filterable) |
| GET | `/alerts/{id}` | Alert detail with linked data |
| POST | `/cases` | Create case from alert |
| GET | `/cases` | List cases |
| GET | `/cases/{id}` | Full case detail |
| POST | `/cases/{id}/transitions` | State transition |
| POST | `/cases/{id}/notes` | Add note |
| POST | `/cases/{id}/evidence` | Upload evidence |

**Task List:**

- [ ] **C.CM.01** — Kafka consumer for alerts.generated topic
- [ ] **C.CM.02** — State machine: allowed_transitions dict + Temporal workflow guard
- [ ] **C.CM.03** — AlertAssignmentWorkflow: round-robin by team queue depth; in-app + email notification; escalate if unassigned >1hr
- [ ] **C.CM.04** — InvestigationWorkflow: POST /hold (tme-engine API) → gather evidence → additional blockchain queries → timeline → document findings; 4hr SLA timer
- [ ] **C.CM.05** — SARApprovalWorkflow: peer review → manager approval → compliance officer sign-off → file to JFIU; 24hr SLA timer
- [ ] **C.CM.06** — EscalationWorkflow: >1hr → notify team lead; >2hr → notify compliance manager; >4hr → notify MLRO
- [ ] **C.CM.07** — GET /alerts: page, limit, sort_by, filters={status, tier, rule, date_from, date_to, assignee}
- [ ] **C.CM.08** — GET /alerts/{id}: linked_transactions[], triggered_rules[], risk_score_breakdown{total, deterministic, ml}, customer_summary
- [ ] **C.CM.09** — POST /cases: create case from alert; set initial priority based on risk score
- [ ] **C.CM.10** — POST /cases/{id}/transitions: validate against state machine; execute Temporal workflow; return new state
- [ ] **C.CM.11** — GET /cases/{id}: case object + linked alerts + linked transactions + notes + evidence + timeline
- [ ] **C.CM.12** — Transaction timeline: group by date; expandable items with txn summary, risk score, wallet addresses
- [ ] **C.CM.13** — Customer 360: risk tier badge, recent activity (last 50 txns across all rails), linked wallets, PEP/adverse media status
- [ ] **C.CM.14** — Network graph data: GET /cases/{id}/graph — returns nodes[{id, label, type, risk}] + edges[{source, target, amount}]
- [ ] **C.CM.15** — Notes: POST → INSERT note with type + text; read-only after save; no edit/delete
- [ ] **C.CM.16** — Evidence: POST multipart; validate mime type + size (<20MB); stream to MinIO; store hash in case record; ClamAV scan
- [ ] **C.CM.17** — SAR draft pre-population: map case data → STR XML fields; return draft for review
- [ ] **C.CM.18** — SAR draft CRUD: create, read, update (before filing), preview XML
- [ ] **C.CM.19** — Read-only audit replica: periodic sync of case data to read-only audit DB
- [ ] **C.CM.20** — Publish all case state transitions + notes + evidence to forensic.events
- [ ] **C.CM.21** — Publish SAR lifecycle events to forensic.events (DRAFTED, REVIEWED, APPROVED, FILED, ACKNOWLEDGED)

**Acceptance Criteria:**
- 4 Temporal workflows operational; end-to-end alert->case->investigation->SAR lifecycle passes
- Invalid state transitions rejected with 422
- All state changes + decisions published to forensic.events

### 3.3.3 regulatory-reporting-service

**Purpose:** SAR/STR generation in JFIU-compatible format, HKMA periodic reporting.

**Dependencies:**
- **Requires:** Case data from case-management-service
- **Provides:** SAR XML filing to JFIU; HKMA reports

**Task List:**

- [ ] **C.RR.01** — Jinja2 XML template: JFIU STREAMS 2 STR format; fields mapped from case data
- [ ] **C.RR.02** — POST /sar/generate: case_id → fetch case → populates template → return XML preview
- [ ] **C.RR.03** — POST /sar/submit: finalise, store XML in case record, update status to FILED
- [ ] **C.RR.04** — JFIU STREAMS 2 upload: web portal assisted (semi-automated); SFTP XML (v2)
- [ ] **C.RR.05** — POST /filing/submit: upload to STREAMS 2; record ack reference
- [ ] **C.RR.06** — GET /filing/{id}/status: query submission status; update ack receipt
- [ ] **C.RR.07** — HKMA statistical return: aggregate transaction volumes + alert totals by month/quarter
- [ ] **C.RR.08** — POST /reports/generate: type+period → generate report → store in MinIO
- [ ] **C.RR.09** — Airflow DAG `sar_status_check`: daily query pending SAR submissions for JFIU ack
- [ ] **C.RR.10** — Airflow DAG `hkma_monthly`: run day 1 of month; generate HKMA return
- [ ] **C.RR.11** — Airflow DAG `aml_quarterly`: run first day of quarter; generate comprehensive report
- [ ] **C.RR.12** — Forensic events: log each SAR lifecycle transition (DRAFTED → FILED → ACKNOWLEDGED)

**Acceptance Criteria:**
- SAR XML validates against JFIU STREAMS 2 schema
- Draft → review → approve → file workflow functional end-to-end
- Monthly HKMA report auto-generated on schedule (Airflow DAG)

### 3.3.4 forensic-audit-service

**Purpose:** Sole writer to ForensicDB. Cryptographically seals all manual human interactions with SHA-256 hash chains, Merkle trees, and external witness publishing.

**Dependencies:**
- **Requires:** forensic.events kafka topic, aml_forensic PostgreSQL (separate VLAN)
- **Provides:** Tamper-proof evidence for regulatory audit

**Tasks - Core Ingestion:**

- [ ] **C.FA.01** — Kafka consumer for forensic.events topic (partitioned by event_category; idempotent)
- [ ] **C.FA.02** — Event validation: reject if missing operator_id, session_id, client_ip, user_agent, justification; log rejection to separate alert
- [ ] **C.FA.03** — Record hashing: `record_hash = SHA-256(record_type || json_payload || operator_id || timestamp || previous_record_hash)`
- [ ] **C.FA.04** — INSERT into correct ForensicDB table (alert_disposition, case_transition, rule_change, risk_override, access_log, sar_lifecycle)
- [ ] **C.FA.05** — Global hash chain append: `chain_n = SHA-256(chain_{n-1}.hash || table_name || record_hash || now())`

**Tasks - Merkle Tree:**

- [ ] **C.FA.06** — Per-table Merkle tree: collect all records inserted in current hour; build balanced binary tree; compute root hash
- [ ] **C.FA.07** — Store Merkle root in `forensic.merkle_root` with table_name, block_start, block_end, computed_at
- [ ] **C.FA.08** — Hourly witness: publish composite hash (all roots + chain head) to Blockchain (Polygon testnet OP_RETURN or smart contract)

**Tasks - Verification:**

- [ ] **C.FA.09** — forensic-verifier CLI: `forensic-verifier verify --from-genesis` -> recomputes all hashes, compares to stored hashes
- [ ] **C.FA.10** — Verifier output: PASS (all hashes match) / FAIL (list of record IDs + expected hash + actual hash)
- [ ] **C.FA.11** — Scheduled verifier: runs every 15 min on read-only replica; P0 alert on FAIL via AlertManager
- [ ] **C.FA.12** — GET /forensic/records?category=&from=&to=&limit= — auditor read-only paginated query
- [ ] **C.FA.13** — GET /forensic/chain/verify — quick integrity check: returns {status: "PASS"|"FAIL", last_verified_at, records_checked, integrity_pct}
- [ ] **C.FA.14** — GET /forensic/merkle/{table}/{date} — return Merkle root for specific table+date

**Tasks - Witness & Retention:**

- [ ] **C.FA.15** — Witness publisher: compute composite hash (all roots + chain head) → send to Polygon testnet → store `{published_at, tx_id, composite_hash}`
- [ ] **C.FA.16** — Daily attestation: sign global chain head + all Merkle roots with HSM key; upload to S3 Object Lock bucket in separate cloud account
- [ ] **C.FA.17** — Retention manager: archive ForensicDB records older than 7 years to WORM optical media; verify export hash chain; log chain-of-custody event

**Acceptance Criteria:**
- ForensicDB accepts writes; hash chain verifiable
- forensic-verifier detects single-bit tampering
- External witness published hourly; txId verifiable on block explorer
- P0 alert fires within 1 minute of chain break
- WORM enforced at DB, filesystem, and storage array levels

### 3.3.5 batch-scanning-service (T+1 Batch Scanning)

**Purpose:** Next-day batch transaction scanning complementing the real-time TME. Performs computationally intensive analyses (behavioral baselining, peer group comparison, multi-account structuring, network graph anomaly detection, ensemble ML scoring, cross-rail layering) that are impossible within the real-time <500ms latency SLA.

**Dependencies:**
- **Requires:** aml_core (canonical transactions), aml_analytics (TimescaleDB for feature store), wallet-analytics-adapter (Squad B), Apache AGE graph, Airflow (Squad D), MinIO batch-data bucket
- **Provides:** batch.alerts topic, batch.results topic, daily AML briefing PDF

**Airflow DAG:** `t1_batch_scan_pipeline` — scheduled daily at 02:00 HKT; 8-stage pipeline (Pre-flight → Data Extraction → Enrichment → Parallel Analysis → ML Scoring → Alert Generation → Daily Briefing → Feedback Loop); completes within 4 hours for 500K transactions.

**API Endpoints:**

| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| POST | `/api/v1/batch/scan/trigger` | Trigger ad-hoc scan for date | `{scan_date: "YYYY-MM-DD"}` | `{run_id, status: "QUEUED", estimated_completion}` |
| GET | `/api/v1/batch/scan/{run_id}/status` | Get scan run progress | — | `{run_id, scan_date, status, current_stage, jobs_completed, jobs_total, txns_processed}` |
| GET | `/api/v1/batch/scan/{run_id}/results` | Get full scan results | — | `{run_id, scan_date, txns_processed, alerts_generated, analysis_breakdown, daily_briefing_path}` |
| GET | `/api/v1/batch/scan/daily-briefing/{date}` | Get daily briefing PDF link | — | `{briefing_path, summary}` |
| GET | `/api/v1/batch/scan/history` | List past scan runs | `?from=&to=&page=` | `{runs[], total}` |
| DELETE | `/api/v1/batch/scan/{run_id}` | Purge scan results (enable re-run) | — | `{success, message}` |

**Kafka Topics Produced:**

```
batch.alerts       → Key: customer_id  → Partition count: 6  → Retention: 90d
batch.results      → Key: run_id       → Partition count: 6  → Retention: 365d
batch.scan.progress→ Key: run_id       → Partition count: 3  → Retention: 7d
```

**Kafka Topics Consumed:**

```
batch.scan.commands→ Key: run_id       → Partition count: 3  → Triggers scan pipeline
```

**10 Batch-Only Analysis Modules (Parallel Kubernetes Jobs):**

| # | Analysis | Description | Output |
|---|----------|-------------|--------|
| 1 | Full-Day Customer Behavioral Baselining | Per-customer daily stats vs 30/90-day baseline; >3 sigma flagging | Behavioral deviation scores |
| 2 | Peer Group Comparative Analysis | Group by segment/jurisdiction/income; flag peer group outliers | Peer group anomaly flags |
| 3 | Multi-Account Structuring Detection | Traverse party graph (Apache AGE); aggregate linked accounts; detect threshold evasion | Structuring cluster alerts |
| 4 | Velocity Pattern Mining (Multi-Day) | 7-day txn history; time-series decomposition; classify ramping/burst-and-pause/cyclical | Pattern classification + alerts |
| 5 | Network Graph Anomaly Detection | Full daily graph; PageRank + Louvain community detection; historical baseline comparison | Graph anomaly scores |
| 6 | Ensemble ML Scoring (Full Feature Set) | XGBoost ensemble from MinIO; full feature vectors; batch inference; SHAP explanations | Risk scores + SHAP values |
| 7 | Rule Effectiveness Retrospective | Per-rule alert rate, FPR, detection overlap with batch; rule tuning recommendations | Tuning recommendations JSON |
| 8 | Cross-Rail Layering Detection (Full Fund Flow) | Fiat-to-stablecoin-to-fiat flow reconstruction; 4+ hop layering detection; fund flow trail data | Layering alerts + trail data |
| 9 | Sanctions/Screening Retrospective | Re-screen all daily txns against latest sanctions list; detect stale-list-misses | Retrospective screening alerts |
| 10 | SAR Pre-Population Intelligence | For high-confidence findings (>70); pre-compute SAR data; generate draft XML; link to alert | Draft SAR XML + data |

**Tasks:**

- [ ] **C.BT.01** — FastAPI service scaffold: health check, OpenAPI spec, structured logging, Prometheus metrics middleware
- [ ] **C.BT.02** — Airflow DAG `t1_batch_scan_pipeline`: define 8 stages with dependencies; configure retries (3 per stage with exponential backoff); set SLA timers per stage
- [ ] **C.BT.03** — Pre-flight Sensor: GET /health on ingestion-service; query blockchain-indexer lag metrics; poll all chains for finality on previous day; timeout 30 min; emit batch.scan.progress
- [ ] **C.BT.04** — Data Extraction stage: SELECT all canonical_transaction records for target_date (00:00-23:59 HKT) from aml_core; export as Parquet (PyArrow/Pandas) to MinIO `batch-data/YYYY/MM/DD/`; track progress; <30 min for 500K records
- [ ] **C.BT.05** — Enrichment stage: load Parquet from MinIO; JOIN customer_profiles, wallet_scores (call Squad B adapter), peer_group_assignments; write enriched Parquet back to MinIO
- [ ] **C.BT.06** — Parallel Analysis Dispatcher: generate K8s Job YAML per analysis (10 jobs); `kubernetes_asyncio.client.BatchV1Api.create_namespaced_job()`; monitor Job statuses; collect results into batch_scan_result table
- [ ] **C.BT.07** — Behavioral Baselining Job: compute per-customer daily stats (total_volume, txn_count, avg_amount, beneficiary_diversity, time_of_day_distribution, rail_mix_ratio); compare against 30/90-day baseline from TimescaleDB; flag >3 sigma deviations
- [ ] **C.BT.08** — Peer Group Comparison Job: assign customers to groups by segment + jurisdiction + income_band + product_usage; compute group-level statistics (median, IQR, stddev); flag customers outside IQR bounds; store baselines in batch_peer_group (recompute monthly)
- [ ] **C.BT.09** — Structuring Detection Job: traverse party graph via Apache AGE Cypher queries; identify linked accounts/parties; aggregate daily outflow across linked set; detect combined outflow exceeding thresholds while individual accounts below; generate structuring cluster alert JSON with linked account details
- [ ] **C.BT.10** — Velocity Pattern Mining Job: pull 7-day txn history per customer from TimescaleDB hypertable; apply STL time-series decomposition (trend + seasonal + residual); classify: ramping (monotonic increase over 3-5 days), burst-and-pause (intra-day spike then dormancy >48h), cyclical (weekly periodicity); output pattern classification + confidence score
- [ ] **C.BT.11** — Graph Anomaly Detection Job: build full daily transaction graph (nodes: parties/wallets, edges: transfers with amount/currency); run PageRank for influence scoring; run Louvain community detection; compute edge anomaly scores (amount z-score within community); compare community structure delta vs historical baseline; output anomaly scores per node + per edge
- [ ] **C.BT.12** — Ensemble ML Scoring Job: load production XGBoost ensemble model (versioned, from MinIO model-artifacts bucket); compute full feature vectors (behavioral + peer group + graph centrality + temporal pattern + cross-rail interaction + wallet risk features); run batch inference on complete daily dataset; generate risk scores with SHAP explanations per transaction; store in TimescaleDB
- [ ] **C.BT.13** — Rule Effectiveness Retrospective Job: for each real-time rule, compute alert_rate, false_positive_rate (from ForensicDB analyst disposition feedback), detection_overlap_with_batch; identify transactions that WOULD have been flagged under adjusted thresholds; generate rule tuning recommendations as structured JSON with reason codes
- [ ] **C.BT.14** — Layering Detection Job: reconstruct complete fiat-to-stablecoin-to-fiat fund flows traversing the daily transaction graph; detect multi-hop layering (fiat deposit → crypto purchase → unhosted wallet → exchange → fiat withdrawal, 4+ hops); build fund flow trail data (nodes + edges as Cytoscape.js-compatible JSON); output layering alerts with trail visualization data
- [ ] **C.BT.15** — Sanctions Retrospective Job: re-screen all daily transactions against the latest sanctions list version (loaded from sanctions-service); compare screening results with real-time results; flag any transaction that passed screening on a stale mid-day list version; flag transactions involving entities added to sanctions lists on same day; output retrospective screening alerts
- [ ] **C.BT.16** — SAR Pre-Population Job: for high-confidence batch findings (batch_risk_score >70), pre-compute SAR-relevant data: transaction timeline (ordered by time), counterparty details (known entities, risk scores), fund flow summary (total volume, rails used, hop count), risk factor breakdown (which analyses triggered, scores, explanations); pre-populate SAR draft XML (Jinja2 STREAMS 2 template); store draft in case record; link to batch alert
- [ ] **C.BT.17** — Batch Alert Generator: aggregate findings from all 10 analyses; deduplicate by txn_id (same txn flagged by multiple analyses → single alert with all trigger analysis_types); compute composite batch_risk_score = weighted sum of individual analysis scores; set priority based on score bands (LOW: 0-30, MEDIUM: 31-65, HIGH: 66-100); publish to batch.alerts topic
- [ ] **C.BT.18** — CMS Integration: read batch.alerts; POST to case-management-service /cases with source=BATCH_SCAN, priority=LOW (default, lower urgency than real-time alerts), enrich case context with batch analysis findings and pre-populated SAR drafts
- [ ] **C.BT.19** — Daily AML Briefing Generator: compile top 10 riskiest txns, peer group anomaly summary, rule effectiveness metrics (real-time vs batch), false positive trends, new pattern detections, SAR pre-population queue; render as PDF with matplotlib tables and Recharts-based chart images; store on MinIO daily-briefings bucket (90d retention); generate email notification (via SMTP/SendGrid) to compliance team
- [ ] **C.BT.20** — POST /api/v1/batch/scan/trigger: validate scan_date (must be past, not future); create batch_scan_run record (status: QUEUED); trigger Airflow DAG via REST API; return run_id + estimated completion
- [ ] **C.BT.21** — GET /api/v1/batch/scan/{run_id}/status: query batch_scan_run; return current_stage, stage_progress, jobs_completed/total, txns_processed
- [ ] **C.BT.22** — GET /api/v1/batch/scan/{run_id}/results: query batch_scan_result + batch_scan_run; return full analysis_breakdown + daily_briefing_path + alert summary
- [ ] **C.BT.23** — GET /api/v1/batch/scan/daily-briefing/{date}: lookup briefing PDF path in MinIO; return download URL + summary metadata
- [ ] **C.BT.24** — GET /api/v1/batch/scan/history: paginated list of past runs with filter by date range; sort by scan_date DESC
- [ ] **C.BT.25** — DELETE /api/v1/batch/scan/{run_id}: soft-delete results (mark status = PURGED); enable idempotent re-run of same date
- [ ] **C.BT.26** — Kafka producers: batch.scan.commands (DAG→service), batch.scan.progress (per stage), batch.alerts (alert generator→CMS), batch.results (summary→dashboard)
- [ ] **C.BT.27** — Database migrations: `batch_scan_run` (run_id UUID PK, scan_date DATE, status, started_at, completed_at, txns_processed, alerts_generated, analysis_results JSONB, error_log TEXT), `batch_scan_result` (result_id UUID PK, run_id FK, txn_id, analysis_type, anomaly_score, findings JSONB, alert_generated BOOL), `batch_alert` (alert_id UUID PK, run_id FK, txn_id, analysis_type, risk_score, alert_reason TEXT, priority, status, case_id FK), `batch_peer_group` (group_id UUID PK, group_name, segment, jurisdiction, income_band, member_count, median_daily_volume, iqr_low, iqr_high), `batch_behavioral_baseline` (customer_id FK, baseline_date, total_volume_30d, avg_txn_amount_30d, txn_count_30d, beneficiary_diversity_30d, rail_mix_ratio_30d, stddev_volume; TimescaleDB hypertable, 90d chunks)
- [ ] **C.BT.28** — Publish all batch findings, alert dispositions, and briefing events to forensic.events topic for tamper-proof audit trail
- [ ] **C.BT.29** — Prometheus metrics: batch_scan_duration_seconds (histogram, by run_id), batch_jobs_completed, batch_jobs_failed, batch_alerts_generated_total, batch_txns_processed_total, batch_briefing_generation_seconds, batch_stage_duration_seconds (histogram, by stage)

**Acceptance Criteria:**
- Airflow DAG triggers automatically at 02:00 HKT daily; completes within 4 hours for 500K txns
- Pre-flight sensor verifies ingestion-service health + all chains finality before proceeding
- All 10 analyses execute in parallel Kubernetes Jobs; each completes <20 min
- Behavioral baseline deviation catches >3 sigma anomalies with explainable outlier reports
- Multi-account structuring detection catches 3+ linked accounts aggregating above threshold
- Ensemble ML scores all transactions with SHAP explanations; scores stored and retrievable
- Cross-rail layering detection reconstructs full 4+ hop fiat-to-stablecoin-to-fiat flows
- Batch alerts deduplicated and published to batch.alerts; CMS cases created with source=BATCH_SCAN
- Daily AML briefing PDF generated and emailed to compliance team within 5 min of scan completion
- Idempotent: re-running same date overwrites previous results; DELETE /api/v1/batch/scan/{run_id} enables clean re-run
- All findings and dispositions published to forensic.events (complete audit trail)
- Grafana dashboard "T+1 Batch Scanning" renders run history, stage latency, alert trends, anomaly breakdowns

### 3.3.6 aml-portal (Frontend)

**Purpose:** AML Admin Portal used by compliance analysts for daily case investigation and monitoring.

**Dependencies:**
- **Requires:** REST APIs from case-management-service, tme-engine, regulatory-reporting-service, forensic-audit-service
- **Tech Stack:** Next.js 14 (App Router), React 18, TypeScript 5, shadcn/ui, Tailwind CSS 5, Cytoscape.js, Recharts, React Query 5, Zustand

**Task List:**

- [ ] **C.PO.01** — Scaffold Next.js 14 App Router with TypeScript strict mode + path aliases
- [ ] **C.PO.02** — shadcn/ui init + theme: brand colours (navy #1B3A5C, grey #556B82), light mode, Calibri font family
- [ ] **C.PO.03** — React Query provider; configure global defaults (staleTime: 30s, retry: 3)
- [ ] **C.PO.04** — Zustand stores: `useUIStore` (sidebar, theme, session), `useFilterStore` (alert filters, date range)
- [ ] **C.PO.05** — Keycloak OIDC: next-auth or next-keycloak; login page, token refresh, role-based route guards
- [ ] **C.PO.06** — Layout: sidebar nav (collapsible), top bar (breadcrumb, user avatar + role badge + logout), notification bell + dropdown
- [ ] **C.PO.07** — Responsive breakpoints: desktop (1200px+), tablet (768-1199px), mobile (<768px) — mobile read-only

**Dashboard (Module 1):**

- [ ] **C.PO.08** — Dashboard page: row of stat cards (total alerts, open cases, pending SARs, SLA breaches) + date range picker (24h, 7d, 30d, 90d, custom)
- [ ] **C.PO.09** — Alert volume chart (Recharts BarChart): time series with breakdown by risk tier (coloured stacked bars)
- [ ] **C.PO.10** — Alert-to-case conversion rate: AreaChart with trend line over date range
- [ ] **C.PO.11** — False-positive rate: RadialBarChart gauge (0-100%) + line chart trend
- [ ] **C.PO.12** — SAR filing volume: StackedBarChart (draft/reviewed/filed/acknowledged)
- [ ] **C.PO.13** — Avg case resolution time: BarChart with p50/p95/p99 overlay
- [ ] **C.PO.14** — Queue backlog: BarChart with aging distribution buckets
- [ ] **C.PO.15** — SLA compliance: Table with investigator name, team, assigned count, within SLA %, breach count
- [ ] **C.PO.16** — Customer risk tier: PieChart (LOW/MEDIUM/HIGH/PEP/SANCTIONED) with count and percentage
- [ ] **C.PO.17** — Export: browser print trigger → PDF (via @media print CSS)

**Alert Queue (Module 2):**

- [ ] **C.PO.18** — GET /alerts → Table with columns: timestamp, alert_id, risk_tier (badge), triggered_rules (tags), customer_name, status, assignee; server-side pagination; filters panel
- [ ] **C.PO.19** — Alert detail page: risk score breakdown card, linked transactions table (expandable rows), triggered rules list with descriptions and scores
- [ ] **C.PO.20** — Customer 360: summary card with risk tier, recent txns (last 10), linked wallets (expandable), PEP badge, MSB indicator
- [ ] **C.PO.21** — Wallet risk: score gauge, tags list (coloured), high-risk interactions count, chain analysis summary text

**Case Management (Module 3):**

- [ ] **C.PO.22** — Cases list: Table (status badge, priority, assignee, case age); bulk actions (assign, escalate); CSV export
- [ ] **C.PO.23** — Case detail workspace: 3-panel responsive layout (50/30/20 split); timeline left, investigation centre, customer profile right
- [ ] **C.PO.24** — Transaction timeline: accordion grouped by date; each item: amount, currency, source_type, risk_score, wallet addresses (truncated + copy button)
- [ ] **C.PO.25** — Note system: textarea + type selector (Observation/Action/Escalation); submit → appended with timestamp + operator name; no delete/edit
- [ ] **C.PO.26** — Evidence upload: dropzone (react-dropzone); file list with name, size, type, hash (SHA-256), scan status badge; max 20MB
- [ ] **C.PO.27** — SAR draft: form pre-populated from case data; editable text fields; XML preview button; Submit for Approval button
- [ ] **C.PO.28** — Network graph: Cytoscape.js instance in panel; nodes: parties (rounded rect) + wallets (circle); edges: directed arrows coloured by amount; legend
- [ ] **C.PO.29** — SAR approval UI: progress stepper (Peer Review → Manager → Compliance Officer → Filed); current stage highlighted
- [ ] **C.PO.30** — Case audit timeline: chronological expandable list of all events, state transitions, decisions

**Configuration (Module 4):**

- [ ] **C.PO.31** — /config/rules: Table of rules (name, category, enabled toggle, shadow-mode toggle, tier applicability); version dropdown; history diff view
- [ ] **C.PO.32** — /config/thresholds: Inline editable table (tier rows × rule category columns); save button shows diff confirmation
- [ ] **C.PO.33** — /admin/users: Table with name, email, role dropdown, status; search; invite user form
- [ ] **C.PO.34** — /audit/logs: Search form (event type, date range, user, resource) + results table; CSV export; detail expand
- [ ] **C.PO.35** — /forensic/verify: Input field for chain head hash + Verify button → displays PASS (green) / FAIL (red) with details

**Reporting (Module 5):**

- [ ] **C.PO.36** — /reports: SAR list (searchable, filterable by date/status); HKMA return list; schedule configuration form
- [ ] **C.PO.37** — SAR preview: XML viewer with syntax highlighting + collapsible sections; edit in place; Submit to JFIU button
- [ ] **C.PO.38** — Scheduling: date picker, frequency (single/daily/monthly/quarterly), format (PDF/CSV/XML), Airflow DAG reference display

**Acceptance Criteria:**
- Login via Keycloak; RBAC routes enforced (analyst cannot access /admin/users)
- Dashboard renders 8 KPI widgets with live data <3s first load
- 10K alerts table renders <3s; detail page loads <1s
- Investigation workspace: all panels functional with test data
- /forensic/verify returns PASS for valid chain head, FAIL for tampered

---

## 3.4 Squad D — Platform & Infrastructure

**Lead:** DevOps / Platform Engineer + Security Engineer  
**Repo prefix:** `infra/`  
**Start week:** 0 (foundation for all)

### 3.4.1 Kubernetes Cluster

- [ ] **D.K8.01** — Provision 3 control-plane + 6 worker nodes (Ubuntu 24.04 LTS)
- [ ] **D.K8.02** — Install k3s/RKE2 + Calico CNI
- [ ] **D.K8.03** — VLAN segmentation: DMZ, application, data, forensic (isolated), management
- [ ] **D.K8.04** — HAProxy (L4) + Nginx Ingress (L7) with HSM-backed TLS
- [ ] **D.K8.05** — Kubernetes NetworkPolicies: default-deny cross-namespace
- [ ] **D.K8.06** — Resource quotas per namespace
- [ ] **D.K8.07** — Prometheus operator + Grafana: cluster/node/pod metrics; 30d retention
- [ ] **D.K8.08** — Loki + Promtail: log aggregation; 90d retention
- [ ] **D.K8.09** — Tempo: distributed tracing via OpenTelemetry; 14d retention
- [ ] **D.K8.10** — AlertManager: P0 SMS/PagerDuty, P1 email+Slack, P2 Slack
- [ ] **D.K8.11** — Velero: K8s backup (etcd + PV snapshots); weekly to MinIO
- [ ] **D.K8.12** — Jumpbox bastion host: SSO+MFA; no direct SSH to nodes
- [ ] **D.K8.13** — HPA configuration for stateless services (CPU + Kafka lag)

### 3.4.2 Stateful Services

- [ ] **D.DB.01** — PostgreSQL CloudNativePG operator: 3-node aml_core Patroni cluster
- [ ] **D.DB.02** — 2-node aml_audit Patroni cluster (append-only)
- [ ] **D.DB.03** — 2-node aml_forensic Patroni cluster (separate VLAN, WORM)
- [ ] **D.DB.04** — pgBackRest: daily full backup to MinIO; WAL archive 5min
- [ ] **D.DB.05** — MinIO S3 Object Lock (Compliance mode) on forensic bucket
- [ ] **D.DB.06** — TimescaleDB extension installed (aml_analytics)
- [ ] **D.DB.07** — Apache AGE extension installed (aml_graph)
- [ ] **D.DB.08** — PgBouncer: connection pooling for all PG instances
- [ ] **D.DM.01** — Redpanda 3-broker cluster; 11 topics created
- [ ] **D.DM.02** — TLS + SASL/SCRAM auth for Kafka
- [ ] **D.DM.03** — Redis 2-node active-passive; TLS + AUTH
- [ ] **D.DM.04** — MinIO 4-node erasure coding; buckets: evidence, model-artifacts, backups, historical-exports
- [ ] **D.DM.05** — Temporal server 4-node with PostgreSQL persistence
- [ ] **D.IAM.01** — Keycloak 3-node; LDAP integration; RBAC roles: admin, compliance_manager, analyst, auditor, readonly
- [ ] **D.IAM.02** — OIDC flows: authorization_code (UI), client_credentials (M2M)

### 3.4.3 CI/CD

- [ ] **D.CI.01** — GitLab self-hosted; LDAP sync; SMTP
- [ ] **D.CI.02** — GitLab Runner (Kubernetes executor); autoscale to 10
- [ ] **D.CI.03** — GitLab Container Registry (MinIO backed)
- [ ] **D.CI.04** — ArgoCD: repos per env (dev/staging/prod); Kustomize overlays
- [ ] **D.CI.05** — Auto-sync 3min (dev); manual approval (staging+prod)
- [ ] **D.CI.06** — Python CI template: lint→type→test→scan→build→push→integrate→deploy
- [ ] **D.CI.07** — TypeScript CI template: lint→type→test→scan→build→push→deploy
- [ ] **D.CI.08** — Go CI template: lint→test→scan→build→push→deploy
- [ ] **D.CI.09** — Cosign image signing (HSM key)
- [ ] **D.CI.10** — Trivy CI: fail on CRITICAL/HIGH CVEs; weekly full registry scan
- [ ] **D.CI.11** — Bandit Python SAST in CI
- [ ] **D.CI.12** — Ephemeral test namespace per MR

### 3.4.4 Security

- [ ] **D.SE.01** — CIS Benchmark Ubuntu 24.04 (Level 1+2)
- [ ] **D.SE.02** — CIS Benchmark Kubernetes (kube-bench)
- [ ] **D.SE.03** — HSM: root CA, TLS intermediate, AES-256 encryption keys, RSA-4096 TRP signing keys
- [ ] **D.SE.04** — Linkerd service mesh: auto-inject; mTLS inter-service
- [ ] **D.SE.05** — mTLS certificate rotation (HSM-issued, 90d validity)
- [ ] **D.SE.06** — HashiCorp Vault 3-node HA (Raft + HSM unseal)
- [ ] **D.SE.07** — Vault dynamic secrets: PostgreSQL (16h TTL), Kafka (24h TTL)
- [ ] **D.SE.08** — Sealed Secrets for Git-encrypted K8s secrets
- [ ] **D.SE.09** — ModSecurity WAF: OWASP CRS + rate limiting (100 req/s/API key)
- [ ] **D.SE.10** — Trivy weekly vulnerability scan of running containers
- [ ] **D.SE.11** — K8s API audit logging; all SSH sessions recorded; Vault audit log
- [ ] **D.SE.12** — SBOM generation per CI build (Syft); archived in MinIO

### 3.4.5 Data Platform

- [ ] **D.DP.01** — Apache Airflow with Kubernetes executor; PostgreSQL backend
- [ ] **D.DP.02** — TimescaleDB hypertable: txn_metrics, alert_metrics, risk_score_history
- [ ] **D.DP.03** — Airflow DAG: ml_training_pipeline (weekly, Friday midnight)
- [ ] **D.DP.04** — Airflow DAG: forensic_witness_publisher (hourly)
- [ ] **D.DP.05** — Airflow DAG: data_quality_checks (daily)
- [ ] **D.DP.06** — Airflow DAG: customer_risk_reassessment (monthly)
- [ ] **D.DP.07** — Grafana dashboard for Airflow DAG metrics

---

# 4. Database Schemas

## 4.1 aml_core (Primary Operational Database)

### 4.1.1 Party Tables

```sql
-- Schema: aml_core

CREATE TABLE party (
    party_id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    party_type                  VARCHAR(20) NOT NULL CHECK (party_type IN ('INDIVIDUAL','CORPORATE','FI','TRUST')),
    full_name                   VARCHAR(255) NOT NULL,
    hkid_passport_no            VARCHAR(50),
    date_of_birth               DATE,
    nationality_code            CHAR(2),          -- ISO 3166-1
    country_of_residence        CHAR(2),          -- ISO 3166-1
    registered_address          TEXT,
    customer_risk_rating        VARCHAR(20) NOT NULL DEFAULT 'LOW' CHECK (customer_risk_rating IN ('LOW','MEDIUM','HIGH','PEP','SANCTIONED')),
    is_pep                      BOOLEAN DEFAULT FALSE,
    is_sanctioned               BOOLEAN DEFAULT FALSE,
    sanctions_list_ref          VARCHAR(100),
    is_beneficial_owner_identified BOOLEAN DEFAULT FALSE,
    onboarding_channel          VARCHAR(20) CHECK (onboarding_channel IN ('FACE_TO_FACE','REMOTE','iAM_SMART')),
    cdd_last_reviewed_at        TIMESTAMPTZ,
    edd_required_at             TIMESTAMPTZ,
    is_active                   BOOLEAN DEFAULT TRUE,
    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE party_document (
    doc_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    party_id        UUID NOT NULL REFERENCES party(party_id),
    doc_type        VARCHAR(10) NOT NULL CHECK (doc_type IN ('HKID','PASSPORT','BR','CI','POA')),
    doc_number      VARCHAR(100),
    expiry_date     DATE,
    issuing_country CHAR(2),
    is_verified     BOOLEAN DEFAULT FALSE,
    verified_at     TIMESTAMPTZ
);

CREATE TABLE party_wallet (
    wallet_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    party_id        UUID NOT NULL REFERENCES party(party_id),
    blockchain      VARCHAR(20) NOT NULL,  -- ethereum, polygon, solana, etc
    wallet_address  VARCHAR(255) NOT NULL,
    is_verified     BOOLEAN DEFAULT FALSE,
    verification_tx VARCHAR(255),  -- micro-transaction ref
    risk_score      INT,
    risk_score_updated_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(blockchain, wallet_address)
);
```

### 4.1.2 Transaction Tables

```sql
CREATE TABLE fiat_transaction (
    fiat_txn_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_ref        VARCHAR(255) NOT NULL,
    source_type         VARCHAR(20) NOT NULL CHECK (source_type IN ('SWIFT_MT103','SWIFT_MT202','ISO_20022_PACS008','ACH','FPS','INTERNAL')),
    sender_name         VARCHAR(255),
    sender_account      VARCHAR(100),
    sender_jurisdiction CHAR(2),
    beneficiary_name    VARCHAR(255),
    beneficiary_account VARCHAR(100),
    beneficiary_jurisdiction CHAR(2),
    amount              DECIMAL(24,8) NOT NULL,
    currency            CHAR(3) NOT NULL,
    txn_timestamp       TIMESTAMPTZ NOT NULL,
    raw_payload         JSONB,
    created_at          TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (txn_timestamp);

CREATE TABLE onchain_transaction (
    onchain_txn_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chain_id            INTEGER NOT NULL,
    tx_hash             VARCHAR(255) NOT NULL,
    block_number        BIGINT NOT NULL,
    from_address        VARCHAR(255) NOT NULL,
    to_address          VARCHAR(255) NOT NULL,
    token_address       VARCHAR(255) NOT NULL,
    token_symbol        VARCHAR(20),
    value_raw           NUMERIC(78,0) NOT NULL,
    value_decimal       DECIMAL(24,8),
    txn_timestamp       TIMESTAMPTZ NOT NULL,
    confirmation_blocks INTEGER DEFAULT 0,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(chain_id, tx_hash, from_address, to_address)
) PARTITION BY RANGE (txn_timestamp);

CREATE MATERIALIZED VIEW canonical_transaction AS
SELECT
    COALESCE(f.fiat_txn_id, o.onchain_txn_id) AS transaction_id,
    COALESCE(f.external_ref, o.tx_hash) AS external_ref,
    CASE WHEN f.fiat_txn_id IS NOT NULL THEN
        CASE f.source_type
            WHEN 'SWIFT_MT103' THEN 'FIAT_SWIFT'
            WHEN 'ISO_20022_PACS008' THEN 'FIAT_SWIFT'
            ELSE 'FIAT_ACH'
        END
    ELSE 'STABLECOIN_' || CASE o.chain_id
        WHEN 1 THEN 'EVM'
        WHEN 137 THEN 'EVM'
        WHEN 42161 THEN 'EVM'
        WHEN 10 THEN 'EVM'
        WHEN 8453 THEN 'EVM'
        ELSE 'SOL'
    END END AS source_type,
    o.chain_id,
    -- ... (full canonical mapping)
    NOW() AS ingestion_timestamp
FROM fiat_transaction f
FULL OUTER JOIN onchain_transaction o ON f.external_ref = o.tx_hash;
```

### 4.1.3 Alert & Case Tables

```sql
CREATE TABLE alert (
    alert_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id  UUID,
    customer_id     UUID,
    risk_score      INT NOT NULL,
    risk_tier       VARCHAR(20),
    triggered_rules JSONB NOT NULL,  -- [{rule_id, name, score, details}]
    status          VARCHAR(20) NOT NULL DEFAULT 'NEW' CHECK (status IN ('NEW','ASSIGNED','UNDER_INVESTIGATION','CLOSED_FALSE_POSITIVE','CLOSED_MONITORING','SAR_FILED')),
    assigned_to     UUID,  -- user_id
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE case_record (
    case_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id            UUID REFERENCES alert(alert_id),
    customer_id         UUID,
    priority            VARCHAR(10) NOT NULL DEFAULT 'MEDIUM' CHECK (priority IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    status              VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','UNDER_INVESTIGATION','PENDING_REVIEW','CLOSED')),
    assigned_to         UUID,
    investigation_notes TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    closed_at           TIMESTAMPTZ
);
```

### 4.1.4 Travel Rule Tables

```sql
CREATE TABLE travelrule_message (
    message_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id  UUID NOT NULL,
    counterparty_vasp VARCHAR(255),
    message_type    VARCHAR(20) CHECK (message_type IN ('SENT','RECEIVED')),
    payload         JSONB NOT NULL,
    status          VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING','DELIVERED','ACKNOWLEDGED','FAILED','TIMEOUT')),
    sent_at         TIMESTAMPTZ,
    responded_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

## 4.2 aml_audit (Append-Only Operational Audit)

```sql
CREATE TABLE audit_event (
    event_id        UUID PRIMARY KEY,
    event_type      VARCHAR(50) NOT NULL,
    service_name    VARCHAR(50) NOT NULL,
    payload         JSONB NOT NULL,
    prev_hash       VARCHAR(64),  -- SHA-256 of previous event
    record_hash     VARCHAR(64) NOT NULL,  -- SHA-256(this record)
    created_at      TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (created_at);

CREATE INDEX idx_audit_event_type ON audit_event(event_type);
CREATE INDEX idx_audit_created_at ON audit_event(created_at);
```

## 4.3 aml_forensic (WORM Tamper-Proof Ledger)

```sql
-- Schema: forensic

CREATE TABLE chain_head (
    sequence_id         BIGSERIAL PRIMARY KEY,
    chain_hash          VARCHAR(64) NOT NULL,
    record_table        VARCHAR(50) NOT NULL,
    record_hash         VARCHAR(64) NOT NULL,
    business_timestamp  TIMESTAMPTZ NOT NULL,
    witness_tx_id       VARCHAR(255)
);

CREATE TABLE alert_disposition (
    event_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id         UUID NOT NULL,
    disposition      VARCHAR(30) NOT NULL,
    justification    TEXT NOT NULL,
    operator_id      UUID NOT NULL,
    pre_state        JSONB,
    post_state       JSONB,
    prev_hash        VARCHAR(64),
    record_hash      VARCHAR(64) NOT NULL,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);
-- Similar for: case_transition, rule_change, risk_override, sar_lifecycle, access_log, merkle_root, external_witness
```

---

# 5. API Contracts

## 5.1 OpenAPI 3.1 — External AML Gateway

```yaml
openapi: 3.1.0
info:
  title: Project Overwatch AML Gateway API
  version: 1.0.0
  description: |
    AML transaction screening and compliance API for the Project Overwatch platform.
    Supports fiat and stablecoin transaction pre-settlement screening, wallet risk scoring,
    and forensic chain verification.

servers:
  - url: https://aml-gateway.overwatch.internal/v1

paths:
  /transactions/screen:
    post:
      summary: Screen a single transaction
      operationId: screenTransaction
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ScreenRequest'
      responses:
        '200':
          description: Screening decision
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ScreenResponse'

  /forensic/verify:
    get:
      summary: Verify forensic chain integrity
      operationId: verifyForensicChain
      responses:
        '200':
          description: Chain integrity status
          content:
            application/json:
              schema:
                type: object
                properties:
                  status: { type: string, enum: [PASS, FAIL] }
                  last_verified_at: { type: string, format: date-time }
                  records_checked: { type: integer }
                  integrity_pct: { type: number }

components:
  schemas:
    ScreenRequest:
      type: object
      required: [external_ref, source_type, amount, currency, txn_timestamp]
      properties:
        external_ref: { type: string, example: "SWIFT20260703AB12345" }
        source_type:
          type: string
          enum: [FIAT_SWIFT, FIAT_ACH, STABLECOIN_EVM, STABLECOIN_SOL]
        sender_name: { type: string }
        sender_wallet: { type: string }
        beneficiary_name: { type: string }
        beneficiary_wallet: { type: string }
        amount: { type: number, example: 15000.00 }
        currency: { type: string, example: "HKD" }
        txn_timestamp: { type: string, format: date-time }

    ScreenResponse:
      type: object
      properties:
        transaction_id: { type: string, format: uuid }
        decision: { type: string, enum: [APPROVE, HOLD, FLAG] }
        risk_score: { type: integer, minimum: 0, maximum: 100 }
        rule_triggers:
          type: array
          items:
            type: object
            properties:
              rule_id: { type: string }
              rule_name: { type: string }
              score: { type: integer }
        hold_reason: { type: string, nullable: true }
```

## 5.2 Internal Service API Endpoints

### Go → Python Boundary (blockchain-indexer → ingestion)

| Method | Path | Interface | SLA |
|--------|------|-----------|-----|
| Post | `onchain.raw` (Kafka) | `{chain_id, tx_hash, block, from, to, value, token, timestamp}` | <30s block→topic |

### Python → Python Boundaries

| From | To | Method | SLA |
|------|----|--------|-----|
| TME → Wallet Analytics | POST /score (REST) | <200ms p95 |
| TME → Sanctions | POST /screen (REST) | <100ms exact; <500ms fuzzy |
| TME → ML | POST /predict (REST) | <100ms |
| Gateway → Notabene | POST /api/v1/trp/send (REST) | <5min (incl. counterparty) |
| CMS → TME | POST /decide/hold (REST) | <200ms |
| Frontend → CMS | GET /alerts (REST) | <3s for 10K results |
| Frontend → Forensic | GET /forensic/verify (REST) | <5min (chain recompute) |

---

# 6. Kafka Event Map

## 6.1 Topic Registry

| Topic | Partitions | Retention | Cleanup Policy | Key | Schema ID | Producer | Consumers |
|-------|-----------|-----------|----------------|-----|-----------|----------|-----------|
| `fiat.raw` | 6 | 7d | delete | `external_ref` | 1 | ingestion-service | ingestion-(normaliser) |
| `onchain.raw` | 12 | 7d | delete | `chain_id+tx_hash` | 2 | blockchain-indexer | ingestion-(normaliser) |
| `fiat.normalised` | 6 | 30d | delete | `customer_id` | 3 | ingestion-service | tme-engine, audit-service |
| `onchain.normalised` | 12 | 30d | delete | `customer_id` | 3 | ingestion-service | tme-engine, audit-service |
| `screening.requests` | 6 | 7d | delete | — (round-robin) | 4 | tme-engine | sanctions-service |
| `screening.results` | 6 | 30d | delete | `transaction_ref` | 5 | sanctions-service, tme-engine | tme-engine, audit-service |
| `travelrule.requests` | 3 | 30d | delete | — (round-robin) | 6 | tme-engine | travelrule-gateway |
| `travelrule.results` | 3 | 90d | delete | `transaction_ref` | 7 | travelrule-gateway | tme-engine, audit-service |
| `alerts.generated` | 6 | 90d | delete | `customer_id` | 8 | tme-engine | case-management-service, audit-service |
| `audit.events` | 3 | ∞ | compact | `event_id` | 9 | ALL services | audit-service |
| `forensic.events` | 6 | ∞ | compact | `event_category` | 10 | CMS, Portal, TME, Reporting | forensic-audit-service |
| `batch.scan.commands` | 3 | 7d | delete | `run_id` | 11 | Airflow DAG | batch-scanning-service |
| `batch.scan.progress` | 3 | 7d | delete | `run_id` | 12 | batch-scanning-service | portal (dashboard) |
| `batch.alerts` | 6 | 90d | delete | `customer_id` | 13 | batch-scanning-service | case-management-service |
| `batch.results` | 6 | 365d | delete | `run_id` | 14 | batch-scanning-service | portal (dashboard), analytics |

## 6.2 Event Schemas

### 6.2.1 audit.events (Schema ID: 9)

```json
{
  "event_id": "uuid",
  "event_type": "TRANSACTION_SCREENED | RULE_CHANGED | USER_ACTION | SAR_FILED | ...",
  "service_name": "tme-engine | ingestion | sanctions | ...",
  "payload": {},  // type-specific payload
  "timestamp": "2026-07-03T10:30:01.123Z"
}
```

### 6.2.2 forensic.events (Schema ID: 10)

```json
{
  "event_category": "ALERT_DISPOSITION | CASE_TRANSITION | RULE_CHANGE | RISK_OVERRIDE | ACCESS_LOG | SAR_LIFECYCLE",
  "operator_id": "uuid (Keycloak user ID)",
  "session_id": "uuid",
  "client_ip": "10.0.1.50",
  "user_agent": "Mozilla/5.0...",
  "justification": "Customer provided source of funds documentation confirming wire transfer was for property sale proceeds.",
  "payload": {},  // category-specific payload with full before/after state
  "timestamp": "2026-07-03T10:30:01.123Z"
}
```

### 6.2.4 batch.alerts (Schema ID: 13)

```json
{
  "alert_id": "uuid",
  "run_id": "uuid",
  "transaction_id": "uuid",
  "analysis_types": ["BEHAVIORAL_DEVIATION", "PEER_GROUP_ANOMALY"],
  "batch_risk_score": 72,
  "priority": "MEDIUM",
  "alert_reason": "Customer daily volume 4.2σ above 90-day baseline",
  "customer_id": "cust-001",
  "scan_date": "2026-07-02",
  "created_at": "2026-07-03T03:15:00+08:00"
}
```

### 6.2.5 batch.results (Schema ID: 14)

```json
{
  "run_id": "uuid",
  "scan_date": "2026-07-02",
  "status": "COMPLETED",
  "txns_processed": 487231,
  "alerts_generated": 142,
  "analysis_breakdown": {
    "behavioral_deviation_flags": 89,
    "peer_group_anomalies": 34,
    "structuring_clusters": 8,
    "velocity_patterns": 23,
    "graph_anomalies": 12,
    "ml_high_risk_scores": 67,
    "rule_false_positives": 215,
    "layering_trails": 5,
    "sanctions_retrospective": 3,
    "sar_pre_populations": 18
  },
  "daily_briefing_path": "s3://daily-briefings/2026-07-02-daily-aml-briefing.pdf",
  "completed_at": "2026-07-03T05:47:00+08:00"
}
```

### 6.2.6 batch.scan.progress (Schema ID: 12)

```json
{
  "run_id": "uuid",
  "scan_date": "2026-07-02",
  "stage": "PARALLEL_ANALYSIS",
  "stage_index": 4,
  "total_stages": 8,
  "jobs_completed": 6,
  "jobs_total": 10,
  "txns_processed": 250000,
  "progress_pct": 62.5,
  "timestamp": "2026-07-03T03:45:00+08:00"
}
```

---

# 7. Infrastructure Configuration

## 7.1 Namespace Resource Quotas

| Namespace | CPU Request | Memory Request | Pod Limits (min/max) | Network Policy |
|-----------|-----------|---------------|----------------------|---------------|
| `ingestion` | 4 cores | 16 GB | 3/12 | Egress: kafka, redis; Ingress: api-gateway |
| `monitoring` | 8 cores | 32 GB | 3/16 | Egress: kafka, redis, analytics; Ingress: ingestion |
| `analytics` | 4 cores | 16 GB | 2/10 | Egress: kafka, redis, aml-core; Ingress: monitoring |
| `compliance` | 6 cores | 24 GB | 3/10 | Egress: kafka, aml-core, forensic; Ingress: portal |
| `forensic` | 2 cores | 8 GB | 2/4 | NO egress to internet; Ingress: compliance only |
| `portal` | 2 cores | 8 GB | 2/6 | Egress: compliance, audit; Ingress: keycloak, browser |
| `batch` | 16 cores (elastic) | 64 GB (elastic) | 0/20 | Egress: kafka, minio, aml-core, aml-analytics; Ingress: compliance only |
| `audit` | 2 cores | 8 GB | 2/4 | Egress: kafka, aml-audit |
| `infra` | 12 cores | 48 GB | Dedicated | Stateful services; limited egress |

## 7.2 Environment Configuration (dev → staging → prod)

| Config | dev | staging | prod |
|--------|-----|---------|------|
| Nodes | 3 (1 CP + 2 workers) | 6 (3+3) | 9 (3+6) |
| PG replicas | 1 | 2 | 3+2 |
| Kafka brokers | 1 | 3 | 3 |
| ArgoCD sync | Auto (3min) | Auto (5min) | Manual approval |
| Logging | Debug | Info | Warn+ |
| Monitoring | Prom + Grafana | Full stack | Full stack + PagerDuty |
| Access | Dev team + CI | Dev + QA teams | Read-only for all except SRE |

---

# 8. CI/CD Pipeline

## 8.1 Python Service Pipeline

```yaml
# .gitlab-ci.yml (Python template)
variables:
  PYTHON_VERSION: "3.12"
  BASE_IMAGE: "python:3.12-slim"

stages:
  - lint
  - typecheck
  - test
  - security
  - build
  - push
  - integrate
  - deploy

ruff:
  stage: lint
  script: ruff check src/ tests/

mypy:
  stage: typecheck
  script: mypy src/ --strict

pytest:
  stage: test
  script: pytest --cov=src --cov-fail-under=85 --junitxml=report.xml
  coverage: '/TOTAL.*\s+(\d+%)$/'

bandit:
  stage: security
  script: bandit -r src/ -x tests/

trivy:
  stage: security
  script: trivy image --severity CRITICAL,HIGH $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

docker-build:
  stage: build
  script: docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
  only: [main, develop]

cosign-sign:
  stage: push
  script: cosign sign --key hsm:// $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

argo-sync:
  stage: deploy
  script: argocd app sync $CI_PROJECT_NAME-$CI_ENVIRONMENT_NAME
  environment: { name: $CI_ENVIRONMENT_NAME }
```

## 8.2 Go Service Pipeline

```yaml
golangci-lint:
  stage: lint
  script: golangci-lint run ./...

go-test:
  stage: test
  script: go test -race -coverprofile=coverage.out ./...
  coverage: '/coverage: \d+\.\d+% of statements/'

trivy:
  stage: security
  script: trivy image --severity CRITICAL,HIGH $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

docker-build:
  stage: build
  script: |
    CGO_ENABLED=0 GOOS=linux go build -o bin/indexer ./cmd/indexer
    docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
```

---

# 9. Monitoring & Observability

## 9.1 Prometheus Metrics (All Services)

```yaml
# Convention: overwatch_<service>_<metric_name>
# Labels: service, version, environment
rules:
  - alert: HighErrorRate
    expr: rate(overwatch_requests_total{status=~"5.."}[5m]) > 0.01
    for: 5m
    labels: { severity: critical }
    annotations: { summary: "High error rate on {{ $labels.service }}" }

  - alert: AuditChainBreak
    expr: overwatch_audit_chain_integrity == 0
    for: 0m
    labels: { severity: critical }
    annotations: { summary: "AUDIT CHAIN INTEGRITY BREACH DETECTED" }

  - alert: ForensicChainBreak
    expr: overwatch_forensic_chain_integrity == 0
    for: 0m
    labels: { severity: critical }
    annotations: { summary: "FORENSIC CHAIN INTEGRITY BREACH — P0" }

  - alert: TMEHighDecisionLatency
    expr: histogram_quantile(0.95, rate(overwatch_tme_decision_duration_seconds_bucket[5m])) > 0.5
    for: 5m
    labels: { severity: warning }
    annotations: { summary: "TME p95 latency > 500ms" }
```

## 9.2 Grafana Dashboards

| Dashboard | Source | Purpose |
|-----------|--------|---------|
| Cluster Overview | Prometheus + KSM | Node health, pod status, resource usage |
| Service Health | Prometheus | Per-service: request rate, error rate, latency, uptime |
| AML Metrics | Custom exporters | Alert volume, decision distribution, rule trigger count, false positive rate |
| Forensic Integrity | forensic-audit-service | Chain head age, last verified, integrity status, witness publication age |
| Kafka Monitoring | JMX exporter | Consumer lag, throughput, partition distribution |
| Temporal | Temporal metrics | Workflow duration, success/fail rate, queue depth |
| Airflow | Airflow exporter | DAG duration, task success/fail, SLA misses |

---

# 10. Testing Requirements

## 10.1 Test Coverage Targets

| Layer | Tool | Coverage Target | Run Frequency |
|-------|------|----------------|--------------|
| Unit (Python) | pytest + pytest-cov | >=85% line coverage | Every commit |
| Unit (Go) | go test -cover | >=80% statement coverage | Every commit |
| Unit (TypeScript) | vitest | >=80% line coverage | Every commit |
| Integration | pytest + testcontainers | All critical paths | Every MR |
| Contract | Pact (CDC) | All producer-consumer boundaries | Every MR |
| E2E | Custom harness + k6 | Top 20 transaction scenarios | Nightly + pre-release |
| Regulatory | Curated HKMA/FATF scenarios | 8 documented scenarios | Pre-release + quarterly |
| Forensic Integrity | forensic-verifier CLI | Tamper simulation (detect single-bit change) | Pre-release + weekly auto |
| Load | k6 + custom Kafka loadgen | 500 TPS sustained, p95<500ms | Pre-release + quarterly |
| Chaos | Chaos Mesh / Litmus | Single-node failure, network partition, Kafka broker loss | Monthly |
| Security | Bandit, Trivy, Semgrep, ZAP | Zero CRITICAL/HIGH CVEs | Every commit + weekly |

## 10.2 Regulatory Test Scenarios

| ID | Scenario | Steps | Expected Outcome |
|----|----------|-------|-----------------|
| R1 | Structuring | Submit 10 stablecoin txns of HKD 7,900 each to different addresses in 30 min | Alert generated; structuring rule triggered |
| R2 | Cross-rail layering | Fiat deposit (HKD 1M) → buy USDC → transfer to unhosted wallet → sell for fiat at secondary platform | Cross-rail alert; enhanced monitoring triggered |
| R3 | Sanctions hit | Beneficiary wallet = OFAC SDN address | Transaction BLOCKED; mandatory reporting flag set |
| R4 | Travel Rule threshold | USDC transfer HKD 10,000 to VASP | TRP message sent; beneficiary data returned; APPROVED |
| R5 | Unhosted wallet | USDC >HKD 100,000 to self-custodied wallet | HOLD decision; EDD case created; assigned to senior analyst |
| R6 | PEP transaction | PEP-tagged customer sends HKD 500,000 offshore | FLAG; EDD triggered; case assigned to senior analyst |
| R7 | Velocity breach | 50 txns to 50 addresses in 1 hour | Alert; account HOLD; freeze initiated |
| R8 | Forensic tamper | Attempt direct UPDATE on ForensicDB | Trigger blocks write; tamper alert P0; hash chain break detected |

---

# 11. Task Assignment Matrix

## 11.1 Squad A — Core Platform (5-6 engineers)

| Engineer | Primary Focus | Tasks |
|----------|-------------|-------|
| BE Python 1 | ingestion-service | A.IN.01-10, A.IN.13-14 |
| BE Python 2 | tme-engine core | A.TM.01-10 |
| BE Python 3 | Rule library + testing | A.TM.15-23 |
| BE Python 4 | tme-ml + sanctions | A.ML.01-07, A.SC.01-10 |
| DE | audit + kafka infra | A.AU.01-05, A.IN.20, B.5 (shared with D) |

**Dependency:** Requires Squad D to provision K8s + Kafka + aml_core DB (Week 0-4)

## 11.2 Squad B — Blockchain & Analytics (4-5 engineers)

| Engineer | Primary Focus | Tasks |
|----------|-------------|-------|
| Go BE 1 | Indexer foundation + Ethereum | B.BC.01-06 |
| Go BE 2 | Polygon + Arbitrum + Optimism | B.BC.07-09 |
| Go BE 3 | Base + Solana + backfill | B.BC.10-16 |
| BE Python | Wallet analytics adapter | B.WA.01-12 |
| BE Python | Risk scoring service | B.RS.01-09 |

**Dependency:** Requires Kafka topics + MinIO (Squad D)

## 11.3 Squad C — Compliance UX (5-6 engineers)

| Engineer | Primary Focus | Tasks |
|----------|-------------|-------|
| BE Python 1 | travelrule-gateway | C.TR.01-11 |
| BE Python 2 | case-management (API + workflows) | C.CM.01-14 |
| BE Python 3 | case-management (evidence + SAR) + regulatory-reporting | C.CM.15-21, C.RR.01-12 |
| BE Python 4 | forensic-audit-service (full) | C.FA.01-17 |
| FE TypeScript 1 | Portal foundation + dashboard + alert queue | C.PO.01-21 |
| FE TypeScript 2 | Case workspace + config + reporting | C.PO.22-38 |

**Dependency:** Requires TME (Squad A) alerts.generated topic; requires Notabene API key

## 11.4 Squad D — Platform & Infra (4-5 engineers)

| Engineer | Primary Focus | Tasks |
|----------|-------------|-------|
| DevOps 1 | K8s cluster + networking | D.K8.01-13 |
| DevOps 2 | Stateful services (PG, Kafka, Redis, MinIO, Temporal) | D.DB.01-08, D.DM.01-05 |
| DevOps 3 | CI/CD + GitOps | D.CI.01-12 |
| Security | HSM, Vault, mTLS, WAF, CIS | D.SE.01-12 |
| DE | Airflow + TimescaleDB + ML pipeline | D.DP.01-07 |

**Dependency:** Requires hardware (servers ordered week -4), data centre colocation

---

# 12. Development Timeline & Dependencies

## 12.1 Phase Map by Week

| Week | Squad A | Squad B | Squad C | Squad D |
|------|---------|---------|---------|---------|
| 0-4 | — | — | — | Provision K8s + stateful services + CI/CD + security (D.K8→D.CI→D.SE) |
| 4-6 | ingestion scaffold + tme-engine core (A.IN→A.TM) | — | — | Keycloak + Vault + monitoring (D.DM→D.IAM) |
| 6-8 | ingestion complete + sanctions start | blockchain-indexer scaffold (B.BC.01-05) | — | Airflow + TimescaleDB (D.DP) |
| 8-10 | tme-engine complete + rule library | indexer EVM chains (B.BC.06-10) + wallet analytics start | — | Prod environment hardening |
| 10-14 | tme-ml + rule library complete | All 6 chains + wallet analytics complete | — | Load testing + Chaos |
| 14-18 | Sanctions complete + audit complete | Risk scoring complete | — | Security audit |
| 18-22 | — | — | travelrule-gateway + CMS start | Penetration test |
| 22-28 | — | — | CMS complete + portal start | Remediation |
| 28-34 | — | — | forensic-audit + portal complete + regulatory reporting | Regulatory doc pack |
| 34-40 | TME shadow ML → production | Additional chains (Tron) | Forensic witness publish live | Production launch prep |
| 40-52 | False positive reduction + optimisation | — | — | 30-day hypercare |

## 12.2 Critical Path (Blocks Downstream)

```
Sprint 0 (D)
  ↓
Data Layer (D)
  ↓
            ┌─────────┐        ┌─────────────────────┐
            │ Squad A │        │     Squad B         │
            │ (TME)   │        │ (Blockchain)        │
            └────┬────┘        └──────────┬──────────┘
                 │                        │
                 ▼                        ▼
            ┌────────────────────────────────────┐
            │          Squad C                   │
            │  (Compliance workflows + Portal)   │
            └────────────────────────────────────┘
```

**Blocking paths:**
- `D.K8 + D.DB → A.IN + A.TM → C.CM + C.TR` (critical path)
- `D.K8 + D.DM → B.BC` (parallel — blockchain does not block on TME)
- `A.TM → C.TR` (Travel Rule needs TME to detect threshold)
- `C.CM → C.PO` (frontend needs CMS API)

---

# 13. Appendices

## 13.1 Environment Variables Template

```bash
# Per-service environment variables (managed via Vault)

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka-0.infra:9092,kafka-1.infra:9092,kafka-2.infra:9092
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_USERNAME=service_account_name

# PostgreSQL
PG_HOST=pg-aml-core-rw.infra
PG_PORT=5432
PG_DATABASE=aml_core
PG_USER=${VAULT:secret/path/to/db/creds:username}
PG_PASSWORD=${VAULT:secret/path/to/db/creds:password}

# Redis
REDIS_HOST=redis.infra
REDIS_PORT=6379
REDIS_AUTH=${VAULT:secret/path/to/redis:auth}

# MinIO
MINIO_ENDPOINT=minio.infra:9000
MINIO_ACCESS_KEY=${VAULT:secret/path/to/minio:access_key}
MINIO_SECRET_KEY=${VAULT:secret/path/to/minio:secret_key}

# Vendors
TRM_API_KEY=${VAULT:secret/path/to/trm:api_key}
CHAINALYSIS_API_KEY=${VAULT:secret/path/to/chainalysis:api_key}
NOTABENE_API_KEY=${VAULT:secret/path/to/notabene:api_key}
NOTABENE_ORG_ID=overwatch-hk

# Keycloak
KEYCLOAK_URL=https://keycloak.infra
KEYCLOAK_REALM=project-overwatch
KEYCLOAK_CLIENT_ID=aml-api
KEYCLOAK_CLIENT_SECRET=${VAULT:secret/path/to/keycloak:client_secret}
```

## 13.2 Dockerfile Standards

```dockerfile
# Python service (distroless)
FROM python:3.12-slim AS builder
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

FROM gcr.io/distroless/python3-debian12:nonroot
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY src/ /app/src/
WORKDIR /app
USER nonroot:nonroot
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

```dockerfile
# Go service (distroless)
FROM golang:1.22-alpine AS builder
COPY . /app
WORKDIR /app
RUN CGO_ENABLED=0 GOOS=linux go build -o /app/indexer ./cmd/indexer

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=builder /app/indexer /indexer
USER nonroot:nonroot
CMD ["/indexer"]
```

## 13.3 Decision Matrix Reference

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Rule Engine | YAML DSL + sandboxed Python | Compliance team can author/modify rules without deployment; sandbox prevents malicious expressions |
| Performance | In-memory sliding window | Velocity rules need O(1) lookup of recent txns per customer; Redis too slow for sub-ms window checks |
| ML Framework | ONNX Runtime | Language-agnostic inference; hot-swap models; GPU-capable when needed |
| Wallet Analytics | Abstracted adapter | Vendor lock-in avoidance; TRM Labs primary, Chainalysis fallback; config-only switch |
| Workflow Engine | Temporal | Durable execution with retry/compensation for Travel Rule handshakes; state machine enforcement for CMS |
| Kafka Cleanup | Compact for audit/forensic | Permanent retention required by AMLO (7 years); compact policy retains latest state |
| Forensic DB Isolation | Separate VLAN + WORM | Regulator/auditor must have independent verifiability even if operational infrastructure is compromised |
| External Witness | Polygon testnet + S3 Object Lock | Cost-effective (testnet = free); regulatory comfort from blockchain-anchored attestation |
