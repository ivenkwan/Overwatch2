# Production ETL Pipeline: Dagster Operations Guide

This document outlines the architecture, data flow, and operational procedures for the Overwatch Production ETL Pipeline. This pipeline orchestrates the ingestion of raw financial ledgers into an optimized Apache AGE graph database for anti-money laundering (AML) network analysis.

## Overview

The daily production process is orchestrated asynchronously via **Dagster** (`etl_pipeline`). It handles data cleaning, hashing (idempotency key generation), normalizing into PostrgreSQL relational tables, and finally projecting those tables into an advanced Graph schema (`tap_and_go_network`).

## ETL Data Flow Architecture

The data pipeline runs in multiple defined asset steps:

1. **`raw_ledger_data`**: Loads unshaped CSV output containing raw fiat transaction data and standardizes primary column namings (e.g., `customer num` -> `customer_num`).
2. **`cleaned_ledger_data`**: Enriches the dataset by assigning unique deterministic SHA-256 hashes for idempotency (`txn_hash`), cleaning string prefixes (e.g., removing `PAY TO` from counterparties), and filtering null transactions.
3. **`load_relational_tables`**: Normalizes the in-memory Polars DataFrame into standard PostgreSQL `core` DDL structures.
4. **`update_age_graph`**: Executes idempotent Cypher queries using a PL/pgSQL loop to sink the relational records into graph Vertices and Edges.

## Relational to Graph Schema Mapping

The following schema demonstrates the projection logic handled during the `update_age_graph` phase.

```mermaid
erDiagram
    %% Relational Core Tables
    CORE_CUSTOMERS {
        string customer_num PK
    }
    CORE_COUNTERPARTIES {
        string counterparty_id PK
        string counterparty_name
        boolean is_merchant
    }
    CORE_TRANSACTIONS {
        string txn_hash PK
        string customer_num FK
        string counterparty_id FK
        string txn_date
        string cdi_code
        float txn_amount_in_hkd
    }

    %% Graph Entity Mapping (Apache AGE)
    GRAPH_CUSTOMER {
        Customer id
    }
    GRAPH_COUNTERPARTY {
        Counterparty id
    }
    GRAPH_MERCHANT {
        Merchant id
    }

    %% Mappings
    CORE_CUSTOMERS ||--o{ GRAPH_CUSTOMER : "MERGE (n:Customer)"
    CORE_COUNTERPARTIES ||--o{ GRAPH_MERCHANT : "MERGE (m:Merchant) IF is_merchant"
    CORE_COUNTERPARTIES ||--o{ GRAPH_COUNTERPARTY : "MERGE (n:Counterparty) IF NOT is_merchant"

    %% Edge Generation Logic
    CORE_TRANSACTIONS ||--o{ GRAPH_CUSTOMER : "cdi_code = 'D'"
    CORE_TRANSACTIONS ||--o{ GRAPH_COUNTERPARTY : "cdi_code = 'C'"
```

### Graph Edge Resolution (Cypher Injection)
- **Customer to Merchant (Debit):** `(Customer)-[PAID]->(Merchant)`
- **Customer to P2P Counterparty (Debit):** `(Customer)-[TRANSFERRED]->(Counterparty)`
- **Counterparty to Customer (Credit):** `(Counterparty)-[TRANSFERRED]->(Customer)`

## Environment & Run Definitions

The ETL orchestration relies directly on the standard Postgres environment exposed by `age_db`.
* **Database Target**: `postgresql://postgres:password@age_db:5432/age_prod_01` (Inside Docker network).
* **Execution Module**: `z:/GITHUB/Overwatch/etl/repo.py`

> [!TIP]
> The scripts are resilient to local dev environments vs containers. If running via native python, connections inherently fallback to `localhost:5432` if the Docker upstream isn't reachable via DNS.

## Operational Procedures

To run the pipeline natively using the Dagster UI:
1. Initialize the ETL virtual environment.
2. Execute `dagster dev -h 0.0.0.0 -p 3000` to boot the web server.
3. Using the web interface (at `localhost:3000`), trigger a **Materialize All** operation on the unified layout.
