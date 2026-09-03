# Multi-Agent Brainstorming & Implementation Plan: Tap and Go ETL Container

## Phase 1: Single-Agent Design (Primary Designer)

**Goal:** Rebuild the ETL data pipeline for production according to `"doc\Build a new ETL container to extract data for Tap and Go.md"` using the sample data.
**Design Proposal:**
- **Stack:** Python 3.12 (Polars + SQLAlchemy), PostgreSQL 16 (w/ Apache AGE), Dagster for orchestration.
- **Workflow:** 
  1. **Extract:** Python script reads CSV/API.
  2. **Load Raw:** Insert into `raw.wallet_ledger_ingest` with `COPY`.
  3. **Transform:** Polars functions clean strings, separate entities.
  4. **Graph Projection:** Output to `graph.entity_vertices` and `graph.transaction_edges`.
  5. **Graph Load:** Upsert into Apache AGE via Cypher commands.
  6. **Data Quality:** Idempotent runs based on `composite_txn_hash`.

---

## Phase 2: Structured Review Loop (Complete)

### 1. Skeptic / Challenger Agent
**Objection 1:** *Assume this design fails in production due to unstructured `Counterparties` fields.* The sample has raw strings like `PAY TO SAE-FOO, S*******`, `(FOREIGN TXN FEE) GRABPAY-EC`, and `CASH TOPUP - 711`. Regular SQL isn't going to reliably handle these anomalies.
**Objection 2:** *Assume duplicate transaction references exist across files.* What happens if `txn_ref_no` resets per month? The idempotency logic fails.

### 2. Constraint Guardian Agent
**Constraint 1 (Performance):** Bulk upserting Cypher graphs on large datasets row-by-row via psycopg is notoriously slow and locks tables.
**Constraint 2 (Maintainability):** Adding `dbt` and Dagster into one container image creates a bloated image and tight coupling. Let's simplify.

### 3. User Advocate Agent
**Observation 1:** Analysts running this ETL locally via Docker Compose will get overwhelmed if there's no visible UI describing the failure dead-letter queue.
**Observation 2:** The pipeline needs strict mapping for JFIU reporting fields later. Clean `txn_country` and `Txn Type` values are critical.

---

## Phase 3: Integration & Arbitration (Arbiter)

### Resolutions & Decision Log

| Decision Made | Alternatives Considered | Objections Raised | Resolution & Rationale |
| :--- | :--- | :--- | :--- |
| **Python Regex Parsing Over pure SQL/dbt** | Normalize counterparts purely using dbt/SQL macros. | Skeptic Obj 1: SQL text parsing is fragile for complex, evolving string formats. | **Accept Objection.** Python/Polars will execute cleaning rules (e.g., stripping `PAY TO`, masking names) *before* bulk loading to PostgreSQL staging, rather than using dbt for regex. |
| **Composite Primary Key** | Use `txn_ref_no` exclusively. | Skeptic Obj 2: `txn_ref_no` resets per file and is not globally unique. | **Accept Objection.** Composite key: SHA256 hash of `customer num` + `txn_date` + `txn_ref_no` + `txn_currency_amount` as the primary idempotent key. |
| **AGE Graph Upsert Strategy** | Row-by-row Cypher `MERGE`. | Constraint Guardian 1: Row-by-row is too slow. | **Accept Objection.** We will generate optimal batch Cypher blocks or build a mapping table within Postgres to load AGE quickly on the database side. |
| **Container Architecture** | Combine dbt, Dagster, PostgreSQL into one monolith. | Constraint Guardian 2: Bloated container. | **Partial Reject.** The spec mandates a "deployable container set" (Docker Compose). We will use a 3-container `docker-compose.yml`: 1) PostgreSQL+AGE, 2) Dagster Daemon + UI (ETL Worker), 3) User app backend. No dbt—transforms handled in Python/Polars. |
| **Dead Letter Queue (DLQ)** | Drop bad rows silently. | User Advocate 1: Silent failures frustrate analysts. | **Accept Objection.** Python pipeline will write unparseable rows to a `raw.wallet_ledger_dlq` table and emit Dagster asset warnings. |

---

> [!IMPORTANT]
> **Arbiter Final Disposition: APPROVED WITH REVISIONS.** The original design relied on dbt, but we've pivoted to pure Python/Polars for heavy lifting before hitting PostgreSQL, guaranteeing a cleaner Graph injection.

---

## Final Proposed Changes

### Docker / Infrastructure
#### [NEW] `docker-compose.etl.yml` (or integrated into main)
Defines the `postgres-age` and `dagster-etl` containers. 
*Note: A custom Dockerfile `Dockerfile.etl` will bundle python 3.12, polars, and dagster.*

### Extraction & Transformation (Python/Polars)
#### [NEW] `etl/repo.py`
Dagster execution entry point defining the pipeline assets.

#### [NEW] `etl/assets/ledger_ingest.py`
Dagster pipeline orchestrating extraction.
- **Extract:** Read `sample_6_customers_TXN_202510.csv.csv`.
- **Cleanse:** Polars code isolating counterparty names (strip "PAY TO", "CASH TOPUP"), standardizing `Txn Type` (FIAT, ERC-20, WIRE).
- **Load Relational:** Upsert to `core.transactions` and `core.counterparties`.

#### [NEW] `etl/assets/graph_projection.py`
- Read newly committed relations.
- Generate valid Edge/Vertex CSVs or Cypher queries.
- Update Apache AGE `tap_and_go_network` graph using PostgreSQL native drivers.

### SQL Init
#### [NEW] `etl/sql/init_schema.sql`
Defines `raw`, `stg`, and `core` tables, creates the AGE extension, and initializes the graph layout.

## Open Questions

> [!WARNING]
> 1. Does removing `dbt` and handling transformations inside Polars + Dagster assets (as proposed in the Arbiter's resolution) meet your expectations? It vastly reduces container bloat and simplifies orchestration for these messy strings.
> 2. Is a separate `docker-compose.etl.yml` acceptable to be separated from your main app deployment, or do you want the ETL orchestrator permanently merged into the primary Overwatch `docker-compose.yml`?

## Verification Plan

### Automated Tests
- Run the full Dagster pipeline against the provided `sample_6_customers_TXN_202510.csv.csv`.
- Query `count(*)` from PostgreSQL `core.transactions` and verify no duplicate rows exist.

### Manual Verification
- Verify the Graph edges inside PostgreSQL with a Cypher match `MATCH (a)-[r:TRANSFERRED]->(b) RETURN r LIMIT 5;` to ensure topologies represent accurately the P2P and Merchant payments.
