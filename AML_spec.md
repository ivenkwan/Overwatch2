# AML Platform: Networked Fund Flow Specification v2.0

## 1. Executive Summary
The AML Platform is a unified investigation tool for analyzing networked fund flows across traditional fiat (SWIFT) and Web3 (On-chain/Crypto) environments. It leverages a hybrid Relational-Graph architecture to detect complex money laundering typologies and provide analysts with interactive visual investigation capabilities.

---

## 2. Technical Stack
- **Backend**: Python 3.12+ / FastAPI (Modular N-Tier Architecture)
- **Database**: PostgreSQL 16+ with **Apache AGE** (openCypher extension)
- **Frontend**: Next.js 15 (App Router) + TypeScript
- **Styling**: Tailwind CSS + Shadcn/UI
- **Graph Visualization**: Cytoscape.js with custom layout engines
- **Infrastructure**: Docker Compose (Local Dev) / Kubernetes (Target)

---

## 3. Core Functional Requirements

### 3.1 Data Ingestion & Normalization
- **T+1 Batch Processing**: Ingest daily records for Fiat (SWIFT) and Crypto (On-chain).
- **Unified Schema**: Map disparate data sources to a single property graph:
  - **Nodes**: `Entity` (Account/Wallet/Legal Entity), `SuperNode` (Exchanges/Hot Wallets/Omnibus).
  - **Edges**: `Transfer` (amount_usd, timestamp, asset_id, flow_type).
- **Regulatory Gate**: Pre-graph screening against OFAC, FATF, and internal blocklists.

### 3.2 Automated Analytics (Cypher Rule Engine)
- **Rule execution**: Daily batch run of openCypher templates:
  - **Circular Flow**: Detection of 2-5 hop cycles back to origin.
  - **Smurfing**: Aggregated layering of sub-$10k transfers.
  - **Rapid Movement**: Money mule forwarding (>90% of incoming funds within window).
- **Alert Queue**: Persistence of hits into relational `alerts` table with priority scoring.

### 3.3 Investigation Workspace (Frontend)
- **Unified Alert Dashboard**: 
  - Prioritized queue of flagged entities and transactions.
  - State management (OPEN, UNDER_REVIEW, CLOSED, ESCALATED).
- **Visual Graph Explorer**: 
  - Dynamic expansion of node neighborhoods (up to 5 degree depth).
  - Contextual metadata overlays on nodes/edges.
  - Evidence export (graph screenshots/JSON).

---

## 4. Non-Functional Requirements

### 4.1 Security & Compliance
- **Audit Logging**: Every read, expansion, or keyword search must be logged in the evidentiary audit trail.
- **RBAC**: Strict role separation (Viewer, Reviewer, Senior Investigator, Admin).
- **Data Privacy**: PII masking for unauthorized roles.

### 4.2 Performance
- **Query Capping**: Enforce 30s timeout on Graph/Cypher traversals to prevent DB stall.
- **Super-Node Handling**: Automatically exclude designated `SuperNode` hubs from large-scale cycle detection.
- **Frontend Responsiveness**: Progressive loading of graph data to ensure smooth zooming/panning ($<$100ms UI interactions).

---

## 5. Deployment & Operations
- **Initialization**: Automated SQL scripts for PostgreSQL/AGE schema setup.
- **Monitoring**: Health endpoints for API and DB connection pool state.
- **DLQ**: Dead Letter Queue implementation for failed ETL rows.
