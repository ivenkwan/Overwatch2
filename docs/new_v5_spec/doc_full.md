**Project Overwatch\
Build Specification & Engineering Plan**

Unified AML Transaction Monitoring Platform\
Consolidated Fiat & Regulated Stablecoin Transactions\
\
AnchorPoint (SCB x HKT x Animoca Brands JV) \| USDC\
Hong Kong Payments / Remittance Platform

Document Version: 2.0\
Date: 03 July 2026\
Classification: Confidential - Project Overwatch

Table of Contents
=================

1\. Build Overview & Scope

2\. System Context & Interfaces

3\. Module Decomposition & Responsibilities

3.1 Ingestion Layer \| 3.2 TME \| 3.3 Sanctions \| 3.4 Blockchain
Indexer

3.5 Travel Rule \| 3.6 Risk Scoring \| 3.7 Case Management \| 3.8 Admin
Portal

3.9 Regulatory Reporting \| 3.10 Audit Trail \| 3.11 Tamper-Proof
Forensic Audit Ledger

4\. Data Architecture & Storage

5\. API Contracts & Service Interfaces

6\. Infrastructure & Deployment (On-Prem / Hybrid)

7\. CI/CD Pipeline & DevSecOps

8\. Build Phases & Milestones (52-Week Roadmap)

9\. Team Structure & Sizing

10\. Vendor Integration Matrix

11\. Testing Strategy

12\. Security Architecture

13\. Performance & Scalability Requirements

Appendix A: Technology Stack Reference

Appendix B: Glossary of Terms

1. Build Overview & Scope
=========================

1.1 Purpose
-----------

This Build Specification translates the Project Overwatch requirements
into an actionable engineering blueprint. It defines system
architecture, module boundaries, data contracts, infrastructure
topology, CI/CD pipelines, testing strategy, phased delivery plan, and
team sizing required to build the unified AML transaction monitoring
platform. Audience: Engineering leads, architects, platform engineers,
QA leads, and delivery managers.

1.2 What We Are Building
------------------------

A unified, real-time AML transaction monitoring platform applying
consistent compliance controls across fiat payment rails and regulated
stablecoin (AnchorPoint HKDR and USDC) on-chain transfers. Serves a Hong
Kong-based payments/remittance platform distributing AnchorPoint (SCB x
HKT x Animoca Brands JV) and USDC across EVM chains and Solana.

1.3 Scope Boundaries
--------------------

  **In Scope**                                                       **Out of Scope (Future / Adjacent)**
  ------------------------------------------------------------------ ---------------------------------------------------------------------
  Transaction Monitoring Engine with configurable rules              KYC/KYB identity verification (consumed from existing provider)
  Real-time sanctions screening (OFAC, UN, EU, HK, custom lists)     Customer-facing onboarding portal or mobile app
  Blockchain indexer for EVM + Solana (AnchorPoint + USDC)           Core banking / ledger transaction processing
  Wallet screening via blockchain analytics vendor API               Smart-contract-level compliance controls (Phase 5 R&D)
  Travel Rule messaging via TRP protocol                             Full graph analytics and entity relationship detection (Phase 4)
  Case management system with alert investigation workflow           Direct integration with all global regulatory filing portals
  AML Admin Portal (KPI dashboard, case management, network graph)   General ledger or accounting integration
  Regulatory reporting (SAR filing, HKMA returns)                    Multi-jurisdiction licensing across EU / US (documented for future)
  On-prem / hybrid infrastructure with data residency controls       Public cloud-only deployment
  Audit trail + tamper-proof forensic audit ledger                   Real-time screening for off-platform P2P transfers

1.4 Key Design Decisions
------------------------

  **Decision**             **Choice**                        **Rationale**
  ------------------------ --------------------------------- ---------------------------------------------------------------------------------
  Core engine              Build (Python + FastAPI)          Differentiation on rule flexibility, ML scoring, tight HKMA integration
  Event backbone           Apache Kafka (on-prem)            Proven at scale; replay, partitioning, exactly-once
  Workflow orchestration   Temporal.io (on-prem)             Durable execution for Travel Rule + case state machines
  Database (primary)       PostgreSQL 16+                    ACID, JSONB, strong encryption, audit capabilities
  Forensic DB              PostgreSQL 16+ (WORM, separate)   Cryptographically sealed, independent verifiability for all manual interactions
  Graph layer              Apache AGE (PG extension)         openCypher + relational SQL; no separate graph DB
  Scheduling               Apache Airflow                    Industry standard; Kafka, PostgreSQL, cloud integration
  Orchestration            Kubernetes (k3s/Rancher)          Portability, auto-scaling, standardised deployment
  IAM                      Keycloak (self-hosted)            RBAC, OIDC federation, segregation of duties
  Blockchain analytics     Integrate (vendor adapter)        TRM Labs or Chainalysis; switching via abstracted adapter
  Travel Rule              Notabene TRP                      Largest counterparty directory; HK VASP adoption
  Frontend                 Next.js + React + TypeScript      Established stack; SSG for dashboard; SSR for case mgmt

2. System Context & Interfaces
==============================

2.1 External System Context
---------------------------

  **External System**              **Type**   **Interface**                          **Direction**   **Protocol**
  -------------------------------- ---------- -------------------------------------- --------------- ----------------------------
  Payments / Remittance Platform   Upstream   Sync hold/release + async events       Bidirectional   REST + Kafka
  Banking Rails (SWIFT/FPS/ACH)    Upstream   Bank file feeds                        Inbound         ISO 20022 / SWIFT MT / CSV
  KYC / KYB Provider               Upstream   Webhook + REST pull                    Inbound         REST (OAuth2)
  Blockchain Networks              Upstream   RPC + events                           Inbound         JSON-RPC / WebSocket
  Blockchain Analytics Vendor      External   Wallet screening API                   Outbound        REST (API key)
  Sanctions List Provider          External   SFTP feed + REST                       Inbound         SFTP / HTTPS
  Travel Rule Counterparties       External   TRP messaging                          Bidirectional   HTTPS mTLS
  JFIU (Hong Kong FIU)             External   STR filing                             Outbound        STREAMS 2 / SFTP XML
  Compliance Team                  User       Web UI                                 Bidirectional   HTTPS
  Internal Audit / Regulators      User       Read-only portal + forensic verifier   Inbound         HTTPS + SFTP

2.2 Deployment Context
----------------------

The platform deploys on dedicated on-premises Kubernetes clusters (Hong
Kong data centre: Equinix HK, MEGA-i). All customer PII and transaction
data resides on-prem. Vendor services receive only pseudonymised data
(wallet hashes). Travel Rule data is encrypted end-to-end.

3. Module Decomposition & Responsibilities
==========================================

The system decomposes into eleven microservices. Services communicate
via Kafka events (async) for most interactions, with REST/gRPC for
synchronous request-response. Each owns a distinct bounded context.

3.1 Ingestion Layer
-------------------

### 3.1.1 ingestion-service

-   Language: Python 3.12+ (FastAPI + Kafka producer)

-   Fiat: POST /api/v1/transactions/fiat (sync hold/release); batch SFTP
    > for SWIFT/ISO 20022

-   On-chain: RPC poller per EVM chain; Solana geyser; WebSocket
    > receiver

-   Normalisation: transforms to Canonical Transaction Schema (Section
    > 4.2)

-   Enrichment: wallet screening cache for address risk scores
    > pre-publish

### 3.1.2 Kafka Topic Map

  **Topic**             **Partitions**   **Retention**   **Key**               **Consumers**
  --------------------- ---------------- --------------- --------------------- ----------------------------------------------------
  fiat.raw              6                7d              transaction\_ref      normalisation engine
  onchain.raw           12               7d              chain\_id+tx\_hash    normalisation engine
  fiat.normalised       6                30d             customer\_id          TME, sanctions, risk scoring
  onchain.normalised    12               30d             customer\_id/wallet   TME, sanctions, blockchain analytics
  screening.requests    6                7d              round-robin           sanctions, wallet screening
  screening.results     6                30d             transaction\_ref      TME, audit
  travelrule.requests   3                30d             round-robin           Travel Rule gateway
  travelrule.results    3                90d             transaction\_ref      TME, audit
  alerts.generated      6                90d             customer\_id          CMS, audit
  audit.events          3                permanent       event\_id             audit service
  forensic.events       6                permanent       event\_category       forensic-audit-service (sole writer to ForensicDB)

3.2 Transaction Monitoring Engine (TME)
---------------------------------------

### tme-engine

-   Language: Python 3.12+ (FastAPI + Kafka consumer)

-   Internal: in-memory sliding window per customer (5min, 1hr, 24hr)

-   Rules: YAML DSL; versioned in PostgreSQL; hot-reload

-   Pipeline: Pre-filter \> Tier gate \> Rule evaluation (parallel
    > async) \> ML scoring \> Composite score \> Decision \> Output

-   Decisions: score 0-30 auto-approve; 31-65 flag for review; 66-100
    > block

### tme-ml (ML Inference)

-   ONNX runtime for XGBoost/LightGBM

-   Features: amount log, frequency, z-score baseline, wallet risk,
    > counterparty risk, jurisdiction pair, time-of-day

-   Output: probability \[0,1\] + SHAP explanations

3.3 Sanctions Screening Service
-------------------------------

-   Python 3.12+ (FastAPI sync + Kafka batch)

-   Fuzzy name matching: rapidfuzz (Levenshtein, token-set ratio,
    > Soundex)

-   Wallet screening: in-memory hash map for sub-ms exact-match lookups

-   Lists: OFAC SDN, UN, EU, HKMA, custom; daily SFTP pull; diff
    > detection

-   Confidence: \>=80 = block; 60-79 = review

-   Batch re-screening: all customers within 24h of list update

3.4 Blockchain Indexer & Wallet Analytics Adapter
-------------------------------------------------

### blockchain-indexer

-   Language: Go (performance-critical polling)

-   Per-chain goroutine worker; monitors Transfer events for
    > AnchorPoint + USDC

-   Chains: Ethereum, Polygon, Arbitrum, Optimism, Base, Solana

-   Publishes to onchain.raw (JSON: chain\_id, tx\_hash, block, from,
    > to, value, token, timestamp)

### wallet-analytics-adapter

-   Python 3.12+; abstracted vendor interface (TRM / Chainalysis /
    > Elliptic)

-   Redis cache: 24h TTL static scores, 1h TTL dynamic scores

-   N-hop chain analysis (configurable 1-3 hops); circuit breaker \>5
    > failures/min

3.5 Travel Rule Gateway
-----------------------

### travelrule-gateway

-   Python 3.12+ (Temporal workflow worker); triggered \>= HKD 8,000
    > equivalent

-   Workflow: Counterparty discovery (Notabene) \> TRP message \> await
    > response \> timeout (5min) \> hold/unhosted EDD

-   Publishes result to travelrule.results; TME consumes for final
    > decision

3.6 Risk Scoring Service
------------------------

-   Python 3.12+ (FastAPI + PostgreSQL)

-   Factors: velocity deviation, wallet risk, counterparty risk,
    > sanctions, PEP, adverse media, jurisdiction, source-of-funds

-   Triggers: new txn, sanctions update, PEP update, manual re-score

3.7 Case Management System (CMS)
--------------------------------

### case-management-service

-   Python 3.12+ (FastAPI + Temporal state machines)

-   States: NEW \> ASSIGNED \> UNDER\_INVESTIGATION \> CLOSED\_FP /
    > CLOSED\_MONITORING / SAR\_FILED

-   Temporal-enforced transitions; no direct DB mutation

  **Workflow**       **Trigger**                  **Steps**                                                         **SLA**
  ------------------ ---------------------------- ----------------------------------------------------------------- -------------
  Alert assignment   New alert                    Assign (round-robin); notify; escalate if unassigned \>1hr        Seconds
  Investigation      Analyst self-assigns         Hold transaction; gather evidence; blockchain queries; document   4hr typical
  SAR approval       Analyst drafts SAR           Peer review \> manager \> compliance officer \> file to JFIU      24hr
  Escalation         High-risk unactioned \>1hr   Team lead \> compliance manager \> MLRO                           Progressive

3.8 AML Admin Portal
--------------------

-   Framework: Next.js 14+ (App Router) + React + TypeScript

-   UI: shadcn/ui (Radix + Tailwind); state: React Query + Zustand; viz:
    > Cytoscape.js + Recharts

  **Route**            **Module**          **Description**
  -------------------- ------------------- ----------------------------------------------------------------------
  /dashboard           KPI Dashboard       Real-time AML metrics; configurable date range; exportable
  /alerts              Alert Queue         Paginated, filterable, sortable alert list
  /alerts/\[id\]       Alert Detail        Triggered rules, risk breakdown, customer 360, wallet summary
  /cases               Case Management     Case list: status, priority, assignee; bulk assignment
  /cases/\[id\]        Case Detail         Investigation workspace: timeline, graph, notes, evidence, SAR draft
  /reports             Reporting           SAR generation, HKMA returns, scheduled reports
  /config/rules        Rule Management     Rule config, version history, enable/disable, shadow-mode
  /config/thresholds   Thresholds          Per-tier and per-jurisdiction thresholds
  /admin/users         User Management     Keycloak-mediated provisioning and role assignment
  /audit/logs          Audit Log Viewer    Immutable audit log search, filter, export
  /forensic/verify     Forensic Verifier   Independent hash-chain verification UI for auditors

3.9 Regulatory Reporting & SAR Filing
-------------------------------------

-   Python 3.12+; SAR: JFIU-compatible STR form XML from case data

-   Filing: STREAMS 2 web portal (assisted upload); SFTP XML (future
    > automated)

-   HKMA returns: automated periodic AML statistical returns via Airflow
    > DAGs

3.10 Audit Trail Service
------------------------

-   Python 3.12+ (idempotent Kafka consumer)

-   Consumes audit.events topic; stores in dedicated PostgreSQL schema
    > with monthly partitioning

-   Append-only (no UPDATE/DELETE); hash-chain: SHA-256(prev\_hash +
    > payload)

-   Integrity checker runs hourly; events: transaction decisions, rule
    > evaluations, screening results, system events

3.11 Tamper-Proof Forensic Audit Ledger (ForensicDB)
----------------------------------------------------

The ForensicDB is a dedicated, cryptographically-sealed
write-once-read-many (WORM) database capturing every manual human
interaction: compliance analyst decisions, SAR approvals, rule
adjustments, risk tier overrides, and configuration changes. It provides
forensic-grade traceability for regulatory examination, internal audit,
and legal discovery, with independently verifiable proof that no record
has been altered or deleted after the fact.

### 3.11.1 Design Principles

-   WORM immutability: records cannot be modified, deleted, or
    > soft-deleted; enforced at storage engine level, not application
    > logic

-   Cryptographic sealing: every record SHA-256 hashed and chained;
    > tampering breaks the chain and is independently detectable

-   Operator attribution: all manual actions signed with operator
    > Keycloak identity, enriched with session token metadata, and
    > recorded with hardware-level NTP-synchronised timestamp

-   Segregation: ForensicDB runs on physically separate PostgreSQL
    > instance from operational DB; separate replication topology,
    > access controls, and backup schedule

-   Independent verifiability: standalone verifier tool (CLI + web UI)
    > recomputes the entire hash chain without any application code;
    > suitable for external auditors and regulators

-   Retention: minimum 7 years (AMLO requirement); automatic annual
    > archival to WORM optical media with chain-of-custody tracking

### 3.11.2 What Gets Recorded (Forensic Event Categories)

  **Event Category**          **Examples**                                        **Recorded Artifacts**
  --------------------------- --------------------------------------------------- ------------------------------------------------------------------------------------------------------------
  Alert disposition           Analyst closes alert as false positive              Alert ID, score, triggered rules, pre-state, decision, justification, operator ID, session hash, timestamp
  Case decisions              Manager approves SAR filing; analyst escalates      Case ID, state transition (from-\>to), notes, evidence hashes, approval chain, SAR draft version hash
  Rule configuration          Compliance manager adjusts velocity threshold       Rule ID, old/new definition (full JSON), diff, change ticket ref, approver, effective timestamp
  Risk tier overrides         Analyst downgrades customer from HIGH to MEDIUM     Party ID, old/new tier, override reason (free-text + category), expiry, approver, supporting doc hashes
  Sanctions list overrides    Analyst marks sanctions hit as false positive       Screening result ID, matched entity, match confidence, override reason, evidence refs, dual-approval chain
  Travel Rule interventions   Compliance officer releases held transaction        Transaction ID, workflow ID, hold reason, release reason, counter signatory, counterparty comms logs
  User access events          Analyst views sensitive customer; auditor exports   User ID, session ID, resource, access type (read/write/export), client IP, user agent, timestamp
  System config changes       DevOps adjusts Kafka partition count                Config key, old/new value hash, change management ticket, approver, deployment timestamp
  Model governance            ML model promoted from shadow to active             Model ID, version, training run, validation metrics, approval chain, effective timestamp, rollback policy
  SAR/STR lifecycle           SAR draft, review, approval, filing, JFIU ack       Full SAR XML at each stage, each reviewer ID + timestamp, JFIU ref, filing timestamp

### 3.11.3 Cryptographic Sealing Architecture

The ForensicDB employs dual-layer sealing: per-table Merkle trees for
efficient partial verification and a global hash chain for end-to-end
integrity.

-   Record-level: SHA-256(record\_type, payload, operator\_id,
    > business\_timestamp, previous\_record\_hash) computed at write
    > time

-   Merkle tree (per table): balanced Merkle tree per event category.
    > Root published hourly to external witness. Auditors verify single
    > records in O(log n) time.

-   Global hash chain: chain\_n = SHA-256(chain\_n-1, table\_name,
    > record\_hash, timestamp). Monotonic sequence number. Chain head
    > published with Merkle roots.

-   Verification tool (forensic-verifier CLI): recomputes all hashes
    > from genesis; outputs tamper report: clean or specific divergent
    > records

-   Auto-verification: integrity checker runs every 15 minutes on
    > read-only replica; chain break triggers immediate P0 alert

### 3.11.4 WORM Enforcement at the Storage Layer

-   Database-level: forensic\_db role has only INSERT + SELECT. UPDATE,
    > DELETE, TRUNCATE, DROP revoked. Table ownership held by separate
    > admin role unused by application.

-   Row-level: BEFORE UPDATE / BEFORE DELETE triggers unconditionally
    > raise exceptions. Trigger removal itself generates an audit event
    > in externally-monitored tamper log.

-   Filesystem-level: PostgreSQL data directory mounted with chattr +i
    > on WAL directory. Underlying block device exported from storage
    > array with WORM snapshot policies.

-   Replication: read-only replica in physically separate network
    > segment serves verifier and auditor access. No write path to
    > replica.

-   Backup: daily encrypted backups to MinIO with S3 Object Lock in
    > Compliance mode (retention lock, no deletion even by root). Annual
    > archival to WORM optical media with chain-of-custody.

### 3.11.5 External Witness Publishing

To provide independent third-party verifiability, Merkle roots and chain
heads are published to external witnesses.

-   Hourly: composite hash (Merkle roots + chain head) published to
    > Bitcoin testnet via OP\_RETURN or to Polygon (lower cost).
    > Transaction ID stored in ForensicDB as external witness reference.

-   Daily attestation: signed attestation containing global chain head
    > and all Merkle roots stored in separate cloud immutable store (S3
    > Object Lock / Azure Immutable Blob) with different access control
    > boundary.

-   Independent verification: any auditor can independently verify
    > by: (a) recomputing the hash chain from ForensicDB records; (b)
    > verifying published Merkle root matches recomputed root; (c)
    > checking blockchain witness transaction exists and contains the
    > same hash. No trust in the institution systems is required.

### 3.11.6 Service: forensic-audit-service

-   Language: Python 3.12+ (idempotent Kafka consumer + REST API for
    > auditors)

-   Writes: consumes forensic.events Kafka topic (partitioned by
    > event\_category); inserts into ForensicDB as sole writer

-   Reads: REST API - GET /forensic/records, GET /forensic/chain/verify
    > (returns current chain state and last verified timestamp)

-   Verifier: scheduled subprocess recomputes hash chains in read-only
    > mode against replica; results logged to Prometheus metrics and
    > tamper-alert topic

-   Witness publisher: computes current Merkle roots, publishes to
    > external witness, stores witness tx reference

-   Retention manager: exports records older than 7 years to WORM media,
    > verifies export hash, logs archival with chain-of-custody tracking

### 3.11.7 ForensicDB Schema

  **Table**                     **Key Columns**                                                                                                                                              **Purpose**
  ----------------------------- ------------------------------------------------------------------------------------------------------------------------------------------------------------ --------------------------------------------------------------------
  forensic.chain\_head          sequence\_id (bigserial), chain\_hash, record\_table, record\_hash, business\_timestamp, witness\_tx\_id                                                     Global hash chain linking all records in insertion order
  forensic.alert\_disposition   event\_id (UUID v7), alert\_id, disposition, justification, operator\_id, pre\_state (jsonb), post\_state (jsonb), prev\_hash, record\_hash                  Every alert decision with full before/after state
  forensic.case\_transition     event\_id, case\_id, from\_state, to\_state, operator\_id, notes, evidence\_hashes\[\], approval\_chain (jsonb), prev\_hash, record\_hash                    Case state transitions with approval chain
  forensic.rule\_change         event\_id, rule\_id, old\_definition (jsonb), new\_definition (jsonb), change\_diff, approver\_id, change\_ticket\_ref, prev\_hash, record\_hash             All rule and threshold configuration changes
  forensic.risk\_override       event\_id, party\_id, old\_tier, new\_tier, override\_reason, override\_category, expiry\_dt, approver\_id, supporting\_docs\[\], prev\_hash, record\_hash   Manual risk tier overrides with expiry and justification
  forensic.sar\_lifecycle       event\_id, str\_id, stage (DRAFT/REVIEWED/APPROVED/FILED/ACKED), operator\_id, sar\_content (xml), reviewer\_ids\[\], jfiu\_ref, prev\_hash, record\_hash    Complete SAR lifecycle with full XML at each stage
  forensic.access\_log          event\_id, user\_id, session\_id, resource\_type, resource\_id, access\_type, client\_ip, user\_agent, justification, prev\_hash, record\_hash               All access to sensitive customer data and case records
  forensic.merkle\_root         table\_name, block\_start, block\_end, merkle\_root, computed\_at, witness\_tx\_id                                                                           Published Merkle roots per table per hour for partial verification
  forensic.external\_witness    witness\_id, composite\_hash, target (BITCOIN\_TESTNET/POLYGON/S3), witness\_tx\_id, published\_at, verified\_at                                             Record of all external witness publications

### 3.11.8 Integration with Existing Services

The ForensicDB complements, not replaces, the operational audit trail
(audit.events / aml\_audit). The operational audit trail captures
system-level events for observability and debugging. The ForensicDB
captures manual human interactions for regulatory-grade tamper-proof
evidence. They operate on physically separate infrastructure.

-   TME: publishes rule execution logs to audit.events (operational)
    > only; forensic events generated only if compliance analyst
    > manually overrides a TME decision

-   CMS: publishes all alert dispositions, case state transitions,
    > notes, evidence uploads, and SAR drafts to forensic.events topic

-   AML Admin Portal: publishes all rule config changes, risk overrides,
    > threshold adjustments, and access to sensitive records to
    > forensic.events

-   regulatory-reporting-service: publishes SAR lifecycle events to
    > forensic.events

-   All forensic.events publishers must include: operator\_id
    > (Keycloak), session\_id, client\_ip, user\_agent, business
    > justification. Missing fields = rejected by
    > forensic-audit-service.

-   forensic-audit-service is the sole writer to the ForensicDB. No
    > other service has credentials to the ForensicDB instance. The
    > operational audit trail continues to write to the separate
    > aml\_audit PostgreSQL instance.

4. Data Architecture & Storage
==============================

4.1 Database Topology
---------------------

  **Database**     **Engine**                                   **Purpose**                                                      **Data Includes**
  ---------------- -------------------------------------------- ---------------------------------------------------------------- -----------------------------------------------------------------------------------------------------------------------------------------
  aml\_core        PostgreSQL 16+                               Primary operational DB                                           Customers, parties, accounts, transactions, screenings, alerts
  aml\_audit       PostgreSQL 16+ (append-only)                 Immutable operational audit store                                All system-level audit events with hash-chain verification
  aml\_forensic    PostgreSQL 16+ (WORM, physically separate)   Tamper-proof forensic ledger for all manual human interactions   Alert dispositions, case decisions, rule changes, risk overrides, SAR lifecycle, access logs, Merkle trees, external witness references
  aml\_graph       PostgreSQL 16+ + Apache AGE                  Graph exploration                                                Party-to-party edges, wallet-to-wallet edges, transaction graph
  aml\_analytics   TimescaleDB (PG extension)                   Aggregation + time-series                                        Dashboard metrics, trend analysis, ML feature store
  redis\_cache     Redis                                        Low-latency cache                                                Wallet risk scores, sanctions index, customer tiers, rate limit counters
  minio\_store     MinIO (S3-compatible)                        Object / evidence storage                                        SAR PDFs, evidence, ML model artifacts, historical exports

4.2 Canonical Transaction Schema
--------------------------------

All transactions normalised into this canonical schema before
processing:

  **Field**                   **Type**                  **Source**         **Example**
  --------------------------- ------------------------- ------------------ -------------------------------------------------------------
  transaction\_id             UUID v7                   System             01J12345-\...
  external\_ref               varchar(255)              Original system    SWIFT MT103 ref / tx hash
  source\_type                enum                      Ingestion          FIAT\_SWIFT / FIAT\_ACH / STABLECOIN\_EVM / STABLECOIN\_SOL
  chain\_id                   int (nullable)            Indexer            1 (Ethereum) / null for fiat
  sender\_party\_id           UUID (nullable)           Customer profile   Party UUID or null for external
  sender\_wallet              varchar(255) (nullable)   Indexer            0x\... / null for fiat
  sender\_name                varchar(255)              Payment/KYC        John Smith
  sender\_jurisdiction        char(2)                   KYC                HK
  beneficiary\_party\_id      UUID (nullable)           Customer profile   Party UUID or null for external
  beneficiary\_wallet         varchar(255) (nullable)   Indexer            0x\... / null for fiat
  beneficiary\_name           varchar(255)              Payment/KYC        Acme Corp
  beneficiary\_jurisdiction   char(2)                   Counterparty       SG
  amount                      numeric(24,8)             Original system    15000.00
  currency                    char(3)                   Original system    HKD / USDC
  amount\_usd\_equivalent     numeric(24,2)             FX conversion      1923.08
  txn\_timestamp              timestamptz               Original system    2026-07-03T10:30:00+08:00
  risk\_score                 int (nullable)            TME                45
  risk\_tier\_at\_time        enum                      Risk scoring       MEDIUM
  overall\_decision           enum                      TME                HOLD / APPROVE / FLAG
  ingestion\_timestamp        timestamptz               System             2026-07-03T10:30:01.123+08:00

4.3 Data Model (Key Tables)
---------------------------

Full data model defined in the separate AML Data Model Converged
Specification. Key entity groups:

-   Party & KYC: party, party\_document, party\_wallet,
    > party\_risk\_history, party\_risk\_tier

-   Transaction: fiat\_transaction, onchain\_transaction,
    > canonical\_transaction (materialised view),
    > transaction\_wallet\_link

-   Screening: screening\_result, screening\_match\_detail,
    > sanctions\_list, sanctions\_list\_entry

-   Risk: risk\_score\_event, risk\_model\_version, risk\_rule\_version

-   Travel Rule: travelrule\_message, travelrule\_counterparty,
    > travelrule\_workflow

-   Alert & Case: alert, case, case\_note, case\_evidence,
    > case\_transaction\_link

-   SAR: str\_filing, str\_filing\_version, str\_submission\_ack

-   Audit: audit\_event, audit\_hash\_chain

-   Forensic: forensic.chain\_head, forensic.alert\_disposition,
    > forensic.case\_transition, forensic.rule\_change,
    > forensic.risk\_override, forensic.sar\_lifecycle,
    > forensic.access\_log, forensic.merkle\_root,
    > forensic.external\_witness

5. API Contracts & Service Interfaces
=====================================

5.1 External REST API (AML Gateway)
-----------------------------------

  **Endpoint**                             **Method**   **Description**
  ---------------------------------------- ------------ ---------------------------------------------------------------------
  /api/v1/transactions/screen              POST         Submit txn for pre-settlement screening; sync HOLD/APPROVE response
  /api/v1/transactions/batch-screen        POST         Async batch screening; returns batch\_id for polling
  /api/v1/transactions/batch/{id}/status   GET          Poll batch screening status
  /api/v1/wallets/screen                   POST         Submit wallet address(es) for risk scoring
  /api/v1/transactions/{ref}               GET          Retrieve transaction screening detail
  /api/v1/health                           GET          Health check
  /api/v1/forensic/verify                  GET          Public hash-chain verification endpoint for auditors

5.2 Key Internal Service APIs
-----------------------------

  **Service**                    **Interface**   **Key Endpoints / Topics**
  ------------------------------ --------------- --------------------------------------------------------------------------------------------------------
  sanctions-service              REST            POST /screen; POST /screen/wallet
  wallet-analytics-adapter       REST            POST /score; GET /cache/status
  risk-scoring-service           REST            POST /score/transaction; GET /customer/{id}/risk-profile
  tme-engine                     REST            POST /decide; POST /decide/batch
  travelrule-gateway             Temporal        TravelRuleWorkflow(txn\_payload)
  case-management-service        REST            GET /alerts; POST /cases; POST /cases/{id}/transitions
  regulatory-reporting-service   REST            POST /sar/generate; POST /filing/submit
  audit-service                  Kafka           Consumes audit.events; no external API
  forensic-audit-service         Kafka + REST    Consumes forensic.events; sole writer to ForensicDB; GET /forensic/records; GET /forensic/chain/verify

6. Infrastructure & Deployment (On-Prem / Hybrid)
=================================================

6.1 On-Prem Kubernetes Cluster
------------------------------

  **Component**                **Spec**                                      **Sizing**
  ---------------------------- --------------------------------------------- -----------------------------------------------------------------------------------------
  Kubernetes                   3 CP + 6 workers (scale to 10)                k3s/RKE2 on Ubuntu 24.04; 64GB/16vCPU per worker
  PostgreSQL (aml\_core)       3-node Patroni + 2 replicas                   NVMe; 128GB/8vCPU; pgBackRest to MinIO
  PostgreSQL (aml\_audit)      2-node HA (Patroni)                           NVMe; 64GB/8vCPU; time-partitioned tables
  PostgreSQL (aml\_forensic)   2-node HA (Patroni) separate VLAN with WORM   NVMe; 128GB/8vCPU; WORM snapshots; S3 Object Lock backups; annual WORM optical archival
  Kafka/Redpanda               3-broker                                      32GB/8vCPU; 2TB NVMe per broker; 7d retention
  Redis                        2-node active-passive                         32GB; wallet cache, sanctions index, rate limiting
  MinIO                        4-node erasure coding                         8TB/node; evidence, model artifacts, backups
  Blockchain nodes             1 per chain                                   ETH archive: 2TB+; SOL: 1TB; L2s: lighter RPC nodes
  Load balancers               HAProxy + Nginx Ingress                       Active-passive; TLS with HSM-backed keys
  HSM                          Thales Luna / Azure Dedicated HSM             Root CA, TLS, encryption, TRP signing keys
  Monitoring                   Prometheus + Grafana + Loki + Tempo           Metrics 30d; logs 90d; traces 14d
  Backup                       Velero + pgBackRest                           Daily to MinIO; weekly off-site encrypted cloud; WORM media annual for forensic

6.2 Network Topology
--------------------

-   DMZ: API gateway + blockchain RPC ports (only external reachable
    > components)

-   Application: all microservices, Kafka, Redis (internal only; no
    > direct external access)

-   Data: PostgreSQL clusters, MinIO (isolated; accessed only via mTLS)

-   Forensic Data: separate VLAN segment for ForensicDB; read-only
    > replica for verifier/auditors; no write path externally

-   Management: jumpbox with SSO + MFA; no direct SSH to nodes

-   Segmentation: VLANs via Calico network policy; Kubernetes
    > NetworkPolicies (default deny)

6.3 Kubernetes Resource Quotas
------------------------------

  **Namespace**   **Services**                                                **CPU**    **Memory**   **Pods**
  --------------- ----------------------------------------------------------- ---------- ------------ -----------
  ingestion       ingestion-service, blockchain-indexer                       4 cores    16 GB        3/12
  monitoring      tme-engine, tme-ml, sanctions-service                       8 cores    32 GB        3/16
  analytics       wallet-analytics-adapter, risk-scoring-service              4 cores    16 GB        2/10
  compliance      travelrule-gateway, case-management, regulatory-reporting   6 cores    24 GB        3/10
  forensic        forensic-audit-service                                      2 cores    8 GB         2/4
  portal          aml-portal, api-gateway                                     2 cores    8 GB         2/6
  infra           Kafka, Redis, PG operators, Temporal, Airflow               12 cores   48 GB        Dedicated
  audit           audit-service                                               2 cores    8 GB         2/4

7. CI/CD Pipeline & DevSecOps
=============================

7.1 Pipeline Architecture
-------------------------

-   Source: GitLab (self-hosted, on-prem) - single monorepo with
    > per-module CI

-   CI runner: GitLab Runner (Kubernetes executor, on-prem) - all builds
    > in data centre

-   Registry: GitLab Container Registry (on-prem, S3-compatible backing)

-   Deploy: GitOps via ArgoCD (3-min sync; manual emergency;
    > canary/blue-green per risk level)

-   Secrets: Sealed Secrets for Git-encrypted; HashiCorp Vault for
    > dynamic (DB creds, API keys); HSM for encryption/signing keys

7.2 Per-Service CI Pipeline Stages
----------------------------------

-   Lint: ruff/ESLint/gofmt

-   Type check: mypy (strict) / tsc \--noEmit

-   Unit test: pytest (\>85% coverage) / vitest / go test

-   Security scan: Bandit, Trivy, Semgrep

-   Build: Docker with distroless base images

-   Push: GitLab Container Registry (Cosign signed)

-   Integration test: ephemeral K8s namespace; service-level suite

-   Deploy: ArgoCD PR-based sync to env-specific Git repo

8. Build Phases & Milestones (52-Week Roadmap)
==============================================

Sprint 0: Platform & Infrastructure Foundation (Weeks 0-4)
----------------------------------------------------------

*Objective: Standing up dev and staging environments.*

-   Provision on-prem K8s (dev + staging); deploy PostgreSQL, Kafka,
    > Redis, MinIO, Temporal

-   Deploy GitLab, Runner, ArgoCD, Harbor registry, Keycloak (RBAC
    > roles)

-   Set up Prometheus + Grafana + Loki + Tempo monitoring

-   Establish CI/CD pipeline scaffolds for Python, TS, Go services

-   Exit: developer merges to dev; deployed within 15 min; monitoring
    > dashboards green

Phase 1: Core Monitoring Engine (Weeks 4-14)
--------------------------------------------

*Objective: Minimum viable AML - fiat + stablecoin through basic rule
engine with sanctions.*

-   Build ingestion-service + tme-engine v1 (configurable rules DSL,
    > velocity/threshold/counterparty)

-   Build sanctions-service v1 (OFAC SDN, exact + fuzzy matching);
    > audit-service (append-only, hash-chain)

-   Build blockchain-indexer (Ethereum only); integrate payment platform
    > /screen endpoint

-   Develop aml\_core PostgreSQL schema; document OpenAPI 3.1 contracts

-   Exit: 100 fiat tps + 50 on-chain tps; sanctions \<500ms p95; live on
    > staging

Phase 2: Multi-Chain & Wallet Analytics (Weeks 10-22)
-----------------------------------------------------

*Objective: Full blockchain coverage with wallet risk scoring.*

-   Extend indexer to Polygon, Arbitrum, Optimism, Base, Solana

-   Build wallet-analytics-adapter v1 (abstracted vendor, Redis cache);
    > risk-scoring-service v1

-   Add wallet screening to sanctions; integrate real-time sanctions
    > list updates

-   Load testing: target 500 TPS

-   Exit: all 6 chains within 30s of block finality; \>100K txns/day
    > processed

Phase 3: Travel Rule & Case Management (Weeks 18-34)
----------------------------------------------------

*Objective: Full compliance - Travel Rule, analyst CMS, SAR reporting.*

-   Build travelrule-gateway (Temporal TRP workflow, Notabene)

-   Build case-management-service (state machine, investigation
    > workspace, note/evidence); AML Admin Portal (Modules 1-3)

-   Build regulatory-reporting-service v1 (JFIU-compatible SAR); deploy
    > Airflow

-   Exit: Travel Rule operational; CMS L1/L2/L3 swimlanes functional;
    > portal feature-complete

Phase 4: Intelligence & Regulatory Readiness (Weeks 30-44)
----------------------------------------------------------

*Objective: ML scoring, graph, audit/forensic hardening for regulator
inspection.*

-   Deploy tme-ml inference (XGBoost ONNX, shadow mode); Airflow ML
    > training pipeline

-   Deploy aml\_graph (Apache AGE); ForensicDB and
    > forensic-audit-service (tamper-proof manual interaction ledger)

-   PEP/adverse media screening; DR/BCP (hot standby); penetration test;
    > CIS benchmark audit

-   Regulatory documentation pack; SAR workflow end-to-end test with
    > JFIU simulation

-   External witness publishing activated (hourly blockchain + daily
    > cloud attestation)

-   Exit: pentest passed; forensic hash-chain verified; SAR tested;
    > documentation complete

Phase 5: Optimisation & Scale (Weeks 40-52+)
--------------------------------------------

*Objective: Production ML, expanded chains, performance.*

-   Graduate ML to production (active scoring + rules); false positive
    > reduction tuning

-   Add Tron, Cosmos chain support; performance optimisation (queries,
    > Kafka, Redis)

-   Production rollout: phased traffic migration (10% \> 50% \> 100%);
    > 30-day hypercare

-   Exit: all milestones met; operating at target scale in production;
    > regulatory filing live

8.1 Milestone Summary
---------------------

  **Phase**   **Weeks**   **Key Deliverables**
  ----------- ----------- ----------------------------------------------------------------------------------
  Sprint 0    0-4         K8s + stateful services + CI/CD + monitoring live
  Phase 1     4-14        TME v1, sanctions, Ethereum indexer, audit, fiat API
  Phase 2     10-22       All 6 chains, wallet analytics, risk scoring, live sanctions
  Phase 3     18-34       Travel Rule TRP, CMS, admin portal (dashboard/alerts/cases), SAR gen
  Phase 4     30-44       ML (shadow), AGE graph, ForensicDB, PEP, DR/BCP, security audit, regulatory pack
  Phase 5     40-52+      ML production, false positive reduction, additional chains, production launch

9. Team Structure & Sizing
==========================

Four squads aligned to delivery phases. Peak build team: 20-25 engineers
+ supporting roles.

9.1 Squad Model
---------------

  **Squad**                   **Focus**                                         **Active**            **Headcount**
  --------------------------- ------------------------------------------------- --------------------- --------------------------------
  A: Core Platform            Ingestion, TME, sanctions, audit                  Sprint 0 to Phase 5   5-6 (4 BE, 1-2 DE)
  B: Blockchain & Analytics   Indexer, wallet analytics, ML, risk scoring       Phase 1 to 5          4-5 (2 blockchain, 2 ML, 1 DE)
  C: Compliance UX            CMS, Travel Rule, portal, reporting, forensic     Phase 2 to 5          5-6 (3 BE, 2 FE, 1 DE)
  D: Platform & Infra         K8s, CI/CD, security, monitoring, data platform   Sprint 0 to 5         4-5 (2 DevOps, 1 Sec, 1-2 DE)

9.2 Full Roles List
-------------------

  **Role**                     **Count**   **Key Skills**
  ---------------------------- ----------- ----------------------------------------------------------------
  Backend Engineer (Python)    7           FastAPI, async Python, Kafka, PostgreSQL, Temporal
  Backend Engineer (Go)        2           Go, blockchain nodes, gRPC, high-throughput
  Frontend Engineer (TS)       2           Next.js, React, Cytoscape.js, Recharts, shadcn/ui
  Data Engineer                4           Kafka, Flink, Airflow, PostgreSQL/ClickHouse, ML pipelines
  ML Engineer                  2           XGBoost, ONNX, feature engineering, SHAP, model lifecycle
  DevOps / Platform Engineer   3           K8s (on-prem), Rancher, ArgoCD, GitLab CI, Terraform
  Security Engineer            1           CIS hardening, pentesting, HSM, PKI, secrets, network security
  QA / SDET                    3           Chaos, k6 load, integration, regulatory scenario testing
  Technical Lead               1           System architecture, API contracts, data model, regulatory
  Delivery Manager             1           Vendor management, timeline, risk, stakeholder reporting
  Compliance SME               1           Rule authoring, regulatory, SAR workflows, test scenarios

10. Vendor Integration Matrix
=============================

  **Vendor**               **Product**            **Integration**       **Phase**            **Data Residency**
  ------------------------ ---------------------- --------------------- -------------------- ------------------------------------------
  TRM Labs                 Wallet Screening API   REST API              Phase 2              Vendor cloud (pseudonymised hashes only)
  Chainalysis              KYT                    REST API (fallback)   Phase 2              Vendor cloud (pseudonymised)
  Notabene                 Travel Rule Platform   REST + webhooks       Phase 3              Vendor cloud (PII encrypted in transit)
  LexisNexis / Refinitiv   World-Check            SFTP + REST           Phase 1              On-prem (list data) + vendor cloud (PEP)
  Onfido / Jumio           KYC verification       Webhook + REST        Phase 1 (consumed)   Vendor cloud (PDPO agreement)
  OpenVASP / Sygna         Travel Rule fallback   REST (future)         Phase 3+             Vendor cloud
  JFIU                     STREAMS 2 filing       Web portal + SFTP     Phase 4              HK government (STR data)

*All vendor contracts must include DPA with HK PDPO compliance,
pseudonymisation requirements for blockchain analytics, SOC2 Type II,
and right-to-audit clauses.*

11. Testing Strategy
====================

11.1 Test Pyramid
-----------------

  **Layer**            **Scope**                              **Frequency**               **Tooling**                            **Target**
  -------------------- -------------------------------------- --------------------------- -------------------------------------- -----------------------------------------
  Unit                 Individual functions/services          Every commit                pytest / vitest / go test              \>85% coverage
  Integration          Service-to-service, Kafka, DB          Every MR                    pytest + testcontainers, temporalite   All critical paths
  Contract             API contract (CDC)                     Every MR                    Pact + OpenAPI validation              All public endpoints
  E2E                  Full flow: ingestion to audit          Nightly + pre-release       Custom harness + k6                    Top 20 scenarios
  Regulatory           HKMA/FATF typologies                   Pre-release + quarterly     Curated test cases                     All documented scenarios
  Chaos                Node failure, partition, broker loss   Monthly                     Chaos Mesh / Litmus                    Survive single-node failure
  Forensic integrity   Hash-chain tamper simulation           Pre-release + weekly auto   forensic-verifier CLI                  Detect all tampering; P0 alert on break
  Load / Perf          2x peak volume                         Pre-release + quarterly     k6 + custom loadgen                    500 TPS; p95 \<500ms
  Security             SAST, container, deps                  Every commit + weekly       Bandit, Trivy, Semgrep, ZAP            Zero critical CVEs

11.2 Key Regulatory Test Scenarios
----------------------------------

  **Scenario**                 **Description**                                                   **Expected Outcome**                                                      **Source**
  ---------------------------- ----------------------------------------------------------------- ------------------------------------------------------------------------- ---------------------
  Structuring                  Multiple stablecoin txns just under HKD 8,000                     Alert generated; case created                                             HKMA AML/CFT
  Cross-rail layering          Fiat deposit \> stablecoin \> unhosted wallet \> secondary fiat   Cross-rail alert; enhanced monitoring                                     FATF 2025 report
  Sanctions hit                Beneficiary wallet linked to OFAC SDN entity                      Blocked; mandatory reporting                                              OFAC / UN
  Travel Rule threshold        USDC transfer HKD 10,000 to external VASP                         TRP message sent; beneficiary data returned; released                     AMLO Sch.2 s.13A
  Unhosted wallet high-value   USDC \>HKD 100,000 to unhosted wallet                             Blocked; EDD required                                                     HKMA guidelines
  PEP transaction              PEP customer sends HKD 500,000 offshore                           Flagged; EDD; senior analyst                                              AMLO Sch.2 s.10
  Velocity breach              50+ txns to 50 addresses in 1 hour                                Alert; account frozen                                                     FATF red flags
  Forensic tamper event        Direct DB modification attempt on ForensicDB                      Trigger blocks write; tamper alert generated; hash chain break detected   AMLO record-keeping

12. Security Architecture
=========================

12.1 Principles
---------------

-   Least privilege: minimum permissions for every service and human
    > operator

-   Defence in depth: network segmentation, encryption at rest/transit,
    > application controls

-   Zero trust: no implicit trust between services; all inter-service
    > via mTLS

-   Separation of duties: no user can both configure rules and review
    > cases; admin roles segregated

12.2 Controls
-------------

  **Category**        **Controls**
  ------------------- --------------------------------------------------------------------------------------------------------------
  Network             VLAN segmentation (DMZ/app/data/forensic/mgmt); NetworkPolicies default deny; WAF on API gateway
  Transport           TLS 1.3 external; mTLS inter-service (Istio/Linkerd); HSM-backed certificates
  Data at rest        AES-256 for PostgreSQL (TDE); MinIO SSE; WORM storage policy (S3 Object Lock) for ForensicDB backups
  AuthN               Keycloak OIDC (human); OAuth2 client credentials (M2M); audience-restricted tokens
  AuthZ               RBAC fine-grained per module; ABAC for case-level data; ForensicDB read segregated from write
  Audit               Immutable operational audit trail + cryptographically-sealed forensic ledger; hourly hash-chain verification
  Secrets             HashiCorp Vault dynamic secrets (DB creds daily rotation); no secrets in env vars; Sealed Secrets for Git
  App                 OWASP Top 10: CSRF tokens, XSS headers, rate limiting, Pydantic validation, parameterised queries
  Supply chain        Cosign image signing; Syft SBOM; Trivy dependency scanning; distroless base images
  Incident response   24/7 on-call for AML decisions; alerts on auth failures, API anomalies, audit chain breaks, forensic tamper

13. Performance & Scalability Requirements
==========================================

13.1 SLIs / SLOs
----------------

  **SLI**                         **Target**                  **Method**
  ------------------------------- --------------------------- -------------------------------------
  Sync screening latency (p50)    \<200 ms                    API endpoint histograms
  Sync screening latency (p95)    \<500 ms                    API endpoint histograms
  Sync screening latency (p99)    \<1,500 ms                  API endpoint histograms
  Throughput (sustained)          500 TPS                     Request rate via API gateway
  On-chain ingestion latency      \<30s from block finality   Block vs ingestion timestamps
  Travel Rule workflow            \<5 min to completion       Temporal workflow metrics
  Alert generation latency        \<10s from txn receipt      Txn vs alert timestamps
  Dashboard freshness             \<60s from event            Event vs dashboard query timestamps
  Forensic chain verification     \<5 min full chain          forensic-verifier wall clock time
  Availability (sync screening)   99.95%                      Health check success / total
  Availability (async)            99.9%                       Kafka consumer lag \<10K messages

13.2 Scalability Strategy
-------------------------

-   Horizontal: stateless services scale pods on Kafka lag + CPU

-   Database: read replicas for dashboards; time partitioning for
    > txns/audit; PgBouncer pooling

-   Kafka: 2x peak partition sizing; rebalance planned during
    > maintenance windows

-   Cache: Redis cluster for wallet scores (90%+ hit rate target);
    > in-memory sanctions index

-   Blockchain: per-chain goroutine pools; one slow chain never blocks
    > others

Appendix A: Technology Stack Reference
======================================

  **Category**           **Technology**                                                   **Version**
  ---------------------- ---------------------------------------------------------------- -------------
  Backend (Services)     Python (FastAPI, Pydantic, SQLAlchemy, Kafka-Python)             3.12+
  Backend (Blockchain)   Go (go-ethereum, solana-go)                                      1.22+
  Workflows              Temporal.io (Python SDK)                                         1.24+
  Frontend               Next.js 14+, React 18+, TypeScript, Tailwind CSS 5+, shadcn/ui   Latest
  Viz                    Cytoscape.js 3.30+, Recharts 2.12+                               Latest
  DB Primary             PostgreSQL 16+ with Patroni (HA)                                 16+
  DB Time-series         TimescaleDB (PG extension)                                       2.17+
  DB Graph               Apache AGE (PG extension)                                        1.5+
  DB Forensic            PostgreSQL 16+ WORM (separate instance)                          16+
  Streaming              Apache Kafka / Redpanda                                          3.7+ / 24+
  Cache                  Redis                                                            7.2+
  Object Storage         MinIO                                                            2024+
  Orchestration          Kubernetes (k3s / RKE2)                                          1.30+
  CI/CD                  GitLab (self-hosted) + ArgoCD                                    17+
  Workflow Scheduler     Apache Airflow                                                   2.10+
  Auth / IAM             Keycloak                                                         25+
  Monitoring             Prometheus, Grafana, Loki, Tempo                                 Latest
  Secrets                HashiCorp Vault                                                  1.18+
  HSM                    Thales Luna / Azure Dedicated HSM                                Commercial

Appendix B: Glossary of Terms
=============================

**AGE:** Apache Graph Extension - PG extension for graph database via
openCypher

**AMLO:** Anti-Money Laundering Ordinance (Cap. 615), Hong Kong

**AnchorPoint:** HKDR stablecoin issued by SCB x HKT x Animoca Brands JV

**ArgoCD:** GitOps CD tool for Kubernetes

**CDD:** Customer Due Diligence - verifying identity and assessing risk

**CMS:** Case Management System - AML alert investigation and SAR filing
workflow

**EDD:** Enhanced Due Diligence - deeper KYC for high-risk customers

**FATF:** Financial Action Task Force - international AML/CFT
standard-setter

**ForensicDB:** Tamper-proof WORM ledger with cryptographic sealing for
all manual human interactions

**GENIUS Act:** US federal legislation (mid-2025) regulating stablecoin
issuers under BSA

**GitOps:** Git as single source of truth for infrastructure/application
config

**HKMA:** Hong Kong Monetary Authority - banking and stablecoin
regulator

**HSM:** Hardware Security Module - tamper-resistant cryptographic key
management

**JFIU:** Joint Financial Intelligence Unit (HK) - receives STRs

**KYC/KYB:** Know Your Customer / Know Your Business - identity and due
diligence

**Kustomize:** Kubernetes configuration customisation tool

**mTLS:** Mutual TLS - both client and server present certificates

**MiCA:** Markets in Crypto-Assets Regulation (EU)

**MLRO:** Money Laundering Reporting Officer - designated compliance
officer

**PDPO:** Personal Data (Privacy) Ordinance (Cap. 486), Hong Kong

**PEP:** Politically Exposed Person - subject to enhanced due diligence

**RKE2:** Rancher Kubernetes Engine 2 - enterprise K8s distribution

**SAR/STR:** Suspicious Activity/Transaction Report - filed with FIU

**SFC:** Securities and Futures Commission - HK securities and VASP
regulator

**Temporal:** Durable execution platform for workflow orchestration

**TME:** Transaction Monitoring Engine - core rule evaluation and
scoring engine

**TRP:** Travel Rule Protocol - secure exchange of
originator/beneficiary data between VASPs

**Travel Rule:** FATF Recommendation 16 - require originator/beneficiary
info with transfers

**UBO:** Ultimate Beneficial Owner - natural person controlling a legal
entity

**VASP:** Virtual Asset Service Provider - virtual asset transfer,
custody, or exchange services

**WORM:** Write Once Read Many - storage that prevents modification or
deletion after write
