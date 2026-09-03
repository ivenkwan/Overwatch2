# Project Overwatch — Agent Squad Specifications

> **Data Model Reference:** The converged AML Data Model (27 entities across 6 domains: Party & KYC, Account, Transaction & Screening, AML Operations, Graph & Analytics, Batch & Governance) is the authoritative data architecture for all squads. See Build Specification Section 4 for the complete entity reference and relationship diagram.

## Squad Overview & Assignment Matrix

| Squad | Nickname | Primary Build Streams | Language | Key Services | Size |
|-------|----------|----------------------|----------|-------------|------|
| **Squad A** | Core Platform | B, C, D | Python | ingestion, tme-engine, tme-ml, sanctions, risk-scoring, audit | 5-6 |
| **Squad B** | Blockchain & Analytics | E, D | Go, Python | blockchain-indexer, wallet-analytics-adapter, risk-scoring, graph-analytics | 4-5 |
| **Squad C** | Compliance UX | F, G, I | Python, TypeScript | travelrule-gateway, case-management, regulatory-reporting, forensic-audit, batch-scanning-service, aml-portal | 5-6 |
| **Squad D** | Platform & Infra | A, H, B | Python, Shell, IaC | K8s, PostgreSQL, Kafka, MinIO, ArgoCD, GitLab, Keycloak, Vault, Airflow, TimescaleDB | 4-5 |

---

# Squad A — Core Platform

**Motto:** *"Rule the engine. Every transaction, every decision."*

**Squad A builds the transaction processing backbone — the ingestion pipeline, the monitoring engine that makes all screening decisions, and the audit trail that records every system-level event. Every other squad depends on Squad A's services.**

---

## A.1 Mission & Ownership

| Boundary | Owns | Consumes From | Produces For |
|----------|------|---------------|-------------|
| **Ingestion** | ingesting fiat + on-chain transactions, normalising to canonical schema, publishing to Kafka | Payment platform API, blockchain indexer (Squad B) | TME, sanctions (all squads) |
| **Decision Engine** | tme-engine — rule evaluation, composite scoring, hold/release decisions | ingestion, sanctions (Squad A), risk scoring (Squad B), wallet analytics (Squad B) | Payment platform (API response), CMS (Squad C) |
| **ML Inference** | tme-ml — ONNX runtime, feature pipeline, SHAP explanation generation | TME, training pipeline (Airflow) | tme-engine |
| **Operational Audit** | audit-service — system-level event capture, hash-chain, hourly integrity checker | Every service via audit.events topic | Regulators, internal audit |
| **Canonical Schema** | Schema definition, versioning, validation rules | N/A (design authority) | All services writing/reading transactions |

## A.2 Services — Detailed Specifications

### A.2.1 ingestion-service

| Attribute | Value |
|-----------|-------|
| Language | Python 3.12+ |
| Framework | FastAPI |
| Kafka Client | aiokafka (async producer) |
| Repo structure | `services/ingestion/` |

**Key contract — Fiat API (synchronous, external-facing):**

```
POST /api/v1/transactions/fiat
Content-Type: application/json

Request:
{
  "external_ref": "SWIFT20260703AB12345",
  "source_type": "FIAT_SWIFT",
  "sender_name": "John Smith",
  "sender_account": "HK123456789012",
  "sender_jurisdiction": "HK",
  "beneficiary_name": "Acme Corp",
  "beneficiary_account": "SG987654321098",
  "beneficiary_jurisdiction": "SG",
  "amount": 15000.00,
  "currency": "HKD",
  "txn_timestamp": "2026-07-03T10:30:00+08:00"
}

Response (synchronous, after TME decision):
{
  "transaction_id": "01J12345-...",
  "decision": "APPROVE" | "HOLD" | "FLAG",
  "risk_score": 25,
  "rule_triggers": [],
  "hold_reason": null | string
}
```

**Key contract — Kafka output (async):**

```
Topic: fiat.normalised (keyed by customer_id)
{
  "transaction_id": "01J12345-...",
  "source_type": "FIAT_SWIFT",
  // ... full canonical schema (20 fields)
  "ingestion_timestamp": "2026-07-03T10:30:01.123+08:00"
}
```

**Tasks:**
- [ ] **A.IN.01** — FastAPI application scaffold with health check endpoint
- [ ] **A.IN.02** — POST /api/v1/transactions/fiat endpoint (validate, normalise, publish to fiat.raw)
- [ ] **A.IN.03** — Batch file import module (SFTP poller for SWIFT MT/ISO 20022 files)
- [ ] **A.IN.04** — Kafka producer publishing to fiat.raw topic
- [ ] **A.IN.05** — Fiat normaliser (SWIFT MT/ISO 20022 → canonical schema)
- [ ] **A.IN.06** — On-chain normaliser (Transfer event log → canonical schema)
- [ ] **A.IN.07** — POST /api/v1/transactions/batch-screen (async batch; returns batch_id)
- [ ] **A.IN.08** — GET /api/v1/transactions/batch/{id}/status (poll batch result)
- [ ] **A.IN.09** — POST /api/v1/wallets/screen (wallet risk scoring — proxy to Squad B adapter)
- [ ] **A.IN.10** — GET /api/v1/transactions/{ref} (retrieve screening detail)
- [ ] **A.IN.11** — GET /api/v1/health (health check with dependency status)
- [ ] **A.IN.12** — GET /api/v1/forensic/verify (public chain verification)
- [ ] **A.IN.13** — Schema validation with detailed error messages (Pydantic)
- [ ] **A.IN.14** — FX conversion service (non-USD to USD equivalent)
- [ ] **A.IN.15** — OpenAPI 3.1 spec generation; Swagger UI hosting
- [ ] **A.IN.16** — Rate limiting (100 req/s per API key)
- [ ] **A.IN.17** — mTLS configuration for all external API calls
- [ ] **A.IN.18** — Audit event publishing to audit.events topic for each request
- [ ] **A.IN.19** — Forensic event publishing to forensic.events for any manual override
- [ ] **A.IN.20** — Publish normalised transactions to fiat.normalised / onchain.normalised topics

**Acceptance criteria:**
- ✅ 100 fiat txns/sec processed; p95 <200ms for synchronous endpoint
- ✅ Fiat wire + stablecoin transfer normalised to identical canonical schema
- ✅ Batch of 10K txns completes <30s
- ✅ All audit events published correctly
- ✅ Schema validation rejects malformed events with descriptive error

### A.2.2 tme-engine — Rule Processing Core

| Attribute | Value |
|-----------|-------|
| Language | Python 3.12+ |
| Frameworks | FastAPI (workers), aiokafka (consumer) |
| State | In-memory sliding window (customer_id keyed) |
| Persistence | PostgreSQL for rule definitions |
| Repo | `services/tme-engine/` |

**Rule definition schema (YAML DSL):**
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
```

**Tasks:**
- [ ] **A.TM.01** — Kafka consumer for fiat.normalised and onchain.normalised topics
- [ ] **A.TM.02** — In-memory sliding window per customer_id for velocity counting (5min, 1hr, 24hr windows)
- [ ] **A.TM.03** — YAML rule definition schema and parser with validation
- [ ] **A.TM.04** — Sandboxed Python expression engine for rule conditions
- [ ] **A.TM.05** — Rule versioning: snapshots in PostgreSQL; hot-reload endpoint (POST /config/rules/reload)
- [ ] **A.TM.06** — Tier gate logic: LOW gets subset, HIGH gets all rules
- [ ] **A.TM.07** — Parallel rule evaluation (asyncio.gather for all enabled rules)
- [ ] **A.TM.08** — Composite score calculator (weighted: deterministic score + ML score)
- [ ] **A.TM.09** — Decision mapper: 0-30 APPROVE, 31-65 FLAG, 66-100 BLOCK
- [ ] **A.TM.10** — Publish decisions to screening.results; if flagged, publish to alerts.generated
- [ ] **A.TM.11** — POST /decide (sync endpoint, for fiat pre-settlement)
- [ ] **A.TM.12** — POST /decide/batch (async for batch screening)
- [ ] **A.TM.13** — Prometheus metrics: rules evaluated/sec, decision breakdown, latency histograms
- [ ] **A.TM.14** — Audit logging of every decision to audit.events
- [ ] **A.TM.15** — Happy path: [C.2.1] Velocity rule: >5 to same address in 1hr
- [ ] **A.TM.16** — Happy path: [C.2.2] Velocity rule: >HKD 500K cumulative daily
- [ ] **A.TM.17** — Happy path: [C.2.3] Threshold: >HKD 1M single transfer
- [ ] **A.TM.18** — Happy path: [C.2.4] Threshold: >500K USDC single transfer
- [ ] **A.TM.19** — Happy path: [C.2.5] Counterparty: high-risk jurisdiction
- [ ] **A.TM.20** — Happy path: [C.2.6] Counterparty: unhosted wallet above threshold
- [ ] **A.TM.21** — Happy path: [C.2.7] Pattern: round-dollar amounts in stablecoins
- [ ] **A.TM.22** — Happy path: [C.2.8] Pattern: structuring < HKD 8,000
- [ ] **A.TM.23** — Happy path: [C.2.9] Geographic: IP/session origin mismatch

**Acceptance criteria:**
- ✅ 100 fiat txns/sec through full pipeline; p95 <500ms
- ✅ Rule changes hot-reloaded without restart (<10s propagation)
- ✅ All 9 rules tested with known input/output pairs
- ✅ Composite score correctly weights ML score when available

### A.2.3 tme-ml — ML Inference Service

| Attribute | Value |
|-----------|-------|
| Language | Python 3.12+ |
| Runtime | ONNX (onnxruntime) |
| Model | XGBoost classifier |
| Explanations | SHAP |
| Repo | `services/tme-ml/` |

**Tasks:**
- [ ] **A.ML.01** — ONNX runtime inference server scaffold (FastAPI)
- [ ] **A.ML.02** — Feature engineering pipeline: log(amount), freq (hr/day/week), z-score baseline, wallet risk, counterparty risk, jurisdiction risk, time-of-day, day-of-week
- [ ] **A.ML.03** — Initial XGBoost model training on synthetic labelled data (or industry benchmark data)
- [ ] **A.ML.04** — SHAP explanation value generation per prediction
- [ ] **A.ML.05** — Shadow-mode output: score + SHAP logged alongside TME decision; not used for decision
- [ ] **A.ML.06** — Versioned model artifacts stored on MinIO
- [ ] **A.ML.07** — Model loading pipeline: loads latest approved model on start; hot-swap via API
- [ ] **A.ML.08** — ML feature store reads from aml_analytics (TimescaleDB)
- [ ] **A.ML.09** — Prometheus metrics: inference latency, feature distribution drift, model version
- **Acceptance:**
- ✅ Probability [0,1] + SHAP values returned in <100ms
- ✅ Shadow-mode logs predictions without influencing decisions
- ✅ Model hot-swap without service restart

### A.2.4 sanctions-service

*See Squad A shared scope — built jointly, owned by Squad A for operations*

| Attribute | Value |
|-----------|-------|
| Language | Python 3.12+ |
| Frameworks | FastAPI (sync + batch), aiokafka, rapidfuzz |
| In-memory | Hash map for wallet exact-match (<1ms), list index for fuzzy search |
| Repo | `services/sanctions-service/` |

**Tasks:**
- [ ] **A.SC.01** — POST /screen (name + address text matching) synchronous endpoint
- [ ] **A.SC.02** — POST /screen/wallet (wallet hash exact-match) synchronous endpoint
- [ ] **A.SC.03** — Fuzzy name matching: Levenshtein, token-set ratio, Soundex (rapidfuzz)
- [ ] **A.SC.04** — OFAC SDN in-memory hash map loader (wallet addresses)
- [ ] **A.SC.05** — Batch Kafka consumer for screening.requests topic
- [ ] **A.SC.06** — Daily SFTP pull from sanctions provider; diff detection
- [ ] **A.SC.07** — Confidence scoring: 0-100; >=80 = block; 60-79 = review
- [ ] **A.SC.08** — Batch re-screening trigger: all parties within 24h of list update
- [ ] **A.SC.09** — Publish screening results to screening.results topic
- [ ] **A.SC.10** — Sanctions list update audit logging to forensic.events
- **Acceptance:**
- ✅ OFAC SDN 100K+ entries loaded; exact wallet match <1ms
- ✅ Fuzzy "John Smith" vs "Jon Smith" = match >80%
- ✅ Batch re-screening of 10K records <5 min
- ✅ Daily pull + diff detection functional

### A.2.5 audit-service

| Attribute | Value |
|-----------|-------|
| Language | Python 3.12+ |
| Kafka | aiokafka (idempotent consumer) |
| DB | aml_audit PostgreSQL (append-only, time-partitioned) |
| Repo | `services/audit-service/` |

**Tasks:**
- [ ] **A.AU.01** — Kafka consumer for audit.events topic (idempotent)
- [ ] **A.AU.02** — Insert into aml_audit.audit_event with hash-chain: SHA-256(prev_hash + payload)
- [ ] **A.AU.03** — Hash-chain integrity checker (hourly, checks all entries since last checkpoint)
- [ ] **A.AU.04** — Read-only REST API for audit log queries (GET /audit/events, GET /audit/chain/head)
- [ ] **A.AU.05** — Prometheus metric: hash-chain integrity status (0=clean, 1=tampered)
- **Acceptance:**
- ✅ 10K events ingested/min; hash chain consistent
- ✅ Integrity checker detects any modified record and reports P0
- ✅ Audit DB cannot be written to by UPDATE/DELETE (enforced at DB role level)

---

# Squad B — Blockchain & Analytics

**Motto:** *"Trace every token, score every wallet."*

**Squad B builds the blockchain-facing side of the platform — indexing on-chain stablecoin transfers across 6 chains, connecting to analytics vendors for wallet risk scoring, and maintaining the customer risk scoring model.**

---

## B.1 Mission & Ownership

| Boundary | Owns | Consumes From | Produces For |
|----------|------|---------------|-------------|
| **Blockchain Indexing** | Reading Transfer events from AnchorPoint + USDC contracts across EVM chains + Solana; writing stablecoin_txn_detail records; populating graph_node/graph_edge materialised views | Blockchain nodes (RPC) | ingestion (Squad A), wallet analytics |
| **Wallet Analytics** | Vendor-agnostic adapter for TRM/Chainalysis/Elliptic, caching, circuit breaking; populates stablecoin_txn_detail.ba_risk_score and account.account_risk_rating | blockchain-indexer, vendor APIs | sanctions (Squad A), risk scoring |
| **Risk Scoring** | Customer-level risk scoring, tier management, factor-weighted scoring; writes to party.customer_risk_rating and account.account_risk_rating | TME (Squad A), sanctions (Squad A), wallet analytics | TME (Squad A), CMS (Squad C) |
| **Graph Analytics** | Managing graph_node, graph_edge, graph_community materialisation; running batch graph algorithms (PageRank, Louvain, cycle detection); interactive graph exploration for analysts | blockchain-indexer, ingestion (Squad A) | T+1 batch scanner (Squad C), CMS (Squad C) |

## B.2 Services — Detailed Specifications

### B.2.1 blockchain-indexer (Go)

| Attribute | Value |
|-----------|-------|
| Language | Go 1.22+ |
| Key deps | go-ethereum, solana-go, sarama (Kafka producer) |
| Pattern | Per-chain goroutine pool with independent state |
| Repo | `services/blockchain-indexer/` |

**Key contract — Kafka output:**
```
Topic: onchain.raw (keyed by chain_id + tx_hash)
{
  "chain_id": 1,
  "tx_hash": "0xabcdef...",
  "block_number": 21500123,
  "from_address": "0x1234...",
  "to_address": "0x5678...",
  "value": "15000000000",          // raw uint256 (18 decimals)
  "value_decimal": "15000.00",     // human-readable
  "token_address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  // USDC
  "token_symbol": "USDC",
  "timestamp": 1800000000,
  "finality_blocks": 12
}
```

**Tasks:**

**Foundation:**
- [ ] **B.BC.01** — Go project scaffolding with per-chain goroutine worker pattern, graceful shutdown, state persistence
- [ ] **B.BC.02** — Kafka producer client (sarama) with onchain.raw topic integration
- [ ] **B.BC.03** — Shared chain worker library: configurable RPC endpoint, polling interval, confirmation depth, token contract filter, retry with backoff
- [ ] **B.BC.04** — Health monitoring framework: per-chain worker health endpoint, auto-restart on disconnect, Prometheus metrics (blocks behind head, txns indexed/sec, RPC errors)

**Per-chain workers (each follows same pattern — parallelisable across the team):**
- [ ] **B.BC.05** — EVM base worker: Transfer event polling — fromBlock, toBlock, filter by contract address, decode event log, resolve sender/recipient
- [ ] **B.BC.06** — Ethereum mainnet worker (chain_id: 1) — archive node connection, 12-block confirmation depth
- [ ] **B.BC.07** — Polygon PoS worker (chain_id: 137) — full RPC node, checkpoint-based finality
- [ ] **B.BC.08** — Arbitrum One worker (chain_id: 42161) — RPC connection, L1-to-L2 finality awareness
- [ ] **B.BC.09** — Optimism worker (chain_id: 10) — RPC connection, batch inbox monitoring
- [ ] **B.BC.10** — Base worker (chain_id: 8453) — RPC connection
- [ ] **B.BC.11** — Solana worker — geyser plugin or RPC streaming for SPL token Transfer events (AnchorPoint + USDC)

**Capabilities:**
- [ ] **B.BC.12** — Programmable event filter: configurable contract addresses via ConfigMap, wallet-specific monitoring
- [ ] **B.BC.13** — Backfill support: re-index from configurable historical block height; batch writes to Kafka at 10K events/batch
- [ ] **B.BC.14** — Graceful shutdown: persist last indexed block per chain to PostgreSQL; resume on restart
- [ ] **B.BC.15** — On-chain enrichment: calls wallet analytics service for address risk score (cached); enriches event before publishing
- [ ] **B.BC.16** — Per-chain lag alert: if block head age >60s, publish alert to monitoring

**Acceptance criteria:**
- ✅ All 6 chains indexing within 30s of block finality
- ✅ Backfill 1M blocks from historical height — completes <2 hours per chain
- ✅ Single chain RPC failure does not affect other chains
- ✅ After restart, resumes from last persisted block (no double-publish)

### B.2.2 wallet-analytics-adapter

| Attribute | Value |
|-----------|-------|
| Language | Python 3.12+ |
| Frameworks | FastAPI, httpx (async), Redis (asyncio) |
| Pattern | Abstracted vendor adapters with circuit breaker |
| Repo | `services/wallet-analytics-adapter/` |

**Key contract — common output schema:**
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
  "top_interactions": [
    {"address": "0x...", "volume_usd": 5000000, "count": 120, "entity": "Binance"}
  ],
  "last_updated": "2026-07-03T12:00:00Z",
  "vendor": "TRM_LABS"
}
```

**Tasks:**
- [ ] **B.WA.01** — Vendor adapter interface definition (abstract base class): `async def score(addresses: list[str]) -> list[WalletScore]`
- [ ] **B.WA.02** — TRM Labs adapter implementation (primary vendor)
- [ ] **B.WA.03** — Chainalysis KYT adapter implementation (fallback vendor)
- [ ] **B.WA.04** — POST /score endpoint: accepts wallet addresses, returns list of WalletScore
- [ ] **B.WA.05** — POST /batch/score for bulk scoring (100 addresses per call)
- [ ] **B.WA.06** — Redis cache layer: 24h TTL for static scores, 1h TTL for dynamic scores; key = `wallet:{chain_id}:{address}`
- [ ] **B.WA.07** — N-hop chain analysis request (1-3 hops configurable per vendor API)
- [ ] **B.WA.08** — Per-vendor rate limiting: token bucket algorithm; configurable tokens/minute
- [ ] **B.WA.09** — Circuit breaker: >5 failures per vendor per minute → open circuit → fallback vendor
- [ ] **B.WA.10** — Vendor health check: GET /vendors/status — returns per-vendor health, rate limit remaining, circuit state
- [ ] **B.WA.11** — Cache warmup on service start: pre-score known wallet list from database
- [ ] **B.WA.12** — GET /cache/status: hit rate, expiry counts, size, top vendors by request volume
- [ ] **B.WA.13** — Prometheus metrics: cache hit rate, vendor latency p50/p95/p99, circuit breaker state, rate limit exhaustion

**Acceptance criteria:**
- ✅ Wallet score for 100 addresses completes <30s
- ✅ Cache hit rate >90% after 1 hour of operation
- ✅ Circuit breaker opens within 30s of vendor failure; auto closes after cooldown
- ✅ Switch between TRM Labs and Chainalysis without code change (config-only)

### B.2.3 risk-scoring-service

| Attribute | Value |
|-----------|-------|
| Language | Python 3.12+ |
| Frameworks | FastAPI, SQLAlchemy, PostgreSQL |
| Repo | `services/risk-scoring-service/` |

**Tasks:**
- [ ] **B.RS.01** — FastAPI service scaffold with PostgreSQL async connection
- [ ] **B.RS.02** — POST /score/transaction — receives canonical txn + wallet scores; returns contribution to customer risk
- [ ] **B.RS.03** — GET /customer/{id}/risk-profile — returns current tier, numeric score, factor breakdown
- [ ] **B.RS.04** — Scoring factor implementation: velocity deviation (z-score vs baseline), wallet risk (from adapter), counterparty risk, sanctions hit count, PEP flags, adverse media recency, jurisdiction risk, source-of-funds consistency
- [ ] **B.RS.05** — Re-scoring triggers: new txn processed → recalculate; sanctions list update → recalculate affected; PEP DB update → recalculate; manual re-score via API
- [ ] **B.RS.06** — Risk tier escalation: 3 consecutive HIGH-scoring events → auto-upgrade to HIGH tier
- [ ] **B.RS.07** — Scheduled time-decay: factors with age >90 days decay by 50%
- [ ] **B.RS.08** — POST /customer/{id}/recalculate — manual re-score with reason (publishes to forensic.events)
- [ ] **B.RS.09** — Prometheus metrics: scoring distribution per tier, re-score latency, recalculation triggers count
- **Acceptance:**
- ✅ Customer risk score updates within 30s of new transaction
- ✅ Tier escalation: 3 consecutive HIGH events → MEDIUM → HIGH upgrade
- ✅ Manual re-score with reason completes <2s; forensic event recorded

---

# Squad C — Compliance UX

**Motto:** *"Every case closed. Every SAR filed. Every trail sealed."*

**Squad C builds the compliance-facing workflows — Travel Rule handshake with counterparties, case management for alert investigation, SAR generation and filing, and the critical tamper-proof forensic audit ledger. Squad C also owns the AML Admin Portal that compliance analysts use daily.**

---

## C.1 Mission & Ownership

| Boundary | Owns | Consumes From | Produces For |
|----------|------|---------------|-------------|
| **Travel Rule** | TRP messaging, counterparty discovery, unhosted wallet EDD workflow | TME (Squad A) — decision: Travel Rule needed | TME (Squad A) — decision: Travel Rule outcome |
| **Case Management** | Alert lifecycle state machine, investigation workspace, evidence management; writes to aml_alert, aml_case, case_alert_link, case_party_link, case_activity_log, str_report | TME (Squad A) — alerts.generated topic | AML Admin Portal (Squad C), forensic DB (Squad C) |
| **Regulatory Reporting** | SAR generation (JFIU STR XML), HKMA returns, Airflow report DAGs; reads from str_report, writes to kpi_snapshot for regulatory metrics | Case management (Squad C) | JFIU portal, HKMA |
| **Forensic Audit** | Tamper-proof WORM ledger, hash-chain, Merkle trees, external witness publishing | All services — forensic.events topic | Regulators, external auditors |
| **Admin Portal** | KPI dashboard, alert queue, case workspace, config screens, reporting UI, batch scan page, graph exploration view | Case management, TME, risk scoring, audit, batch scanning, graph analytics | Compliance analysts |
| **Batch Scanning** | T+1 next-day batch analysis, Airflow DAG orchestration, 10 batch-only analyses, batch alert generation, daily AML briefing; reads detection_scenario for batch scenarios; writes batch_job, batch_scan_run, batch_scan_result, batch_alert, batch_peer_group, batch_behavioral_baseline, kpi_snapshot, scenario_kpi | TME (Squad A), ingestion (Squad A), blockchain indexer (Squad B), wallet analytics (Squad B), graph analytics (Squad B) | CMS (Squad C), Admin Portal (Squad C) |

## C.2 Services — Detailed Specifications

### C.2.1 travelrule-gateway

| Attribute | Value |
|-----------|-------|
| Language | Python 3.12+ |
| Orchestration | Temporal.io (Python SDK) |
| Vendor API | Notabene TRP (REST) |
| Repo | `services/travelrule-gateway/` |

**TravelRuleWorkflow (Temporal) — state machine:**

```
[travelrule.requests topic]
       │
       ▼
┌──────────────────────┐
│ Counterparty         │
│ Discovery            │──────── Notabene directory API
│ (Notabene)           │
└───────┬──────────────┘
        │
   ┌────┴────┐
   │ FOUND?  │
   └────┬────┘
        │
   ┌────┴────┐         ┌─────────────────────┐
   │ YES     │         │ NO (unhosted)        │
   └────┬────┘         └───────┬─────────────┘
        │                      │
        ▼                      ▼
┌──────────────────┐  ┌──────────────────────┐
│ Construct TRP    │  │ Apply unhosted       │
│ message          │  │ wallet EDD rules     │
│ (originator info)│  │ Check paired fiat    │
│ Send             │  │ account risk         │
└───────┬──────────┘  └───────┬──────────────┘
        │                      │
        ▼                      ▼
┌──────────────────┐  ┌──────────────────────┐
│ Await response   │  │ Generate EDD case    │
│ (5 min timeout)  │  │ Flag for manual      │
│ Retries: 3       │  │ review               │
└───────┬──────────┘  └───────┬──────────────┘
        │                      │
   ┌────┴────┐                 │
   │ RESPONSE│                 │
   └────┬────┘                 │
        │                      │
   ┌────┴────┐                 │
   │ VALID?  │                 │
   └────┬────┘                 │
        │                      │
   ┌────┴────┐                 │
   │ YES     │ NO (timeout)    │
   └────┬────┘                 │
        │                      │
        ▼                      ▼
┌──────────────────┐  ┌──────────────────────┐
│ Publish to       │  │ Publish to           │
│ travelrule.      │  │ travelrule.results   │
│ results (PASS)   │  │ (MANUAL_REVIEW)      │
└──────────────────┘  └──────────────────────┘
```

**Tasks:**
- [ ] **C.TR.01** — Temporal worker scaffold (Python SDK)
- [ ] **C.TR.02** — Kafka consumer for travelrule.requests topic
- [ ] **C.TR.03** — Notabene REST integration: counterparty discovery API
- [ ] **C.TR.04** — TRP message construction: originator name, address, account, jurisdiction; beneficiary name, account
- [ ] **C.TR.05** — TRP message send and response handling
- [ ] **C.TR.06** — 5-minute timeout with 3 retries; hold transaction on failure
- [ ] **C.TR.07** — Unhosted wallet branch: enhanced due diligence trigger, paired fiat account risk check
- [ ] **C.TR.08** — TravelRuleWorkflow Temporal definition with retries, compensation, and timeout
- [ ] **C.TR.09** — Publish results to travelrule.results topic (PASS | HOLD | MANUAL_REVIEW)
- [ ] **C.TR.10** — Publish forensic event for any manual intervention in Travel Rule workflow
- [ ] **C.TR.11** — Prometheus metrics: workflow duration, success rate, timeout rate, counterparty match rate

**Acceptance criteria:**
- ✅ TravelRuleWorkflow completes for VASP-to-VASP transfer <2 min (including counterpary response time)
- ✅ Unhosted wallet transfer >HKD 8,000 triggers EDD path
- ✅ Timeout after 5 min without response → HOLD + manual review case created
- ✅ Manual intervention (release/block) creates forensic event

### C.2.2 case-management-service

| Attribute | Value |
|-----------|-------|
| Language | Python 3.12+ |
| Frameworks | FastAPI, SQLAlchemy, Temporal (workflow client) |
| DB | PostgreSQL (cases, alerts, notes, evidence) |
| Repo | `services/case-management-service/` |

**Alert lifecycle:**
```
NEW ──→ ASSIGNED ──→ UNDER_INVESTIGATION ──→ CLOSED_FALSE_POSITIVE
                                        └──→ CLOSED_MONITORING
                                        └──→ SAR_FILED ──→ (linked to STR)
```

**Tasks:**
- [ ] **C.CM.01** — Kafka consumer for alerts.generated topic
- [ ] **C.CM.02** — Alert lifecycle state machine implementation (state table + Temporal workflow enforcement)
- [ ] **C.CM.03** — AlertAssignmentWorkflow: round-robin by queue depth; notify via in-app notification; escalate if unassigned >1hr
- [ ] **C.CM.04** — InvestigationWorkflow: hold active transaction (call TME hold API), gather evidence, additional blockchain queries, document findings; 4hr SLA timer
- [ ] **C.CM.05** — SARApprovalWorkflow: peer review → manager → compliance officer → file to JFIU; 24hr SLA timer
- [ ] **C.CM.06** — EscalationWorkflow: high-risk unactioned >1hr → team lead → compliance manager → MLRO (progressive notification)
- [ ] **C.CM.07** — REST API: GET /alerts (paginated, filterable by status/tier/date/assignee, sortable)
- [ ] **C.CM.08** — REST API: GET /alerts/{id} (full detail with linked txns, rules, scores)
- [ ] **C.CM.09** — REST API: POST /cases (create case from alert)
- [ ] **C.CM.10** — REST API: POST /cases/{id}/transitions (advance state — validated by Temporal)
- [ ] **C.CM.11** — REST API: GET /cases/{id} (full investigation workspace data)
- [ ] **C.CM.12** — Investigation workspace: transaction timeline (grouped by date, linked txns)
- [ ] **C.CM.13** — Investigation workspace: customer 360 profile (risk tier, recent activity, linked wallets, PEP status)
- [ ] **C.CM.14** — Investigation workspace: network graph data endpoint (for Cytoscape.js frontend)
- [ ] **C.CM.15** — Note system: create note, read-only after save (no edit/delete), note types (observation, action_taken, escalation_reason)
- [ ] **C.CM.16** — Evidence upload service: POST /cases/{id}/evidence → validates file (max 20MB), virus scan (ClamAV), stores on MinIO, stores hash in case record
- [ ] **C.CM.17** — SAR draft pre-population: maps case data to STR form fields
- [ ] **C.CM.18** — SAR draft view/edit/preview workflow
- [ ] **C.CM.19** — Data export for read-only audit replica
- [ ] **C.CM.20** — Publish all case state transitions, alert dispositions, notes, evidence uploads to forensic.events topic
- [ ] **C.CM.21** — Publish SAR lifecycle events to forensic.events (draft → reviewed → approved → filed → JFIU ack)
- [ ] **C.CM.22** — Prometheus metrics: alert ingestion rate, case resolution time (p50/p95/p99), SAR filing rate

**Acceptance criteria:**
- ✅ 4 Temporal workflows operational: assignment, investigation, SAR approval, escalation
- ✅ Alert → case → investigation → SAR lifecycle end-to-end test passes
- ✅ State machine enforces valid transitions; invalid transitions rejected
- ✅ All state changes and decisions published to forensic.events (forensic audit)
- ✅ Investigation workspace returns all linked data <3s

### C.2.3 regulatory-reporting-service

| Attribute | Value |
|-----------|-------|
| Language | Python 3.12+ |
| Frameworks | FastAPI, Jinja2 (XML templates), Airflow (DAG definitions) |
| Repo | `services/regulatory-reporting-service/` |

**Tasks:**
- [ ] **C.RR.01** — SAR/STR XML template engine (Jinja2) — JFIU STREAMS 2 compatible format
- [ ] **C.RR.02** — POST /sar/generate — pre-populates STR from case data; returns XML preview
- [ ] **C.RR.03** — POST /sar/submit — finalise SAR XML, attach to case record, flag for JFIU upload
- [ ] **C.RR.04** — JFIU STREAMS 2 portal assisted upload (web + SFTP via EU/SFTP in v2)
- [ ] **C.RR.05** — POST /filing/submit (STREAMS 2 submission)
- [ ] **C.RR.06** — GET /filing/{id}/status (track acknowledgement from JFIU)
- [ ] **C.RR.07** — HKMA statistical return generator: monthly transaction volume report, quarterly AML metrics report
- [ ] **C.RR.08** — POST /reports/generate (trigger report for given period + type)
- [ ] **C.RR.09** — Airflow DAG: daily SAR filing status check
- [ ] **C.RR.10** — Airflow DAG: monthly HKMA return generation on day 1
- [ ] **C.RR.11** — Airflow DAG: quarterly comprehensive AML report
- [ ] **C.RR.12** — Publish all SAR lifecycle events to forensic.events
- [ ] **C.RR.13** — Prometheus metrics: SARs generated/submitted/filed/acknowledged; report generation duration

**Acceptance criteria:**
- ✅ SAR XML matches JFIU STREAMS 2 schema
- ✅ SAR draft → review → approve → file workflow complete
- ✅ Monthly HKMA report generated on schedule (Airflow DAG)
- ✅ JFIU acknowledgement reference recorded and tracked

### C.2.4 forensic-audit-service

| Attribute | Value |
|-----------|-------|
| Language | Python 3.12+ |
| Kafka | aiokafka (idempotent consumer) |
| DB | aml_forensic PostgreSQL (WORM, physically separate, sole writer) |
| Blockchain | Web3.py (Polygon/Bitcoin testnet witness) |
| Repo | `services/forensic-audit-service/` |

**This service is the SOLE WRITER to the ForensicDB. No other service has credentials.**

**Tasks:**

**Core ingestion:**
- [ ] **C.FA.01** — Kafka consumer for forensic.events (partitioned by event_category; idempotent)
- [ ] **C.FA.02** — Event validation: reject events missing operator_id, session_id, client_ip, user_agent, justification
- [ ] **C.FA.03** — Record-level SHA-256 hashing: SHA-256(record_type, payload, operator_id, business_timestamp, previous_record_hash)
- [ ] **C.FA.04** — Insert into appropriate forensic table (alert_disposition, case_transition, rule_change, risk_override, access_log, sar_lifecycle)
- [ ] **C.FA.05** — Global hash chain append: chain_n = SHA-256(chain_n-1, table_name, record_hash, timestamp)

**Merkle tree:**
- [ ] **C.FA.06** — Per-table Merkle tree computation (balanced binary tree over records inserted per hour)
- [ ] **C.FA.07** — Merkle root storage in forensic.merkle_root table
- [ ] **C.FA.08** — Hourly Merkle root publish to Polygon testnet via smart contract or OP_RETURN

**Verification:**
- [ ] **C.FA.09** — forensic-verifier CLI tool: connects to forensic replica, recomputes all hashes from genesis, compares to stored hashes
- [ ] **C.FA.10** — forensic-verifier output: PASS (all match) or FAIL (list of diverging records with expected vs actual hash)
- [ ] **C.FA.11** — Scheduled verifier (15-min interval on read-only replica); chain break → P0 alert via Prometheus AlertManager
- [ ] **C.FA.12** — GET /forensic/records?category=&from=&to=&limit= REST API (auditor read-only)
- [ ] **C.FA.13** — GET /forensic/chain/verify — returns current chain state, last verified timestamp, integrity status
- [ ] **C.FA.14** — GET /forensic/merkle/{table}/{date} — returns Merkle root for a given table + date

**Witness & retention:**
- [ ] **C.FA.15** — External witness publisher: composite hash (all Merkle roots + chain head) → Polygon/Bitcoin testnet; stores tx reference
- [ ] **C.FA.16** — Daily attestation: signed blob (global chain head + all Merkle roots) uploaded to cloud immutable store (S3 Object Lock / Azure Immutable Blob)
- [ ] **C.FA.17** — Rete ntion manager: exports records >7 years to WORM optical media; verifies export hash; logs chain-of-custody
- [ ] **C.FA.18** — Prometheus metrics: insert rate, chain head age, integrity status (0/1), witness publication age, retention archival status

**Acceptance criteria:**
- ✅ ForensicDB accepts writes; hash chain verifiable
- ✅ forensic-verifier detects any tampered record (single bit flip)
- ✅ External witness publishes hourly; txId verifiable on block explorer
- ✅ P0 alert fires on chain break within 1 minute
- ✅ WORM enforced: INSERT-only at DB, FS, and storage levels

### C.2.5 batch-scanning-service

| Attribute | Value |
|-----------|-------|
| Language | Python 3.12+ |
| Orchestration | Apache Airflow (Kubernetes executor) |
| Analysis Runtime | Parallel Kubernetes Jobs (elastic 16 CPU/64GB burst) |
| Data Format | Parquet (on MinIO, 90-day retention) |
| DB | TimescaleDB (aml_analytics), PostgreSQL (aml_core) |
| Repo | `services/batch-scanning-service/` |

**The batch-scanning-service orchestrates T+1 (next-day) batch transaction scanning — complementing the real-time TME by performing computationally intensive analyses that are impossible within the <500ms latency SLA.**

**Airflow DAG — `t1_batch_scan_pipeline`** (scheduled daily at 02:00 HKT):

```
[02:00 HKT — DAG Trigger]
       │
       ▼
┌──────────────────────┐
│ Stage 1: Pre-flight  │──── Poll ingestion-service health + blockchain-indexer
│ Sensor               │     lag metrics. Verify all chains have finality for
│ (30 min timeout)     │     previous day. Fail DAG if pre-flight not met.
└───────┬──────────────┘
        │
        ▼
┌──────────────────────┐
│ Stage 2: Data        │──── Pull all canonical_transaction records for target
│ Extraction           │     date (00:00-23:59 HKT) from aml_core. Export to
│ (<30 min for 500K)   │     Parquet files on MinIO (batch-data bucket).
│                      │     Include real-time TME decisions, scores, trigger rules.
└───────┬──────────────┘
        │
        ▼
┌──────────────────────┐
│ Stage 3: Enrichment  │──── Augment each transaction with: full customer profile
│                      │     (risk tier, PEP status, account age, declared income),
│                      │     refreshed wallet analytics scores, peer group assignment,
│                      │     real-time TME decision metadata.
└───────┬──────────────┘
        │
        ▼
┌──────────────────────┐
│ Stage 4: Parallel    │──── Launch 10 Kubernetes Jobs (one per analysis type):
│ Analysis Dispatcher  │     I.2.1  Full-Day Customer Behavioral Baselining
│ (10 K8s Jobs)        │     I.2.2  Peer Group Comparative Analysis
│ <20 min each         │     I.2.3  Multi-Account Structuring Detection
│                      │     I.2.4  Velocity Pattern Mining (Multi-Day Windows)
│                      │     I.2.5  Network Graph Anomaly Detection
│                      │     I.2.6  Ensemble ML Scoring (Full Feature Set)
│                      │     I.2.7  Rule Effectiveness Retrospective
│                      │     I.2.8  Cross-Rail Layering Detection (Full Fund Flow)
│                      │     I.2.9  Sanctions/Screening Retrospective
│                      │     I.2.10 SAR Pre-Population Intelligence
└───────┬──────────────┘
        │ (collect results via shared batch_scan_result table)
        ▼
┌──────────────────────┐
│ Stage 5: ML Scoring  │──── Load production XGBoost ensemble from MinIO. Compute
│ (Aggregation)        │     full feature vectors (behavioral + peer + graph +
│                      │     temporal + cross-rail features). Batch inference on
│                      │     complete daily dataset. Store scores with SHAP explanations.
└───────┬──────────────┘
        │
        ▼
┌──────────────────────┐
│ Stage 6: Alert       │──── Aggregate findings from all 10 analyses. Deduplicate
│ Generation           │     (same txn flagged multiple times → single alert with
│                      │     all trigger reasons). Assign composite batch risk score.
│                      │     Set priority (LOW/MEDIUM/HIGH). Publish to batch.alerts
│                      │     topic. Create CMS cases with source=BATCH_SCAN.
└───────┬──────────────┘
        │
        ▼
┌──────────────────────┐
│ Stage 7: Daily       │──── Compile top 10 riskiest txns, peer group anomaly summary,
│ Briefing             │     rule effectiveness metrics, false positive trends, new
│ (<5 min)             │     pattern detection summary, SAR pre-population queue.
│                      │     Render as PDF; store on MinIO (daily-briefings bucket).
│                      │     Email notification to compliance team.
└───────┬──────────────┘
        │
        ▼
┌──────────────────────┐
│ Stage 8: Feedback    │──── Write batch findings back to TimescaleDB for real-time
│ Loop                 │     rule effectiveness tracking. Update peer group baselines
│                      │     (monthly recomputation). Publish batch.dispositions to
│                      │     forensic.events for tamper-proof audit.
└──────────────────────┘
```

**Key contract — Kafka topics produced:**

```
Topic: batch.alerts (6 partitions, 90-day retention, keyed by customer_id)
{
  "alert_id": "01J...",
  "run_id": "01J...",
  "transaction_id": "01J...",
  "analysis_types": ["BEHAVIORAL_DEVIATION", "PEER_GROUP_ANOMALY"],
  "batch_risk_score": 72,
  "priority": "MEDIUM",
  "alert_reason": "Customer daily volume 4.2σ above 90-day baseline + 3.1σ above peer group",
  "customer_id": "CUST-001",
  "scan_date": "2026-07-02",
  "created_at": "2026-07-03T03:15:00+08:00"
}

Topic: batch.results (6 partitions, 365-day retention)
{
  "run_id": "01J...",
  "scan_date": "2026-07-02",
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
  "daily_briefing_path": "s3://daily-briefings/2026-07-02-daily-aml-briefing.pdf"
}
```

**Key contract — internal API for ad-hoc/manual triggers:**

```
POST /api/v1/batch/scan/trigger
Request: { "scan_date": "2026-07-02" }
Response: { "run_id": "01J...", "status": "QUEUED", "estimated_completion": "2026-07-03T06:00:00+08:00" }

GET /api/v1/batch/scan/{run_id}/status
Response: { "run_id", "scan_date", "status": "RUNNING", "current_stage": 4, "jobs_completed": 6, "jobs_total": 10, "txns_processed": 250000 }

GET /api/v1/batch/scan/{run_id}/results
Response: { ... full batch.results payload }

GET /api/v1/batch/scan/daily-briefing/{date}
Response: { "briefing_path": "s3://daily-briefings/2026-07-02-daily-aml-briefing.pdf", "summary": { ... } }

GET /api/v1/batch/scan/history?from=2026-06-01&to=2026-07-02&page=1
Response: { "runs": [ { "run_id", "scan_date", "status", "duration_seconds", "alerts_generated", "top_finding" } ], "total": 30 }

DELETE /api/v1/batch/scan/{run_id}
Response: { "success": true, "message": "Results purged; scan date can be re-run" }
```

**Tasks:**
- [ ] **C.BT.01** — FastAPI service scaffold with Airflow DAG operator registration
- [ ] **C.BT.02** — Airflow DAG `t1_batch_scan_pipeline`: define all 8 stages with dependencies, retries, and SLA timers
- [ ] **C.BT.03** — Pre-flight Sensor: poll ingestion-service health + blockchain-indexer lag; verify finality; 30-min timeout; fail DAG on pre-flight failure
- [ ] **C.BT.04** — Data Extraction stage: pull from aml_core for target date; export as Parquet to MinIO batch-data bucket; track progress via batch.scan.progress topic
- [ ] **C.BT.05** — Enrichment stage: augment with customer profiles, wallet analytics (call Squad B adapter), peer group assignment
- [ ] **C.BT.06** — Parallel Analysis Dispatcher: Kubernetes Job launcher; create Job YAML per analysis type; monitor Job status; collect results via batch_scan_result table
- [ ] **C.BT.07** — Full-Day Customer Behavioral Baselining Job: per-customer daily stats vs 30/90-day baseline; >3 sigma flagging
- [ ] **C.BT.08** — Peer Group Comparative Analysis Job: assign to groups by segment/jurisdiction/income; flag peer group outliers
- [ ] **C.BT.09** — Multi-Account Structuring Detection Job: traverse party graph via Apache AGE; aggregate linked account outflows; detect threshold evasion across accounts
- [ ] **C.BT.10** — Velocity Pattern Mining Job: pull 7-day history; time-series decomposition; classify ramping/burst-and-pause/cyclical patterns
- [ ] **C.BT.11** — Network Graph Anomaly Detection Job: build full daily graph; PageRank + Louvain community detection; compare against historical baseline snapshots
- [ ] **C.BT.12** — Ensemble ML Scoring Job: load XGBoost ensemble from MinIO; compute full feature vectors; batch inference; SHAP explanations
- [ ] **C.BT.13** — Rule Effectiveness Retrospective Job: per-rule alert rate, FPR, detection overlap with batch; generate rule tuning recommendations
- [ ] **C.BT.14** — Cross-Rail Layering Detection Job: reconstruct fiat-to-stablecoin-to-fiat flows; detect 4+ hop layering; build fund flow trail visualization data
- [ ] **C.BT.15** — Sanctions/Screening Retrospective Job: re-screen all daily txns against latest sanctions list; detect stale-list-misses
- [ ] **C.BT.16** — SAR Pre-Population Intelligence Job: for high-confidence findings (>70), pre-compute SAR data; generate draft XML; link to batch alert
- [ ] **C.BT.17** — Batch Alert Generator: aggregate + deduplicate findings; compute composite risk score; publish to batch.alerts Kafka topic
- [ ] **C.BT.18** — CMS integration: create cases with source=BATCH_SCAN; priority=LOW by default; enrich with batch analysis context and pre-populated SAR drafts
- [ ] **C.BT.19** — Daily AML Briefing generator: compile top findings; render PDF with tables and charts; store on MinIO; generate email notification
- [ ] **C.BT.20** — REST API: POST /api/v1/batch/scan/trigger (ad-hoc trigger)
- [ ] **C.BT.21** — REST API: GET /api/v1/batch/scan/{run_id}/status, GET /api/v1/batch/scan/{run_id}/results
- [ ] **C.BT.22** — REST API: GET /api/v1/batch/scan/daily-briefing/{date}, GET /api/v1/batch/scan/history
- [ ] **C.BT.23** — REST API: DELETE /api/v1/batch/scan/{run_id} (idempotent re-run support)
- [ ] **C.BT.24** — Kafka producers: batch.scan.commands, batch.scan.progress, batch.alerts, batch.results
- [ ] **C.BT.25** — Database migrations: batch_scan_run, batch_scan_result, batch_alert, batch_peer_group, batch_behavioral_baseline (TimescaleDB hypertable)
- [ ] **C.BT.26** — Publish all batch findings and alert dispositions to forensic.events for tamper-proof audit
- [ ] **C.BT.27** — Prometheus metrics: DAG stage duration, Jobs completed/failed, alerts generated, briefing generation time, scan completion time
- [ ] **C.BT.28** — Grafana dashboard "T+1 Batch Scanning": DAG run history, stage-by-stage latency, alert volume trend, anomaly type breakdown

**Acceptance criteria:**
- ✅ Airflow DAG triggers daily at 02:00 HKT; completes within 4-hour window for 500K txns
- ✅ Pre-flight sensor passes: all chains have finality; ingestion healthy
- ✅ All 10 analyses execute in parallel; each completes <20 min
- ✅ Behavioral baseline deviation catches >3 sigma anomalies
- ✅ Multi-account structuring catches 3+ linked accounts aggregating above threshold
- ✅ Batch alerts generated and delivered to CMS within SLA
- ✅ Daily briefing PDF generated and emailed to compliance team
- ✅ Idempotent: re-running same date overwrites previous results (no duplicates)
- ✅ Manual ad-hoc trigger works for arbitrary dates
- ✅ All findings published to forensic.events (complete audit trail)

### C.2.6 aml-portal (Frontend)

| Attribute | Value |
|-----------|-------|
| Framework | Next.js 14+ (App Router), React 18+ |
| Language | TypeScript 5+ |
| UI | shadcn/ui (Radix primitives + Tailwind CSS) |
| State | React Query (server), Zustand (client) |
| Viz | Cytoscape.js (graph), Recharts (charts) |
| Auth | Keycloak OIDC (next-auth or next-keycloak) |
| Repo | `apps/aml-portal/` |

**Tasks:**

**G.1 — Foundation:**
- [ ] **C.PO.01** — Scaffold Next.js 14+ App Router with TypeScript strict mode
- [ ] **C.PO.02** — shadcn/ui initialisation + custom theme (brand colours: navy #1B3A5C, grey #556B82)
- [ ] **C.PO.03** — React Query provider + query client configuration
- [ ] **C.PO.04** — Zustand store for UI state (sidebar open, current case, filters)
- [ ] **C.PO.05** — Keycloak OIDC integration: login, token refresh, role-based route guards (admin, analyst, manager, auditor)
- [ ] **C.PO.06** — Layout shell: sidebar navigation, top bar with user menu + roles, notification badge
- [ ] **C.PO.07** — Responsive layout (desktop-first; tablet as secondary target)

**G.2 — KPI Dashboard:**
- [ ] **C.PO.08** — Dashboard page scaffold with date-range picker (presets: 24h, 7d, 30d, 90d, custom)
- [ ] **C.PO.09** — Alert volume chart: bar chart (time series) + breakdown by rule/risk tier/channel
- [ ] **C.PO.10** — Alert-to-case conversion rate: trend line (area chart) over date range
- [ ] **C.PO.11** — False-positive rate: gauge (semi-circular) + trend line
- [ ] **C.PO.12** — SAR filing volume: stacked bar (draft/reviewed/filed/acknowledged)
- [ ] **C.PO.13** — Average case resolution time: bar chart with p50/p95/p99 overlay
- [ ] **C.PO.14** — Queue backlog: bar chart with aging distribution (0-4hr, 4-12hr, 12-24hr, >24hr)
- [ ] **C.PO.15** — SLA compliance: table per investigator + team (% within SLA)
- [ ] **C.PO.16** — Customer risk tier breakdown: donut chart (LOW/MEDIUM/HIGH/PEP/SANCTIONED)
- [ ] **C.PO.17** — Dashboard export to PDF (via browser print or puppeteer service)

**G.3 — Alert Queue:**
- [ ] **C.PO.18** — /alerts: server-side paginated table; filters for risk tier, rule, status, date range, channel
- [ ] **C.PO.19** — /alerts/{id}: detail page with linked transactions table, triggered rules list, risk score breakdown
- [ ] **C.PO.20** — Customer 360 summary panel: risk tier badge, recent activity timeline, linked wallets, PEP indicator
- [ ] **C.PO.21** — Wallet risk summary: risk score badge, tags (mixer, sanctioned, exchange), high-risk interactions count, chain analysis summary

**G.4 — Case Management:**
- [ ] **C.PO.22** — /cases: table with status badge, priority, assignee, age; bulk assignment, CSV export
- [ ] **C.PO.23** — /cases/{id}: 3-panel layout — transaction timeline (left), investigation workspace (centre), customer profile (right)
- [ ] **C.PO.24** — Transaction timeline: grouped by date, expandable list of linked txns with key fields
- [ ] **C.PO.25** — Note system: textarea + submit; read-only display after save; types: observation/action/escalation
- [ ] **C.PO.26** — Evidence upload: drag-and-drop zone, file list with hash display, virus scan status badge
- [ ] **C.PO.27** — SAR draft workspace: editable form pre-populated from case data; preview panel; submit button
- [ ] **C.PO.28** — Network graph (Cytoscape.js): nodes = parties/wallets; edges = transfers; colour-coded by risk; zoom/pan
- [ ] **C.PO.29** — SAR approval workflow UI: visual progress bar (peer review → manager → compliance officer → filed)
- [ ] **C.PO.30** — Audit trail timeline within case: expandable list of all events/decisions

**G.5 — Configuration:**
- [ ] **C.PO.31** — /config/rules: table of rules (name, category, enabled, tier); toggle enable/disable; shadow-mode switch; version dropdown
- [ ] **C.PO.32** — /config/thresholds: editable per-tier thresholds (LOW/MEDIUM/HIGH) for all rule categories
- [ ] **C.PO.33** — /admin/users: user list with roles; assign role dropdown; Keycloak user search
- [ ] **C.PO.34** — /audit/logs: searchable table (event type, date range, user, resource); filter; CSV export
- [ ] **C.PO.35** — /forensic/verify: paste chain head hash → verify button → display PASS/FAIL with detail; show last verified timestamp

**G.6 — Reporting:**
- [ ] **C.PO.36** — /reports: SAR list (searchable + filterable); HKMA return list; report scheduling config
- [ ] **C.PO.37** — SAR preview + edit: XML viewer with collapsible sections; edit-in-place for key fields; submit button
- [ ] **C.PO.38** — Report scheduling: date picker, frequency (once/daily/monthly/quarterly), format (PDF/CSV/XML), Airflow DAG trigger config

**Acceptance criteria:**
- ✅ Portal loads; Keycloak login works; RBAC route guards block unauthorised roles
- ✅ Dashboard renders all 8 KPIs with live data; date filter functional
- ✅ 10K alerts in queue renders <3s; click-through to detail <1s
- ✅ Full investigation workspace functional: timeline, graph, notes, evidence, SAR draft
- ✅ forensic/verify endpoint returns PASS/FAIL for auditor use

---

# Squad D — Platform & Infrastructure

**Motto:** *"Ship it. Secure it. Scale it."*

**Squad D builds and maintains the entire foundation that every other squad runs on — the on-premises Kubernetes cluster, all stateful infrastructure (PostgreSQL, Kafka, Redis, MinIO, Temporal), the CI/CD pipeline, security controls, and the data platform (Airflow, TimescaleDB). Squad D starts first (Week 0) and runs through the entire project lifecycle.**

---

## D.1 Mission & Ownership

| Boundary | Owns | Consumes From | Produces For |
|----------|------|---------------|-------------|
| **Kubernetes** | Cluster provisioning, node management, network policies, monitoring stack | Hardware/data centre | All squads |
| **Stateful Services** | PostgreSQL (all instances), Kafka, Redis, MinIO, Temporal | K8s infrastructure | All squads |
| **CI/CD** | GitLab, GitLab Runner, ArgoCD, container registry | Source code from all squads | All squads |
| **Security** | HSM, Vault, mTLS, WAF, CIS hardening, penetration testing | All squads | All squads + regulators |
| **Data Platform** | Airflow, TimescaleDB, ETL pipelines, ML training infrastructure | All squads (data producers) | All squads (data consumers) |
| **Monitoring** | Prometheus, Grafana, Loki, Tempo, AlertManager, dashboards | All services | All squads + DevOps |

## D.2 Services & Infrastructure — Detailed Specifications

### D.2.1 Kubernetes Cluster Provisioning & Management

**Tasks:**
- [ ] **D.K8.01** — Provision 3 control-plane + 6 worker nodes (Ubuntu 24.04 LTS), hardware-adjacent to Hong Kong data centre (Equinix HK/MEGA-i)
- [ ] **D.K8.02** — Install k3s or RKE2 with Calico CNI (configure overlay network, NetworkPolicies, eBPF dataplane)
- [ ] **D.K8.03** — Configure VLAN segmentation: DMZ (API gateway + blockchain RPC), Application (microservices), Data (PG clusters + MinIO), Forensic (ForensicDB only, isolated), Management (jumpbox)
- [ ] **D.K8.04** — HAProxy (L4 on bare metal) + Nginx Ingress Controller (L7 in cluster) with HSM-backed TLS certificate provisioning
- [ ] **D.K8.05** — Kubernetes NetworkPolicies: default-deny across all namespaces; per-service ingress/egress rules; separate policy for forensic VLAN
- [ ] **D.K8.06** — Kubernetes resource quotas per namespace (see spec Section 6.3): limits and requests
- [ ] **D.K8.07** — Prometheus operator + Grafana stack: cluster metrics, node metrics, pod metrics, custom service metrics; 30-day metric retention
- [ ] **D.K8.08** — Loki (log aggregation) + Promtail daemonset; 90-day log retention; structured log scraping (JSON)
- [ ] **D.K8.09** — Tempo (distributed tracing) — trace collection via OpenTelemetry SDKs; 14-day retention; trace-to-log correlation
- [ ] **D.K8.10** — AlertManager configuration: P0 alerts (SMS/PagerDuty), P1 (email + Slack), P2 (Slack); on-call rotation schedules
- [ ] **D.K8.11** — Velero for K8s resource backup (etcd snapshots, PV snapshots); weekly full backup to MinIO
- [ ] **D.K8.12** — Jumpbox/bastion host: SSO + MFA (Keycloak OIDC); no direct SSH to cluster nodes; audit-logged sessions
- [ ] **D.K8.13** — Horizontal Pod Autoscaler (HPA) configuration for stateless services (CPU + Kafka consumer lag based)

**Acceptance criteria:**
- ✅ `kubectl get nodes` — all nodes Ready; pod network functional across namespaces
- ✅ Ingress routes traffic to services; TLS certs issued and verified
- ✅ NetworkPolicy blocks cross-namespace traffic by default; whitelist only
- ✅ Grafana dashboard shows cluster metrics; Loki ingests pod logs; Tempo receives traces
- ✅ AlertManager fires test alert

### D.2.2 Stateful Infrastructure Deployments

**PostgreSQL instances:**
- [ ] **D.DB.01** — Deploy CloudNativePG (CNP) operator; configure 3-node Patroni cluster for `aml_core` (128GB/8vCPU, NVMe, streaming replication, automatic failover)
- [ ] **D.DB.02** — Deploy 2-node Patroni cluster for `aml_audit` (64GB/8vCPU, time-partitioned tables, read-only replica for queries)
- [ ] **D.DB.03** — Deploy physically separate 2-node Patroni cluster for `aml_forensic` (128GB/8vCPU, separate VLAN, WORM enforcement: `chattr +i` on data directory, BEFORE UPDATE/DELETE triggers configured)
- [ ] **D.DB.04** — Configure pgBackRest for all PG instances: daily full backup to MinIO, WAL archiving every 5min; retention: 30 daily + 12 weekly + 12 monthly
- [ ] **D.DB.05** — For `aml_forensic`: configure MinIO S3 Object Lock in Compliance mode (retention lock, no deletion); enable WORM snapshot on storage array
- [ ] **D.DB.06** — Install TimescaleDB extension (for `aml_analytics` schema)
- [ ] **D.DB.07** — Install Apache AGE extension (for `aml_graph` schema)
- [ ] **D.DB.08** — Configure PgBouncer for connection pooling (all PG instances); max 200 client connections, transaction pooling mode

**Kafka / Redpanda:**
- [ ] **D.DM.01** — Deploy 3-broker Redpanda cluster (32GB/8vCPU, 2TB NVMe per broker) via operator
- [ ] **D.DM.02** — Create all 11 topics (see spec Section 3.1.2) with partitions, retention, replication factor 3
- [ ] **D.DM.03** — Configure TLS encryption for client-broker and inter-broker communication
- [ ] **D.DM.04** — Configure SASL/SCRAM authentication for producer/consumer clients
- [ ] **D.DM.05** — Set up Kafka monitoring: consumer lag dashboard (Grafana), throughput charts, partition distribution
- [ ] **D.DM.06** — Configure topic retention cleanup policies: compact for audit/forensic; delete for raw topics

**Redis:**
- [ ] **D.DM.07** — Deploy 2-node Redis active-passive cluster (32GB) via operator
- [ ] **D.DM.08** — Configure TLS + AUTH; eviction policy: allkeys-lru; maxmemory: 28GB
- [ ] **D.DM.09** — Persistence: AOF every 1s; RDB snapshot every 5min

**MinIO:**
- [ ] **D.DM.10** — Deploy 4-node MinIO cluster (erasure coding, 8TB per node) via operator
- [ ] **D.DM.11** — Create buckets: evidence, model-artifacts, backups, historical-exports
- [ ] **D.DM.12** — Enable S3 Object Lock (Compliance mode) on forensic bucket; retention: 7 years
- [ ] **D.DM.13** — Configure TLS + IAM policies: per-service access keys with bucket-scoped policies

**Temporal:**
- [ ] **D.DM.14** — Deploy Temporal server (4 nodes) with PostgreSQL persistence (aml_core schema)
- [ ] **D.DM.15** — Configure TLS + mTLS for worker connections
- [ ] **D.DM.16** — Temporal Web UI deployment for workflow visibility

**Keycloak:**
- [ ] **D.IAM.01** — Deploy Keycloak (3 nodes, PostgreSQL persistence)
- [ ] **D.IAM.02** — Configure LDAP integration for employee directory sync
- [ ] **D.IAM.03** — Define realms: `project-overwatch`; clients: `aml-portal`, `aml-api`, `forensic-verifier`
- [ ] **D.IAM.04** — Define RBAC roles: `admin` (full), `compliance_manager` (approve SAR, edit rules), `analyst` (investigate cases, close alerts), `auditor` (read-only + forensic verify), `readonly` (dashboard + search)
- [ ] **D.IAM.05** — Configure OIDC flows: authorization_code (UI), client_credentials (M2M API)
- [ ] **D.IAM.06** — Create test users for all roles; configure role-to-group mapping

**Acceptance criteria:**
- ✅ All PG clusters healthy (`pg_isready`); Patroni failover test passes
- ✅ ForensicDB WORM: INSERT works, UPDATE/DELETE rejected, `chattr +i` verified
- ✅ All 11 Kafka topics created; message produce/consume working end-to-end
- ✅ Redis cache functional; AOF/RDB recovery tested
- ✅ MinIO upload/download functional; S3 Object Lock prevents deletion
- ✅ Temporal workflow can be registered, started, and queried
- ✅ Keycloak: login with test users; role-based access to portals

### D.2.3 CI/CD Pipeline

**Tasks:**
- [ ] **D.CI.01** — Deploy GitLab Enterprise (self-hosted, on-prem); configure SMTP, LDAP sync
- [ ] **D.CI.02** — Deploy GitLab Runner (Kubernetes executor) with autoscaling (max 10 concurrent jobs)
- [ ] **D.CI.03** — Enable GitLab Container Registry (backed by MinIO S3)
- [ ] **D.CI.04** — Deploy ArgoCD with Git repository per environment (dev, staging, prod); Kustomize overlays pattern
- [ ] **D.CI.05** — Configure ArgoCD sync policy: auto-sync every 3 min (dev), manual approval (staging + prod)
- [ ] **D.CI.06** — Define Python CI pipeline template: lint (ruff) → type check (mypy strict) → test (pytest, >85%) → scan (Bandit, Trivy) → build (distroless python:3.12-slim) → push (Cosign signed) → integrate (ephemeral K8s namespace) → deploy
- [ ] **D.CI.07** — Define TypeScript CI pipeline template: lint (ESLint) → type check (tsc --noEmit) → test (vitest) → scan (Trivy) → build (node:20-alpine) → push (Cosign signed) → deploy
- [ ] **D.CI.08** — Define Go CI pipeline template: lint (golangci-lint) → test (go test -race) → scan (Trivy) → build (golang:1.22-alpine) → push (Cosign signed) → deploy
- [ ] **D.CI.09** — Configure Cosign for container image signing; store signing key in HSM
- [ ] **D.CI.10** — Configure Trivy in CI: fail build on CRITICAL or HIGH CVEs; schedule weekly full registry scan
- [ ] **D.CI.11** — Configure Bandit (Python SAST) in CI; custom rule set for AML-specific security patterns
- [ ] **D.CI.12** — Configure ephemeral test namespace per MR (namespace created on PR, destroyed on merge)

**Acceptance criteria:**
- ✅ Developer pushes code → CI pipeline runs → image built, signed, pushed → ArgoCD deploys to dev → all <15 min
- ✅ CI fails on lint error, type error, test failure, CVE, or Bandit finding
- ✅ Rolling upgrade: zero-downtime deployment confirmed

### D.2.4 Security Infrastructure

**Tasks:**
- [ ] **D.SE.01** — Apply CIS Benchmark for Ubuntu 24.04 LTS (Level 1 + Level 2 for K8s nodes): kernel hardening, file permissions, SSH config, auditd, AIDE
- [ ] **D.SE.02** — Apply CIS Benchmark for Kubernetes (kube-bench): API server, etcd, kubelet, controller-manager, scheduler
- [ ] **D.SE.03** — Configure HSM (Thales Luna 7 or Azure Dedicated HSM): generate root CA, TLS intermediate CA, encryption keys (AES-256 for PostgreSQL TDE, MinIO SSE), TRP signing keys (RSA-4096)
- [ ] **D.SE.04** — Implement service mesh (Linkerd): auto-inject sidecar proxies; enforce mTLS for all inter-service communication
- [ ] **D.SE.05** — Configure mTLS certificate rotation (HSM-issued, 90-day validity, auto-rotation via cert-manager)
- [ ] **D.SE.06** — Deploy HashiCorp Vault (3-node HA cluster, Raft storage backend, HSM unseal)
- [ ] **D.SE.07** — Vault dynamic secrets engine for PostgreSQL (16h TTL, auto-rotation)
- [ ] **D.SE.08** — Vault dynamic secrets for Kafka (SCRAM credentials, 24h TTL)
- [ ] **D.SE.09** — Vault PKI engine for short-lived mTLS certificates (8h TTL)
- [ ] **D.SE.10** — Configure Sealed Secrets (Bitnami): controller in cluster; secret encryption key stored in Vault
- [ ] **D.SE.11** — ModSecurity WAF on API gateway: OWASP CRS, rate limiting (100 req/s per API key), IP blocklist
- [ ] **D.SE.12** — Automated vulnerability scanning: Trivy weekly OS/dependency scan for all running containers; daily scan for new images
- [ ] **D.SE.13** — Infrastructure audit logging: all K8s API calls logged; all SSH sessions recorded; all Vault operations logged
- [ ] **D.SE.14** — SBOM generation: every CI build produces SBOM (Syft); SBOM archived in MinIO with image reference
- [ ] **D.SE.15** — Regulatory compliance dashboard: Grafana view of CIS compliance, vulnerability posture, certificate expiry, audit log integrity

**Acceptance criteria:**
- ✅ CIS scan passes >90% for OS + K8s
- ✅ HSM functional: key generation, signing, rotation all verified
- ✅ mTLS: inter-service curl requires mutual TLS; fails without client cert
- ✅ Vault: dynamic DB credentials created and revoked; PKI certs issued and expire
- ✅ WAF blocks test SQL injection and XSS payloads
- ✅ SBOM generated and stored for every production image

### D.2.5 Data Platform & Orchestration

**Tasks:**
- [ ] **D.DP.01** — Deploy Apache Airflow (2.10+) with Kubernetes executor; PostgreSQL backend
- [ ] **D.DP.02** — Create `aml_analytics` schema on aml_analytics database (TimescaleDB): hypertables for transaction metrics, alert metrics, risk score history
- [ ] **D.DP.03** — Airflow DAG: `ml_training_pipeline` — weekly retraining of XGBoost model on labelled alert data; triggered on Friday 00:00 UTC
- [ ] **D.DP.04** — Airflow DAG: `forensic_witness_publisher` — hourly DAG to compute Merkle roots and publish to Polygon
- [ ] **D.DP.05** — Airflow DAG: `data_quality_checks` — daily validation of canonical schema compliance, orphaned records, referential integrity
- [ ] **D.DP.06** — Airflow DAG: `customer_risk_reassessment` — monthly full customer risk recalculation
- [ ] **D.DP.07** — Set up Prometheus + Grafana for Airflow DAG metrics (DAG duration, task success/failure, SLA misses)

**Acceptance criteria:**
- ✅ Airflow deployed; all DAGs registered and functional
- ✅ TimescaleDB hypertable created; continuous aggregation working
- ✅ ML training DAG completes with model artifact stored on MinIO

---

## Dependency Matrix Between Squads

| Squad A needs from | Squad B needs from | Squad C needs from | Squad D needs from |
|---|---|---|---|
| D: K8s, Kafka, aml_core DB, Redis, CI/CD (Wk 4) | D: K8s, Kafka, CI/CD, MinIO (Wk 6) | D: K8s, Kafka, PG, Temporal, CI/CD (Wk 18) | N/A (foundation — no upstream) |
| B: wallet risk scores (Phase 2) | A: canonical schema, audit events | A: tme-engine alerts.generated topic (Wk 18) | Hardware vendor: K8s hardware |
| | A: sanctions hit results for scoring | A + B: sanctions + risk scores for case context | Facility: data centre colocation |
| | | A: ingestion API for hold/release | |

| Squad D produces for | Squad A produces for | Squad B produces for | Squad C produces for |
|---|---|---|---|
| A: K8s, Kafka topics, aml_core, Redis, CI/CD | D: service metrics, audit events | D: service metrics | D: service metrics, DAG triggers |
| B: K8s, Kafka topics, MinIO, CI/CD | B: canonical txn schema, audit events | A: wallet risk scores, customer risk scores | A: forensic events, hold/release callbacks |
| C: K8s, Kafka topics, PG (all), Temporal, CI/CD | C: alert generation (alerts.generated), sanction results, Travel Rule trigger | C: wallet risk for case context, customer risk for dashboard | |

---

## Interface Contracts Between Squads

These are the shared API/Kafka contracts that squads must agree on and not break. Each interface has a **single owning squad** (writes/produces) and one or more **consuming squads**.

| Interface | Owner | Consumers | Format | Stability |
|-----------|-------|-----------|--------|-----------|
| `fiat.normalised` topic | Squad A | Squad A (TME), Squad D (analytics) | JSON (canonical schema v1) | Breaking change requires 1 sprint notice |
| `onchain.normalised` topic | Squad B | Squad A (TME), Squad D (analytics) | JSON (canonical schema v1) | Breaking change requires 1 sprint notice |
| `screening.results` topic | Squad A | Squad A, Squad D | JSON: {txn_id, decision, score, rule_triggers[]} | Backward-compatible additions only |
| `alerts.generated` topic | Squad A | Squad C | JSON: {alert_id, txn_id, score, rules[], customer_id, timestamp} | Breaking change requires 2 sprint notice |
| `screening.requests` topic | Squad A | Squad A (sanctions) | JSON: {request_id, names[], wallets[], tx_ref} | Additive only |
| `travelrule.requests` topic | Squad A | Squad C | JSON: {txn_id, amount, currency, sender_wallet, beneficiary_wallet, chain_id} | Breaking = CID |
| `travelrule.results` topic | Squad C | Squad A | JSON: {status, reason, counterparty_vasp, timestamp} | Breaking = CID |
| `batch.alerts` topic | Squad C (batch) | Squad C (CMS) | JSON: {alert_id, run_id, txn_id, analysis_types[], batch_risk_score, priority, customer_id, scan_date} | Additive only |
| `batch.results` topic | Squad C (batch) | Squad C (dashboard), Squad D (analytics) | JSON: {run_id, scan_date, txns_processed, alerts_generated, analysis_breakdown, daily_briefing_path} | Additive only |
| `forensic.events` topic | All (publish) | Squad C (consume) | JSON: {event_category, operator_id, payload, client_ip, user_agent, session_id, justification} | All fields mandatory; breaking requires 1 sprint notice |
| `audit.events` topic | All (publish) | Squad A (consume) | JSON: {event_type, service, payload, timestamp} | Additive only |
| POST /screen | Squad A (owner) | Squad B (calls for scoring) | Request: {names[], wallets[]} Response: {results[{entity, confidence, list}]} | Contract via OpenAPI; breaking requires CID |
| POST /score | Squad B (owner) | Squad A (calls for TME) | Request: {wallets[]} Response: {results[{wallet, risk_score, tags}]} | Contract via OpenAPI; breaking requires CID |
| POST /decide | Squad A (owner) | Squad C (calls for hold/release) | Request: {txn_id, action: "HOLD"|"RELEASE"} Response: {status, timestamp} | Contract via OpenAPI |
| POST /cases/{id}/transitions | Squad C (owner) | Squad A/G (UI calls) | Request: {to_state, analyst_id, reason} Response: {success, new_state, timestamp} | Contract via OpenAPI |

---

## Shared Kubernetes Namespace Layout

```
ingestion/         → Squad A (ingestion-service)
monitoring/        → Squad A (tme-engine, tme-ml, sanctions-service)
analytics/         → Squad B (wallet-analytics-adapter, risk-scoring-service)
compliance/        → Squad C (travelrule-gateway, case-management-service, regulatory-reporting-service)
forensic/          → Squad C (forensic-audit-service)
portal/            → Squad C (aml-portal, api-gateway)
batch/             → Squad C (batch-scanning-service)
audit/             → Squad A (audit-service)
infra/             → Squad D (Kafka, Redis, PG operators, Temporal, Airflow)
```

**Network policies**: Each namespace has default-deny ingress/egress. Only explicitly whitelisted cross-namespace traffic is allowed (e.g., `monitoring/` → `audit/` for audit events). The `forensic/` namespace has additional isolation: no egress to internet, no ingress from anything except `compliance/` (for forensic.events consumer).
