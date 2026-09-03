# Project Overwatch — Detailed TODO Build List

## Parallel Build Streams

The build is organised into **8 parallel workstreams**. Each stream is an independently buildable unit with defined interfaces, dependencies, and acceptance criteria. Streams can run concurrently once platform dependencies are met. Dependency arrows (`→`) show required predecessor tasks.

---

## Stream A: Platform & Infrastructure Foundation

*Squad D — Weeks 0-4 (complete before other streams begin)*

### A.1 On-Prem Kubernetes Cluster
- [ ] **A.1.1** Provision 3 control-plane + 6 worker nodes (Ubuntu 24.04 LTS, 64GB/16vCPU per worker)
- [ ] **A.1.2** Install k3s or RKE2 with Calico CNI for network policy enforcement
- [ ] **A.1.3** Configure VLAN segmentation: DMZ, application, data, forensic, management
- [ ] **A.1.4** Deploy HAProxy (L4) + Nginx Ingress Controller (L7) with HSM-backed TLS termination
- [ ] **A.1.5** Set up Kubernetes NetworkPolicies (default-deny across namespaces)
- [ ] **A.1.6** Configure Prometheus + Grafana + Loki + Tempo monitoring stack (metrics 30d, logs 90d, traces 14d)
- [ ] **A.1.7** Configure backup: Velero for K8s resources, pgBackRest for PostgreSQL
- [ ] **A.1.8** Establish bastion/jumpbox with SSO + MFA
- **Acceptance**: `kubectl get nodes` shows all nodes Ready; ingress routes traffic; monitoring dashboards show cluster metrics

### A.2 Stateful Infrastructure Deployments
- [ ] **A.2.1** Deploy PostgreSQL operator (CloudNativePG or Zalando) — configure 3-node Patroni cluster for `aml_core`, 2-node for `aml_audit`
- [ ] **A.2.2** Deploy separate PostgreSQL 2-node WORM cluster for `aml_forensic` (physically separate VLAN, `chattr +i` on WAL, read-only replica)
- [ ] **A.2.3** Deploy Apache Kafka or Redpanda (3-broker cluster, 2TB NVMe per broker, 7-day retention default)
- [ ] **A.2.4** Deploy Redis (2-node active-passive, 32GB)
- [ ] **A.2.5** Deploy MinIO (4-node erasure coding, 8TB per node)
- [ ] **A.2.6** Deploy Temporal server (on-prem, SQLite or PostgreSQL persistence)
- [ ] **A.2.7** Deploy Keycloak (self-hosted) with LDAP integration; define RBAC roles: admin, analyst, manager, auditor, read-only
- **Acceptance**: All stateful services healthy; services reachable from within cluster; Keycloak login working with test users

### A.3 CI/CD & Developer Tooling
- [ ] **A.3.1** Deploy GitLab (self-hosted on-prem, S3-compatible backing for registry)
- [ ] **A.3.2** Deploy GitLab Runner (Kubernetes executor) — all builds within data centre
- [ ] **A.3.3** Set up GitLab Container Registry (on-prem)
- [ ] **A.3.4** Deploy ArgoCD with GitOps repository structure (one repo per environment: dev, staging, prod; Kustomize overlays)
- [ ] **A.3.5** Set up HashiCorp Vault for dynamic secrets (DB credentials, API keys)
- [ ] **A.3.6** Configure Sealed Secrets (Bitnami) for Git-encrypted K8s secrets
- [ ] **A.3.7** Create base Docker images (python:3.12-slim, node:20-alpine, golang:1.22-alpine) with security hardening
- [ ] **A.3.8** Scaffold CI pipeline templates for Python (lint→type→test→scan→build→push→integrate→deploy), TypeScript, Go
- [ ] **A.3.9** Set up Cosign for container image signing
- [ ] **A.3.10** Set up Trivy + Bandit + Semgrep for CI security scanning
- **Acceptance**: Developer pushes code → CI pipeline runs → image built, signed, pushed → ArgoCD deploys to dev → all in <15 minutes

### A.4 Security Foundation
- [ ] **A.4.1** Apply CIS benchmark to all OS and Kubernetes configurations
- [ ] **A.4.2** Configure HSM (Thales Luna or Azure Dedicated HSM) for root CA, TLS keys, encryption keys, TRP signing keys
- [ ] **A.4.3** Implement mTLS infrastructure (service mesh: Linkerd or Istio)
- [ ] **A.4.4** Configure WAF (ModSecurity) on API gateway
- [ ] **A.4.5** Set up automated vulnerability scanning schedule (weekly full scan, daily incremental)
- [ ] **A.4.6** Implement audit logging of all infrastructure-level changes
- **Acceptance**: CIS scan passes >90%; HSM functional with key rotation; WAF blocking test attacks

---

## Stream B: Core Data Layer

*Squad A + Squad D — Starts week 4, blocks all application services*

> **Data Model Reference:** The converged AML Data Model defines 27 core entities across 6 domains: Party & KYC (party, party_document, party_relationship, watchlist_entry), Account (account, account_party_link), Transaction & Screening (transaction, stablecoin_txn_detail, screening_result, travel_rule_record), AML Operations (detection_scenario, aml_alert, alert_transaction_link, aml_case, case_alert_link, case_party_link, case_activity_log, str_report, str_transaction_link), Graph & Analytics (graph_node, graph_edge, graph_community, graph_node_community, graph_analytics_run), and Batch & Governance (batch_job, batch_scan_run, batch_scan_result, batch_alert, batch_peer_group, batch_behavioral_baseline, kpi_snapshot, scenario_kpi, aml_user, audit_log). See Build Specification Section 4 for the complete entity reference.

### B.1 Database Schema — aml_core
- [ ] **B.1.1** Create party tables: `party`, `party_document`, `party_relationship` (UBO/director/shareholder links), `watchlist_entry` (sanctions + PEP master data)
- [ ] **B.1.2** Create account tables: `account` (unified fiat + stablecoin wallet), `account_party_link` (M:N with role qualifier: OWNER|JOINT_HOLDER|AUTHORISED_SIGNATORY|BENEFICIARY)
- [ ] **B.1.3** Create transaction tables: `transaction` (canonical schema — 22 fields covering both rails), `stablecoin_txn_detail` (on-chain metadata: tx hash, token standard, BA risk score/flags)
- [ ] **B.1.4** Create screening tables: `screening_result` (screen_type: SANCTIONS|PEP|ADVERSE_MEDIA|BLOCKCHAIN_RISK; screen_mode: REALTIME|BATCH), `travel_rule_record` (IVMS101 data, compliance_status, above_hkd8000_threshold)
- [ ] **B.1.5** Create detection & risk tables: `detection_scenario` (scenario_code, category, processing_mode: REALTIME|BATCH|BOTH, threshold_config JSONB, regulatory_reference)
- [ ] **B.1.6** Create alert tables: `aml_alert` (alert_type, alert_mode: REALTIME|BATCH, triggered_rule_detail JSONB), `alert_transaction_link` (M:N alert-to-transaction)
- [ ] **B.1.7** Create case tables: `aml_case` (case_type, ml_typology, SLA tracking), `case_alert_link`, `case_party_link` (party_role_in_case: SUBJECT|ASSOCIATE|COUNTERPARTY|FACILITATOR), `case_activity_log` (immutable analyst action log)
- [ ] **B.1.8** Create STR tables: `str_report` (JFIU STREAMS 2 reference, SAFE approach indicators, tipping_off_risk_assessed), `str_transaction_link`
- [ ] **B.1.9** Create graph tables (aml_graph schema): `graph_node`, `graph_edge`, `graph_community`, `graph_node_community`, `graph_analytics_run`
- [ ] **B.1.10** Create batch & governance tables: `batch_job` (job_type: T1_TM_RUN|T1_SCREENING|T1_KPI_CALC|T1_GRAPH_REFRESH), `batch_scan_run`, `batch_scan_result`, `batch_alert`, `batch_peer_group`, `batch_behavioral_baseline` (TimescaleDB hypertable)
- [ ] **B.1.11** Create KPI tables (aml_analytics): `kpi_snapshot` (HKMA-mandated metrics: false_positive_rate, str_conversion_rate, alert_rate_per_1000_customers, travel_rule_compliance_rate), `scenario_kpi` (per-scenario effectiveness with tuning_recommendation)
- [ ] **B.1.12** Create user & audit tables: `aml_user` (role: ANALYST_L1|ANALYST_L2|SUPERVISOR|MLRO|GRAPH_ANALYST|ADMIN), `audit_log` (aml_audit schema — append-only, all data mutations and sensitive reads)
- [ ] **B.1.13** Set up time-based partitioning for transaction and audit tables (monthly)
- [ ] **B.1.14** Create read-only application user roles; enforce INSERT-only for ingest paths
- [ ] **B.1.15** Implement PgBouncer connection pooling
- **Acceptance**: All 27 tables/entities created across aml_core, aml_audit, aml_graph, aml_analytics; migrations repeatable; rollback scripts exist; can INSERT 10K txns/min

### B.2 Database Schema — aml_audit
- [ ] **B.2.1** Create `audit_event` table with hash-chain verification columns: `event_id`, `event_type`, `payload` (jsonb), `prev_hash`, `record_hash`, `created_at`
- [ ] **B.2.2** Create `audit_hash_chain` table tracking chain heads
- [ ] **B.2.3** Enforce append-only: forensic DB user has INSERT + SELECT only; BEFORE UPDATE/DELETE triggers raise exceptions
- [ ] **B.2.4** Implement monthly time-partitioning on `audit_event`
- **Acceptance**: Audit DB accepts inserts; UPDATE/DELETE rejected; hash chain consistent

### B.3 Database Schema — aml_forensic (Tamper-Proof ForensicDB)
- [ ] **B.3.1** Create `forensic.chain_head` — global hash chain tracking table
- [ ] **B.3.2** Create `forensic.alert_disposition` — alert decisions with before/after state
- [ ] **B.3.3** Create `forensic.case_transition` — case state machine transitions with approval chain
- [ ] **B.3.4** Create `forensic.rule_change` — all rule/threshold changes with full JSON diff
- [ ] **B.3.5** Create `forensic.risk_override` — manual risk tier overrides with expiry
- [ ] **B.3.6** Create `forensic.sar_lifecycle` — SAR stages with full XML at each step
- [ ] **B.3.7** Create `forensic.access_log` — all access to sensitive customer data
- [ ] **B.3.8** Create `forensic.merkle_root` — published Merkle roots per table per hour
- [ ] **B.3.9** Create `forensic.external_witness` — external witness publication records
- [ ] **B.3.10** Enforce WORM: INSERT-only role, immutable file attributes, BEFORE UPDATE/DELETE triggers
- **Acceptance**: ForensicDB isolated on separate VLAN; all 9 tables created; write works; tamper attempts blocked

### B.4 Database Schema — aml_graph
- [ ] **B.4.1** Install Apache AGE extension
- [ ] **B.4.2** Create graph node types: `graph_node` (node_type: PARTY|ACCOUNT|TRANSACTION|IP_ADDRESS|DEVICE|BLOCKCHAIN_ADDRESS with source_entity_id FK and JSONB node_properties)
- [ ] **B.4.3** Create edge types: `graph_edge` (edge_type: SENT_TO|RECEIVED_FROM|OWNS_ACCOUNT|CONTROLS|SAME_IP|BLOCKCHAIN_TX with aggregated edge_weight, txn_count, total_amount_hkd)
- [ ] **B.4.4** Create community tables: `graph_community` (community_algorithm, community_risk_score, is_suspicious), `graph_node_community` (membership_score)
- [ ] **B.4.5** Create analytics tracking table: `graph_analytics_run` (algorithm_name, run_type: BATCH|INTERACTIVE, nodes_analysed, suspicious_clusters_found)
- [ ] **B.4.6** Set up graph-to-relational sync triggers for key entities
- **Acceptance**: AGE extension loaded; openCypher queries return expected results; graph readable alongside SQL

### B.5 Data Ingestion — Kafka Infrastructure
- [ ] **B.5.1** Deploy and configure all Kafka topics (see Section 3.1.2 of spec)
- [ ] **B.5.2** Configure topic retention, partitioning, replication factor, and cleanup policies
- [ ] **B.5.3** Set up Kafka monitoring: consumer lag, throughput, partition distribution
- [ ] **B.5.4** Set up TLS encryption for Kafka client-broker communication
- [ ] **B.5.5** Create idempotent consumer templates in Python
- **Acceptance**: All 11 topics created; messages published and consumed; consumer lag dashboard visible

### B.6 Canonical Transaction Schema Implementation
- [ ] **B.6.1** Define Pydantic models for canonical transaction (all 22 fields: txn_id through is_aml_processed)
- [ ] **B.6.2** Build fiat transaction normaliser (SWIFT MT/ISO 20022 → canonical)
- [ ] **B.6.3** Build on-chain transaction normaliser (Transfer event log → canonical + stablecoin_txn_detail extension)
- [ ] **B.6.4** Build FX conversion service for HKD-equivalent amounts
- [ ] **B.6.5** Implement schema validation with detailed error messages
- **Acceptance**: Fiat wire + stablecoin transfer both normalised to identical canonical schema; validation rejects malformed events

---

## Stream C: Transaction Monitoring Engine (TME)

*Squad A — Starts week 4 (depends on B.1, B.5, B.6)*

### C.1 tme-engine — Rule Processing Core
- [ ] **C.1.1** Build Kafka consumer for `fiat.normalised` and `onchain.normalised` topics
- [ ] **C.1.2** Implement in-memory sliding window per `customer_id` for velocity counting (5min, 1hr, 24hr windows)
- [ ] **C.1.3** Implement rule definition schema (YAML DSL) — fields: `id`, `name`, `category`, `condition` (Python expression), `score`, `enabled`, `tier_applies_to[]`
- [ ] **C.1.4** Build YAML rule parser with sandboxed Python expression engine
- [ ] **C.1.5** Build rule versioning: rule snapshots stored in PostgreSQL; hot-reload enabled
- [ ] **C.1.6** Implement tier gate logic (LOW → subset of rules; HIGH → all rules)
- [ ] **C.1.7** Implement parallel rule evaluation — asyncio.gather for all enabled rules per transaction
- [ ] **C.1.8** Implement composite score calculator (weighted: deterministic + ML)
- [ ] **C.1.9** Implement decision mapper: 0-30 auto-approve, 31-65 flag, 66-100 block
- [ ] **C.1.10** Publish decisions to `screening.results` topic; if flagged, publish to `alerts.generated`
- [ ] **C.1.11** Build POST /decide endpoint (sync, for fiat pre-settlement calls)
- [ ] **C.1.12** Build POST /decide/batch endpoint (async batch screening)
- **Acceptance**: 100 fiat txns/sec processed through full pipeline; rule changes hot-reloaded without restart; p95 latency <500ms

### C.2 Rule Library (Initial Set)
- [ ] **C.2.1** Velocity rule: >5 txns to same address within 1 hour
- [ ] **C.2.2** Velocity rule: >HKD 500K cumulative daily outflow
- [ ] **C.2.3** Threshold rule: single transfer >HKD 1M
- [ ] **C.2.4** Threshold rule: stablecoin transfer >500,000 USDC
- [ ] **C.2.5** Counterparty rule: transaction to/from high-risk jurisdiction
- [ ] **C.2.6** Counterparty rule: transaction to/from unhosted wallet above threshold
- [ ] **C.2.7** Pattern rule: round-dollar amounts in stablecoin transfers
- [ ] **C.2.8** Pattern rule: structuring detection — multiple transfers just under HKD 8,000
- [ ] **C.2.9** Geographic rule: IP/session origin mismatch
- **Acceptance**: All 9 rules functional in test harness; each produces correct alert/score for known test inputs

### C.3 tme-ml — ML Inference Service
- [ ] **C.3.1** Set up ONNX runtime inference server (Python FastAPI)
- [ ] **C.3.2** Build feature engineering pipeline: log(amount), frequency features (last hr/day/week), z-score baseline, wallet risk score, counterparty risk, jurisdiction pair risk, time-of-day, day-of-week
- [ ] **C.3.3** Train initial XGBoost classifier on synthetic/industry-benchmark data
- [ ] **C.3.4** Implement SHAP explanation value generation per prediction
- [ ] **C.3.5** Implement shadow-mode: model produces score but does not influence decision; logs predictions vs actual outcomes
- [ ] **C.3.6** Package model artifacts (versioned) and store on MinIO
- [ ] **C.3.7** Implement model loading pipeline: latest approved model loaded on service start
- **Acceptance**: Inference service returns probability [0,1] + SHAP values in <100ms; shadow-mode logs without affecting decisions

---

## Stream D: Sanctions & Risk Scoring

*Squad A + Squad B — Starts week 6 (depends on B.1, B.5)*

### D.1 sanctions-service
- [ ] **D.1.1** Build symmetric endpoint: POST /screen (name + address for text matching)
- [ ] **D.1.2** Build wallet screening endpoint: POST /screen/wallet (wallet hash exact-match)
- [ ] **D.1.3** Implement fuzzy name matching using rapidfuzz — Levenshtein distance, token-set ratio, Soundex
- [ ] **D.1.4** Load initial OFAC SDN list into in-memory hash map (wallet addresses for sub-ms lookup)
- [ ] **D.1.5** Build batch consumer for `screening.requests` topic
- [ ] **D.1.6** Implement daily SFTP pull from sanctions provider; diff detection against previous version
- [ ] **D.1.7** Implement confidence scoring: 0-100 scale; >=80 = block; 60-79 = review
- [ ] **D.1.8** Build batch re-screening trigger: re-screen all parties within 24h of list update
- [ ] **D.1.9** Publish screening results to `screening.results` topic
- **Acceptance**: OFAC SDN loaded; fuzzy match on John Smith vs Jon Smith = match >80%; wallet exact match <1ms; batch re-screening of 10K records <5 min

### D.2 risk-scoring-service
- [ ] **D.2.1** Build FastAPI service with PostgreSQL persistence
- [ ] **D.2.2** Implement scoring factors: velocity deviation, wallet risk, counterparty risk, sanctions hit count, PEP flags, adverse media recency, jurisdiction risk, source-of-funds consistency
- [ ] **D.2.3** Build POST /score/transaction endpoint — returns risk score contribution for a single txn
- [ ] **D.2.4** Build GET /customer/{id}/risk-profile — returns current tier, score, factor breakdown
- [ ] **D.2.5** Implement re-scoring triggers: new txn processed; sanctions list update; PEP DB update; manual re-score request
- [ ] **D.2.6** Implement risk tier escalation logic: consecutive high-risk events trigger automatic tier upgrade
- [ ] **D.2.7** Build scheduled re-assessment for time-decaying risk factors
- **Acceptance**: Customer risk score updates within 30s of new transaction; tier escalation functional; manual re-score completes <2s

---

## Stream E: Blockchain Analytics & Indexing

*Squad B — Starts week 8 (depends on A.1, B.5)*

### E.1 blockchain-indexer (Go)
- [ ] **E.1.1** Set up Go project with per-chain worker goroutine pattern
- [ ] **E.1.2** Ethereum indexer: connect to archive node; poll Transfer events on AnchorPoint + USDC contracts; configurable confirmation depth (12 blocks)
- [ ] **E.1.3** Polygon indexer: RPC connection; event polling; maps to canonical schema
- [ ] **E.1.4** Arbitrum indexer: RPC connection; event polling; maps to canonical schema
- [ ] **E.1.5** Optimism indexer: RPC connection; event polling; maps to canonical schema
- [ ] **E.1.6** Base indexer: RPC connection; event polling; maps to canonical schema
- [ ] **E.1.7** Solana indexer: RPC connection or geyser plugin; SPL token transfer streaming
- [ ] **E.1.8** Implement programmable event filters per chain (contract addresses, wallet addresses)
- [ ] **E.1.9** Implement backfill support: re-index from configurable historical block height
- [ ] **E.1.10** Publish enriched transactions to `onchain.raw` topic (JSON: chain_id, tx_hash, block, from, to, value, token_address, timestamp)
- [ ] **E.1.11** Implement per-chain health monitoring + auto-restart on disconnect
- [ ] **E.1.12** Graceful shutdown + state persistence for resumption after restart
- **Acceptance**: All 6 chains indexed within 30s of block finality; backfill 1M blocks works; single chain failure doesn't affect others

### E.2 wallet-analytics-adapter
- [ ] **E.2.1** Build abstracted vendor interface: common output schema for TRM Labs, Chainalysis KYT, Elliptic
- [ ] **E.2.2** Implement TRM Labs adapter (primary vendor)
- [ ] **E.2.3** Implement Chainalysis adapter (fallback vendor)
- [ ] **E.2.4** Implement Redis caching: 24h TTL for static scores, 1h for dynamic scores
- [ ] **E.2.5** Build POST /score endpoint: accepts wallet addresses, returns risk scores
- [ ] **E.2.6** Implement n-hop chain analysis (1-3 hops configurable)
- [ ] **E.2.7** Implement vendor rate limiting: per-vendor token bucket; circuit breaker on >5 failures/min
- [ ] **E.2.8** Build GET /cache/status endpoint — cache hit rate, expiry counts, vendor health
- **Acceptance**: Wallet scoring for 100 addresses completes <30s; cache hit rate >90% after warmup; circuit breaker opens on vendor failure

---

## Stream F: Compliance Workflows

*Squad C — Starts week 18 (depends on C.1, D.1, D.2)*

### F.1 travelrule-gateway
- [ ] **F.1.1** Build Temporal workflow worker (Python SDK)
- [ ] **F.1.2** Build consumer for `travelrule.requests` topic (triggered when TME detects >= HKD 8,000 transfer)
- [ ] **F.1.3** Implement Notabene integration: counterparty discovery API, TRP message construction, message send, response await
- [ ] **F.1.4** Implement 5-minute timeout: if no response within 5 min → hold transaction, flag for manual review
- [ ] **F.1.5** Implement unhosted wallet path: if beneficiary VASP not found → enhanced monitoring, paired fiat account risk check
- [ ] **F.1.6** Implement TravelRuleWorkflow Temporal workflow with retries, compensation, and timeout
- [ ] **F.1.7** Publish results to `travelrule.results` topic
- **Acceptance**: Travel Rule message sent for USDC transfer >=HKD 8,000; response received; unhosted wallet path triggers EDD

### F.2 case-management-service
- [ ] **F.2.1** Build consumer for `alerts.generated` topic
- [ ] **F.2.2** Implement alert lifecycle state machine (Temporal workflow): NEW → ASSIGNED → UNDER_INVESTIGATION → CLOSED_FP | CLOSED_MONITORING | SAR_FILED
- [ ] **F.2.3** Build AlertAssignmentWorkflow: round-robin assign, notify, escalate if unassigned >1hr
- [ ] **F.2.4** Build InvestigationWorkflow: hold active transaction, gather evidence, additional blockchain queries, document findings (4hr SLA)
- [ ] **F.2.5** Build SARApprovalWorkflow: peer review → manager approval → compliance officer sign-off → file to JFIU (24hr SLA)
- [ ] **F.2.6** Build EscalationWorkflow: high-risk alert unactioned >1hr → notify team lead → compliance manager → MLRO
- [ ] **F.2.7** Build REST API: GET /alerts (paginated, filterable), POST /cases, POST /cases/{id}/transitions
- [ ] **F.2.8** Implement investigation workspace: transaction timeline, network graph data, customer profile, note/evidence management
- [ ] **F.2.9** Implement evidence upload service (stores on MinIO, hashes stored in case record)
- [ ] **F.2.10** Implement read-only audit replica for auditor access
- **Acceptance**: All 4 workflows operational; alert → case → investigation → SAR lifecycle completed end-to-end

### F.3 regulatory-reporting-service
- [ ] **F.3.1** Build SAR pre-population engine — maps case data to JFIU-compatible STR form XML
- [ ] **F.3.2** Implement SAR draft → review → approve → file workflow
- [ ] **F.3.3** Build HKMA statistical return generator (monthly/quarterly AML reports)
- [ ] **F.3.4** Implement STREAMS 2 filing integration (web portal assisted upload; future SFTP XML)
- [ ] **F.3.5** Build Airflow DAGs for scheduled report generation and distribution
- **Acceptance**: SAR XML generated from case data; report DAGs functional; JFIU submission simulated end-to-end

### F.4 forensic-audit-service
- [ ] **F.4.1** Build consumer for `forensic.events` topic (partitioned by event_category)
- [ ] **F.4.2** Implement ForensicDB writer — sole writer; rejects events missing required fields (operator_id, session_id, client_ip, user_agent, justification)
- [ ] **F.4.3** Implement record-level SHA-256 hashing: SHA-256(record_type, payload, operator_id, timestamp, prev_record_hash)
- [ ] **F.4.4** Implement per-table Merkle tree computation (balanced tree per event category)
- [ ] **F.4.5** Implement global hash chain: chain_n = SHA-256(chain_n-1, table_name, record_hash, timestamp)
- [ ] **F.4.6** Build forensic-verifier CLI — recomputes all hashes from genesis; outputs tamper report
- [ ] **F.4.7** Build scheduled verifier (15-min interval on read-only replica); P0 alert on chain break
- [ ] **F.4.8** Build REST API: GET /forensic/records (date range, category), GET /forensic/chain/verify
- [ ] **F.4.9** Implement external witness publisher — hourly Merkle root hash to Polygon/Bitcoin testnet
- [ ] **F.4.10** Implement daily attestation store — signed attestation uploaded to cloud immutable store
- [ ] **F.4.11** Implement retention manager — archive records >7 years to WORM optical media; verify export hash; log chain-of-custody
- **Acceptance**: ForensicDB accepts forensic events; hash chain verifiable; verifier detects tampered records; external witness tx published

---

## Stream G: AML Admin Portal (Frontend)

*Squad C — Starts week 20 (depends on F.2 API availability)*

### G.1 Portal Foundation
- [ ] **G.1.1** Scaffold Next.js 14+ App Router project with TypeScript
- [ ] **G.1.2** Configure shadcn/ui component library (Radix primitives + Tailwind CSS)
- [ ] **G.1.3** Set up React Query for server state, Zustand for client state
- [ ] **G.1.4** Set up Keycloak integration: OIDC authentication flow, token refresh, role-based route guards
- [ ] **G.1.5** Build layout shell: sidebar navigation, top bar, user menu, notification badge
- **Acceptance**: Portal loads; Keycloak login works; RBAC routes protected

### G.2 Module 1 — KPI Dashboard
- [ ] **G.2.1** Build alert volume chart (total, by rule, by risk tier, by channel) with Recharts
- [ ] **G.2.2** Build alert-to-case conversion rate trend line
- [ ] **G.2.3** Build false-positive rate gauge + trend line
- [ ] **G.2.4** Build SAR filing volume and status breakdown
- [ ] **G.2.5** Build average case resolution time chart
- [ ] **G.2.6** Build queue backlog count + aging distribution chart
- [ ] **G.2.7** Build SLA compliance percentage per investigator/team
- [ ] **G.2.8** Build customer risk tier breakdown (donut chart: low/med/high/PEP/sanctioned)
- [ ] **G.2.9** Implement configurable date-range filter (presets: 24h, 7d, 30d, 90d, custom)
- [ ] **G.2.10** Implement dashboard export (PDF download)
- **Acceptance**: All 8 KPIs rendered with live data; date filter functional; export produces valid PDF

### G.3 Module 2 — Alert Queue & Detail
- [ ] **G.3.1** Build /alerts page: paginated, filterable (by risk tier, rule, status, date range), sortable table
- [ ] **G.3.2** Build /alerts/[id] detail page: linked transactions, triggered rules, risk score breakdown
- [ ] **G.3.3** Build customer 360 summary panel (risk tier, recent activity, linked wallets, PEP status)
- [ ] **G.3.4** Build wallet risk summary (risk score, tags, high-risk interactions, chain analysis summary)
- **Acceptance**: 10K alerts in queue renders <3s; click-through to detail shows all linked data

### G.4 Module 3 — Case Management
- [ ] **G.4.1** Build /cases page: case list with status, priority, assignee; bulk assignment; export CSV
- [ ] **G.4.2** Build /cases/[id] investigation workspace: transaction timeline, network graph, customer profile
- [ ] **G.4.3** Build note system per case (create, edit, read-only after edit)
- [ ] **G.4.4** Build evidence upload widget (drag-and-drop; max 20MB per file; virus scan integration)
- [ ] **G.4.5** Build SAR draft workspace: populates form from case data, edit, preview, submit
- [ ] **G.4.6** Build network graph visualisation with Cytoscape.js (transaction flow, wallet cluster)
- [ ] **G.4.7** Implement SAR approval workflow UI (submit → peer review → manager → compliance officer → file)
- [ ] **G.4.8** Build audit trail timeline within case view
- **Acceptance**: Full L1/L2/L3 swimlane functional; network graph renders; note system immutable after save

### G.5 Module 4 — Configuration & Administration
- [ ] **G.5.1** Build /config/rules page: view rules, enable/disable, shadow-mode toggle, version history
- [ ] **G.5.2** Build /config/thresholds page: per-tier and per-jurisdiction threshold management
- [ ] **G.5.3** Build /admin/users page: Keycloak-mediated provisioning, role assignment
- [ ] **G.5.4** Build /audit/logs page: audit log search, filter by event type/date/user, export
- [ ] **G.5.5** Build /forensic/verify page: hash-chain verification UI for auditors (paste chain head, verify)
- **Acceptance**: Rules can be enabled/disabled without deployment; audit log search <3s; forensic verify returns pass/fail with details

### G.6 Module 5 — Reporting
- [ ] **G.6.1** Build /reports page: SAR generation, HKMA return templates, scheduled report config
- [ ] **G.6.2** Build SAR preview + edit before submission
- [ ] **G.6.3** Build report scheduling UI (Airflow DAG trigger config)
- **Acceptance**: SAR generated from case data; schedule set/change/delete works

---

## Stream H: Integration, Testing & Security

*Running squad — Starts week 6, continues through all phases*

### H.1 API Integration (Payment Platform ↔ AML Gateway)
- [ ] **H.1.1** Implement POST /api/v1/transactions/screen — synchronous pre-settlement screening
- [ ] **H.1.2** Implement POST /api/v1/transactions/batch-screen — async batch screening
- [ ] **H.1.3** Implement POST /api/v1/wallets/screen — wallet risk scoring
- [ ] **H.1.4** Implement GET /api/v1/transactions/{ref} — retrieve screening detail
- [ ] **H.1.5** Implement GET /api/v1/health — health check
- [ ] **H.1.6** Implement GET /api/v1/forensic/verify — public chain verification
- [ ] **H.1.7** Generate OpenAPI 3.1 specification; host on Swagger UI
- [ ] **H.1.8** Implement consumer-driven contract tests (Pact)
- **Acceptance**: All endpoints functional; OpenAPI spec complete; contract tests pass

### H.2 External Vendor Integrations
- [ ] **H.2.1** TRM Labs API onboarding and integration (Phase 2)
- [ ] **H.2.2** Chainalysis KYT API onboarding (fallback — Phase 2)
- [ ] **H.2.3** Notabene TRP onboarding and integration (Phase 3)
- [ ] **H.2.4** LexisNexis World-Check sanctions feed (SFTP + REST) — Phase 1
- [ ] **H.2.5** Onfido/Jumio KYC integration (consumed from existing payment platform — Phase 1)
- [ ] **H.2.6** JFIU STREAMS 2 filing portal onboarding (Phase 4)
- **Acceptance**: Each vendor integration functional in staging; DPA executed; data flow tested

### H.3 Testing Campaigns
- [ ] **H.3.1** Unit tests: >85% line coverage across all services
- [ ] **H.3.2** Integration tests: service-to-service, Kafka, DB (testcontainers)
- [ ] **H.3.3** Contract tests: Pact for all producer-consumer boundaries
- [ ] **H.3.4** End-to-end tests: top 20 transaction scenarios (see Section 11.2 of spec)
- [ ] **H.3.5** Regulatory scenario tests: 8 documented HKMA/FATF scenarios
- [ ] **H.3.6** Forensic integrity tests: tamper simulation — verify detection
- [ ] **H.3.7** Load tests: 500 TPS sustained; p95 <500ms
- [ ] **H.3.8** Chaos tests: single-node failure, network partition, Kafka broker loss
- [ ] **H.3.9** Security tests: SAST (Bandit), container scan (Trivy), dependency scan, DAST (ZAP)
- **Acceptance**: All test campaigns pass; load test at 2x peak passes; chaos test shows no data loss

### H.4 Security Hardening
- [ ] **H.4.1** Full penetration test by external firm
- [ ] **H.4.2** Remediate all critical/high findings
- [ ] **H.4.3** CIS benchmark validation on all nodes and containers
- [ ] **H.4.4** Implement rate limiting (100 req/s per API key)
- [ ] **H.4.5** Verify mTLS is enforced across all inter-service communication
- [ ] **H.4.6** Verify WORM enforcement on ForensicDB (attempt direct modification)
- [ ] **H.4.7** Regulatory documentation pack: AML policy, system description, model governance, control evidence
- **Acceptance**: Pentest passed; CIS >90%; WORM verified; documentation pack complete

## Stream I: T+1 Batch Transaction Scanning (Next-Day Batch Analysis)

*Squad A + Squad C + Squad D — Starts week 30 (depends on C.1, B.5, D.1, Airflow D.DP)*

### I.1 batch-scanning-service — Core Service & Airflow DAGs
- [ ] **I.1.1** Design and deploy Airflow DAG `t1_batch_scan_pipeline` — scheduled daily at 02:00 HKT; orchestrates 8-stage pipeline: Pre-flight Sensor → Data Extraction → Enrichment → Parallel Analysis → ML Scoring → Alert Generation → Daily Briefing → Feedback Loop
- [ ] **I.1.2** Build Pre-flight Sensor: poll ingestion-service health + blockchain-indexer lag metrics; verify all chains have finality for previous day; wait timeout 30 min; fail DAG if pre-flight conditions not met
- [ ] **I.1.3** Build Data Extraction stage: pull all canonical_transaction records for target date (00:00-23:59 HKT) from aml_core; export to Parquet files on MinIO (batch-data bucket); include real-time TME decisions, scores, and rule triggers for comparison
- [ ] **I.1.4** Build Enrichment stage: augment each transaction with full customer profile (risk tier, PEP status, account age, declared income), refreshed wallet analytics scores, peer group assignment, and real-time TME decision metadata
- [ ] **I.1.5** Build Parallel Analysis Dispatcher: launch Kubernetes Jobs per analysis type (10 analyses, each as separate K8s Job with configurable resource limits); collect results via shared results table in TimescaleDB
- **Acceptance**: DAG triggers daily; extracts 500K txns in <30 min; Parquet files written to MinIO with correct schema

### I.2 Batch-Only Analyses (10 Analysis Modules, Parallel K8s Jobs)
- [ ] **I.2.1** Full-Day Customer Behavioral Baselining: compute per-customer daily statistics (total volume, txn count, avg amount, beneficiary diversity, time-of-day distribution, rail mix ratio); compare against 30/90-day historical baseline via TimescaleDB queries; flag customers with >3 sigma deviation from baseline; output behavioral deviation scores
- [ ] **I.2.2** Peer Group Comparative Analysis: assign customers to peer groups (by segment, jurisdiction, declared income band, product usage); compute group-level statistics (median, IQR, standard deviation); flag customers deviating significantly from peer group; store peer group baselines in batch_peer_group table (recomputed monthly)
- [ ] **I.2.3** Multi-Account Structuring Detection: traverse party graph (Apache AGE) to identify linked accounts/parties; aggregate daily outflow across linked accounts; detect patterns where combined outflow exceeds thresholds while individual accounts stay below; generate structuring cluster alerts with linked account details
- [ ] **I.2.4** Velocity Pattern Mining (Multi-Day Windows): pull 7-day txn history per customer from TimescaleDB; apply time-series decomposition (trend + seasonal + residual); detect ramping (increasing amounts over 3-5 days), burst-and-pause (high activity then dormancy), cyclical patterns; classify pattern type and output alerts
- [ ] **I.2.5** Network Graph Anomaly Detection: build full daily transaction graph in Apache AGE (nodes: parties/wallets, edges: transfers); run PageRank for influence scoring; run Louvain community detection for cluster identification; detect outlier edges (amount or frequency anomalies); compare against historical graph baseline snapshots; output graph anomaly scores + community change alerts
- [ ] **I.2.6** Ensemble ML Scoring (Full Feature Set): load production XGBoost ensemble model from MinIO; compute full feature vectors (full-day behavioral + peer group + graph centrality + temporal pattern + cross-rail interaction features); run batch inference on complete daily dataset; generate risk scores with SHAP explanations per transaction; store results in TimescaleDB
- [ ] **I.2.7** Rule Effectiveness Retrospective: for each real-time rule, compute alert rate, false positive rate (based on analyst disposition feedback from ForensicDB), detection overlap with batch analyses; identify transactions that WOULD have been flagged under adjusted thresholds; generate rule tuning recommendations as structured JSON feedback
- [ ] **I.2.8** Cross-Rail Layering Detection (Full Fund Flow): reconstruct complete fiat-to-stablecoin-to-fiat fund flows across the entire day; detect multi-hop layering: fiat deposit → crypto purchase → unhosted wallet → exchange → fiat withdrawal; build full fund flow trail visualization data (nodes + edges for Cytoscape.js); output layering alerts with trail data
- [ ] **I.2.9** Sanctions/Screening Retrospective: re-screen all daily transactions against the latest sanctions list version; detect transactions that passed screening on a stale mid-day list version; flag transactions involving entities added to sanctions lists on the same day; generate retrospective screening alerts
- [ ] **I.2.10** SAR Pre-Population Intelligence: for high-confidence batch findings (risk score >70), pre-compute SAR-relevant data: transaction timeline, counterparty details, fund flow summary, risk factor breakdown; pre-populate SAR draft XML; store as draft in case record for analyst review; link to batch alert
- **Acceptance**: All 10 analyses execute in parallel <20 min each; behavioral baseline deviation detection catches >3 sigma anomalies; multi-account structuring catches 3+ linked accounts; ensemble ML scores all txns; layering detection reconstructs full 4-hop flows

### I.3 Batch Alert Generation & CMS Integration
- [ ] **I.3.1** Build Batch Alert Generator: aggregate findings from all 10 analyses; deduplicate (same txn flagged by multiple analyses → single alert with all trigger reasons); assign composite batch risk score; set alert priority (LOW/MEDIUM/HIGH based on confidence and severity)
- [ ] **I.3.2** Implement Kafka producer for batch.alerts topic (6 partitions, keyed by customer_id, 90-day retention)
- [ ] **I.3.3** Implement batch alerts to CMS integration: create cases with source=BATCH_SCAN; set priority=LOW by default (lower urgency than real-time alerts); enrich case with batch analysis context and pre-populated SAR drafts
- [ ] **I.3.4** Publish all batch alert dispositions and analysis findings to forensic.events for tamper-proof audit trail
- [ ] **I.3.5** Build POST /api/v1/batch/scan/trigger endpoint (manual ad-hoc trigger); GET /api/v1/batch/scan/{run_id}/status; GET /api/v1/batch/scan/{run_id}/results
- [ ] **I.3.6** Build GET /api/v1/batch/scan/daily-briefing/{date} — returns generated Daily AML Briefing report (PDF from MinIO)
- **Acceptance**: Batch alerts generated and delivered to CMS within 4-hour window; idempotent (re-running same date overwrites previous results); manual trigger works for ad-hoc analysis

### I.4 Daily AML Briefing & Reporting
- [ ] **I.4.1** Build Daily AML Briefing generator: compile top 10 riskiest transactions, peer group anomaly summary, rule effectiveness metrics (real-time vs batch detection comparison), false positive trends, new pattern detection summary, SAR pre-population queue; render as PDF with tables and charts
- [ ] **I.4.2** Store Daily Briefing PDF on MinIO (daily-briefings bucket, 90-day retention); generate email notification to compliance team with summary and link
- [ ] **I.4.3** Build /batch-scan page in AML Admin Portal: batch run history table (date, status, duration, alerts generated, top findings); drill-down to individual run results; ad-hoc trigger button; daily briefing viewer
- [ ] **I.4.4** Build "Real-Time vs Batch Detection Comparison" dashboard widget: Venn diagram showing alerts detected by each system; table of discrepancies (txns flagged by batch but missed by real-time, and vice versa)
- [ ] **I.4.5** Build "Rule Effectiveness" dashboard widget: per-rule false positive rate trends sourced from batch retrospective analysis; threshold tuning suggestions with expected impact
- **Acceptance**: Daily briefing generated within <5 min after batch scan completes; portal page renders run history <3s; comparison widget shows actionable discrepancies

### I.5 Database Schema (Batch-Specific Tables)
- [ ] **I.5.1** Create batch_scan_run table: run_id (UUID PK), scan_date (DATE), status (PENDING/RUNNING/COMPLETED/FAILED), started_at, completed_at, txns_processed, alerts_generated, analysis_results (JSONB), error_log (TEXT)
- [ ] **I.5.2** Create batch_scan_result table: result_id (UUID PK), run_id (FK), transaction_id, analysis_type, anomaly_score, findings (JSONB), alert_generated (BOOL), created_at; index on (run_id, transaction_id)
- [ ] **I.5.3** Create batch_alert table: alert_id (UUID PK), run_id (FK), transaction_id, analysis_type, risk_score, alert_reason (TEXT), priority (LOW/MEDIUM/HIGH), status, case_id (FK nullable), created_at
- [ ] **I.5.4** Create batch_peer_group table: group_id (UUID PK), group_name, segment, jurisdiction, income_band, product_usage, member_count, median_daily_volume, iqr_low, iqr_high, updated_at
- [ ] **I.5.5** Create batch_behavioral_baseline table: customer_id (FK), baseline_date, total_volume_30d, avg_txn_amount_30d, txn_count_30d, beneficiary_diversity_30d, rail_mix_ratio_30d, stddev_volume, updated_at; TimescaleDB hypertable with 90-day chunk intervals
- [ ] **I.5.6** Create Kafka topics: batch.scan.commands (3 partitions, 7d retention), batch.scan.progress (3 partitions, 7d), batch.alerts (6 partitions, 90d), batch.results (6 partitions, 365d)
- **Acceptance**: All 5 tables created in aml_core; TimescaleDB hypertable functional for behavioral baselines; 4 Kafka topics created and verified

### I.6 Batch Pipeline Testing
- [ ] **I.6.1** Build end-to-end batch pipeline test: seed 100K transactions for a test date → trigger batch scan → verify all 10 analyses complete → verify alerts generated → verify daily briefing rendered → verify idempotency (re-run same date, confirm results overwrite not duplicate)
- [ ] **I.6.2** Build batch analysis unit tests: each of 10 analyses tested with known input/output pairs; behavioral baseline test with controlled deviation; peer group comparison test with outlier injection; multi-account structuring test with 5 linked accounts
- [ ] **I.6.3** Build batch pipeline failure test: inject failure at each stage (pre-flight timeout, extraction failure, analysis job crash); verify DAG retry, partial rollback, and alert on failure
- [ ] **I.6.4** Build batch pipeline performance test: 500K transactions processed within 4-hour SLA window; verify parallel job execution; verify memory/CPU limits enforced
- **Acceptance**: End-to-end test passes with seed data; failure recovery works; performance test meets 4-hour SLA

---

## Dependency Map (Parallel Stream Execution)

```
Week 0    4     8     12    16    20    24    28    32    36    40    44    48    52
│         │     │     │     │     │     │     │     │     │     │     │     │     │
A         ├─────┘     │     │     │     │     │     │     │     │     │     │     │
Platform  │           │     │     │     │     │     │     │     │     │     │     │
          │           │     │     │     │     │     │     │     │     │     │     │
B         └─────┬─────┘     │     │     │     │     │     │     │     │     │     │
Data Layer      │           │     │     │     │     │     │     │     │     │     │
                │           │     │     │     │     │     │     │     │     │     │
C ──────────────┼─────┐     │     │     │     │     │     │     │     │     │     │
TME             │     │     │     │     │     │     │     │     │     │     │     │
                │     │     │     │     │     │     │     │     │     │     │     │
D ──────────────┼─────┼─────┘     │     │     │     │     │     │     │     │     │
Sanctions+Risk  │     │           │     │     │     │     │     │     │     │     │
                │     │           │     │     │     │     │     │     │     │     │
E ──────────────┼─────┼─────┬─────┘     │     │     │     │     │     │     │     │
Blockchain      │     │     │           │     │     │     │     │     │     │     │
                │     │     │           │     │     │     │     │     │     │     │
F ──────────────┼─────┼─────┼───────────┼─────┘     │     │     │     │     │     │
Compliance WF   │     │     │           │           │     │     │     │     │     │
                │     │     │           │           │     │     │     │     │     │
G ──────────────┼─────┼─────┼───────────┼───────────┘     │     │     │     │     │
Portal (FE)     │     │     │           │                 │     │     │     │     │
                │     │     │           │                 │     │     │     │     │
H ──────────────┼─────┼─────┼───────────┼─────────────────┼─────┘     │     │     │
Integration     │     │     │           │                 │           │     │     │
                │     │     │           │                 │           │     │     │
                │     │     │           │                 │           │     │     │
────────────────┴─────┴─────┴───────────┴─────────────────┴───────────┴─────┴─────┴──
Phase1         Phase2               Phase3               Phase4        Phase5
```

**Key dependency rules:**
- Stream B (data layer) must be complete before C, D, E can write
- Stream A (platform) must be complete before B can deploy stateful services
- Stream C (TME) must be complete before F (compliance workflows) can consume alerts
- Stream F (compliance API) must be complete before G (frontend) can render
- Stream H runs continuously from week 6 — vendors are integrated as dependent streams reach their phases

**Blocking paths:**
- `A → B → C → F → G` (critical path — longest chain)
- `A → B → D` (shortest path — sanctions can be tested earlier)
- `A → B → E` (independent — blockchain indexing doesn't need TME)
- `A → F.4` (forensic service — needs infrastructure but not TME, can start earlier)
