# AML Data Model — Fiat & Stablecoin Transactions
### Hong Kong Regulatory Compliant | T+1 Batch + Real-Time | Network Graph + KPI Daily Summary

> **Regulatory Basis:**  
> AMLO Cap.615 · Stablecoins Ordinance Cap.656 (eff. 1 Aug 2025) · HKMA AML/CFT Guideline  
> HKMA Thematic Review Apr 2024 · JFIU STREAMS 2 · FATF Travel Rule (AMLO Sch.2 s.13A)

---

## Table of Contents
1. [Schema Overview](#schema-overview)
2. [Full Data Model Diagram](#full-data-model-diagram)
3. [Processing Flow Architecture](#processing-flow-architecture)
4. [Network Graph Layer](#network-graph-layer)
5. [KPI Daily Summary Aggregation](#kpi-daily-summary-aggregation)
6. [Table Quick Reference](#table-quick-reference)
7. [Graph Analytics Queries (Apache AGE)](#graph-analytics-queries-apache-age)

---

## Schema Overview

| Schema | Domain | Tables | Purpose |
|---|---|---|---|
| `aml_core` | KYC, Accounts, Transactions | 9 | Customer registry, fiat + stablecoin txns, Travel Rule |
| `aml_detection` | Screening, Scenarios, Alerts | 4 | Detection engine, sanctions screening, alert lifecycle |
| `aml_case_mgmt` | Cases, STR, Activity | 6 | Investigation workflow, JFIU STREAMS 2 STR filing |
| `aml_graph` | Network Graph | 7 | Apache AGE-compatible graph analytics layer |
| `aml_reporting` | KPI, Batch, Daily Summary | 6 | HKMA KPI dashboard, per-rail breakdown, heatmap |
| `aml_audit` | Users, Audit Log | 2 | Immutable audit trail, RBAC (MLRO/Analyst/Supervisor) |

**Total: 34 tables across 6 schemas**

---

## Full Data Model Diagram

The diagram below renders all **34 tables** with field-level detail across all 6 schema domains,
plus four annotated processing flow lanes: Real-Time, T+1 Batch, Graph Analytics, and KPI Daily Summary.

> 💡 **Rendering tip:** Paste into [mermaid.live](https://mermaid.live) or use the VS Code
> Mermaid Preview extension for best results.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'primaryColor': '#1a1a2e', 'primaryTextColor': '#e0e0e0',
  'primaryBorderColor': '#4a90d9', 'lineColor': '#6db3f2',
  'secondaryColor': '#16213e', 'tertiaryColor': '#0f3460',
  'mainBkg': '#1a1a2e', 'clusterBkg': '#0f3460',
  'titleColor': '#6db3f2', 'edgeLabelBackground': '#16213e',
  'fontFamily': 'Segoe UI, sans-serif'
}}}%%
flowchart TD

%% ══════════════════════════════════════════════════════════════
%% AML DATA MODEL — FIAT & STABLECOIN (HK Regulatory Compliant)
%% AMLO Cap.615 · Stablecoins Ord Cap.656 · HKMA AML/CFT Guideline
%% T+1 Batch + Real-Time | Network Graph | KPI Daily Summary
%% ══════════════════════════════════════════════════════════════

subgraph CORE["🏛️  aml_core — KYC · Accounts · Transactions"]
  direction TB

  subgraph KYC["KYC Domain"]
    PARTY["<b>party</b>
─────────────────────
party_id PK
party_type INDIVIDUAL|CORPORATE|FI|TRUST
full_name
hkid_passport_no
nationality_code · country_of_residence
customer_risk_rating LOW|MED|HIGH|PEP|SANCTIONED
is_pep · is_sanctioned · sanctions_list_ref
is_beneficial_owner_identified
onboarding_channel FACE_TO_FACE|REMOTE|iAM_SMART
cdd_last_reviewed_at · edd_required_at
is_active · created_at"]

    PARTY_DOC["<b>party_document</b>
─────────────────────
doc_id PK · party_id FK
doc_type HKID|PASSPORT|BR|CI|POA
doc_number · expiry_date
issuing_country · is_verified · verified_at"]

    PARTY_REL["<b>party_relationship</b>
─────────────────────
rel_id PK
party_id_from FK · party_id_to FK
relationship_type DIRECTOR|SHAREHOLDER
BENEFICIAL_OWNER|GUARANTOR|TRUSTEE
ownership_percentage
effective_from · effective_to"]

    WATCHLIST["<b>watchlist_entry</b>
─────────────────────
watchlist_id PK
list_type OFAC_SDN|UNSC|EU|HMT
HKMA_SANCTIONED|PEP_GLOBAL|PEP_HK
listed_name · alias_names
entity_type · listing_date · is_active
last_synced_at"]
  end

  subgraph ACCTS["Account Domain"]
    ACCOUNT["<b>account</b>
─────────────────────
account_id PK
account_type CURRENT|SAVINGS|SVF
STABLECOIN_WALLET|CRYPTO_WALLET
account_rail FIAT|STABLECOIN
currency_code HKD|USD|USDT|USDC|HKDG
institution_code BIC|LEI
account_status ACTIVE|DORMANT|FROZEN|CLOSED
account_risk_rating · current_balance
blockchain_address
blockchain_network ETH|TRON|BNB|POLYGON
wallet_custody_type HOSTED|UNHOSTED|EXCHANGE"]

    ACCT_PARTY["<b>account_party_link</b>
─────────────────────
link_id PK
account_id FK · party_id FK
role OWNER|JOINT_HOLDER
AUTHORISED_SIGNATORY|BENEFICIARY
effective_from · effective_to"]
  end

  subgraph TXNS["Transaction Domain"]
    TXN["<b>transaction</b>  ← PARTITIONED by initiated_at
─────────────────────
txn_id PK · txn_reference
txn_rail FIAT|STABLECOIN
txn_channel SWIFT|CHATS|FPS|JETCO|ACH|BLOCKCHAIN|SVF
txn_type CREDIT|DEBIT|TRANSFER|MINT|REDEEM|SWAP|BURN
originator_account_id FK · beneficiary_account_id FK
originator_party_id FK · beneficiary_party_id FK
txn_amount · txn_currency
hkd_equivalent_amount  ← normalised for thresholds
txn_status PENDING|COMPLETED|FAILED|HELD|BLOCKED
initiated_at · settled_at
originator_country · beneficiary_country
is_cross_border · purpose_code
processing_mode REALTIME|BATCH
is_aml_processed · ingestion_timestamp"]

    SC_DETAIL["<b>stablecoin_txn_detail</b>
─────────────────────
sc_txn_id PK · txn_id FK UNIQUE
blockchain_tx_hash
originator_wallet_address
beneficiary_wallet_address
block_number · token_standard ERC-20|TRC-20|BEP-20
token_amount · token_symbol USDT|USDC|HKDG
is_unhosted_wallet_involved
ba_risk_score 0-100
ba_provider CHAINALYSIS|ELLIPTIC|TRM
ba_risk_flags MIXER|DARKNET|RANSOMWARE
on_chain_timestamp"]

    TRAVEL_RULE["<b>travel_rule_record</b>  ← AMLO Sch.2 s.13A
─────────────────────
travel_rule_id PK · txn_id FK UNIQUE
compliance_status COMPLIANT|MISSING_DATA|PENDING|FAILED
originator_name · originator_account_ref
originator_address · originator_cid_number
beneficiary_name · beneficiary_account_ref
beneficiary_institution_lei
above_hkd8000_threshold  ← zero-threshold approach
data_transmission_protocol IVMS101|TRISA|OPENVASP
transmitted_at · missing_fields_list[]"]
  end
end

subgraph DETECT["🔍  aml_detection — Screening · Scenarios · Alerts"]
  direction TB

  SCREENING["<b>screening_result</b>
─────────────────────
screening_id PK
txn_id FK · party_id FK · account_id FK
screen_type SANCTIONS|PEP|ADVERSE_MEDIA
BLOCKCHAIN_RISK|HIGH_RISK_COUNTRY
screen_mode REALTIME|BATCH
match_status NO_MATCH|POTENTIAL_MATCH
CONFIRMED_MATCH|FALSE_POSITIVE
match_score 0-100 · matched_name
review_decision CLEARED|ESCALATED|BLOCKED
screened_at · reviewed_at"]

  SCENARIO["<b>detection_scenario</b>
─────────────────────
scenario_id PK · scenario_code
scenario_category STRUCTURING|LAYERING
PLACEMENT|TRAVEL_RULE_BREACH
BLOCKCHAIN_RISK|UNHOSTED_WALLET
VELOCITY|PEP_MONITORING
applicable_rail FIAT|STABLECOIN|BOTH
processing_mode REALTIME|BATCH|BOTH
threshold_config JSONB
lookback_window_days · severity
regulatory_reference AMLO|HKMA|FATF
status ACTIVE|INACTIVE|TESTING"]

  ALERT["<b>aml_alert</b>
─────────────────────
alert_id PK · scenario_id FK
primary_txn_id FK · primary_party_id FK
alert_type TXN|CUSTOMER|NETWORK|SCREENING|TRAVEL_RULE
alert_mode REALTIME|BATCH
alert_status OPEN|UNDER_REVIEW|CLOSED_TP
CLOSED_FP|ESCALATED
alert_priority CRITICAL|HIGH|MEDIUM|LOW
risk_score 0-100 · flagged_amount_hkd
triggered_rule_detail JSONB
sla_due_at · assigned_analyst_id FK
disposition TP|FP|INCONCLUSIVE
alert_generated_at · closed_at"]

  ALERT_TXN["<b>alert_transaction_link</b>
─────────────────────
link_id PK
alert_id FK · txn_id FK
link_reason"]
end

subgraph CASES["📁  aml_case_mgmt — Cases · STR · Activity"]
  direction TB

  CASE["<b>aml_case</b>
─────────────────────
case_id PK · case_reference CASE-2025-HK-00123
primary_party_id FK
case_type INVESTIGATION|SAR_PREP|STR_FILED|EDD_REVIEW
case_status OPEN|UNDER_INVESTIGATION
PENDING_STR|STR_FILED|CLOSED
ml_typology STRUCTURING|LAYERING
CRYPTO_MIXING|DEFI_LAUNDERING|SANCTIONS_EVASION
total_flagged_amount_hkd
assigned_analyst_id FK · assigned_supervisor_id FK
str_filed · str_id FK
opened_at · sla_due_at · closed_at"]

  CASE_ALERT["<b>case_alert_link</b>
─────────────────────
link_id PK
case_id FK · alert_id FK · linked_at"]

  CASE_PARTY["<b>case_party_link</b>
─────────────────────
link_id PK · case_id FK · party_id FK
party_role SUBJECT|ASSOCIATE|COUNTERPARTY|FACILITATOR"]

  ACTIVITY["<b>case_activity_log</b>
─────────────────────
log_id PK · case_id FK
performed_by_user_id FK
activity_type CASE_CREATED|ASSIGNED|NOTE_ADDED
ESCALATED|STR_DRAFTED|STR_SUBMITTED|CLOSED
old_status · new_status · performed_at"]

  STR["<b>str_report</b>  ← JFIU STREAMS 2
─────────────────────
str_id PK · case_id FK
str_reference JFIU ref no.
str_status DRAFT|SUBMITTED|ACKNOWLEDGED
submission_channel STREAMS2_XML|WEBFORM
reporting_institution_name · LEI
subject_details name|HKID|DOB|address
suspicious_activity_description
reasons_for_suspicion SAFE approach
applicable_ordinances Cap.405|455|575
tipping_off_risk_assessed
activity_period_from · to
submitted_at · jfiu_case_ref"]

  STR_TXN["<b>str_transaction_link</b>
─────────────────────
link_id PK · str_id FK · txn_id FK"]
end

subgraph GRAPH["🕸️  aml_graph — Network Graph Exploration Layer (Apache AGE)"]
  direction TB

  subgraph GNODES["Graph Nodes"]
    G_NODE["<b>graph_node</b>
─────────────────────
node_id PK
node_type PARTY|ACCOUNT|TRANSACTION
IP_ADDRESS|DEVICE|BLOCKCHAIN_ADDRESS
INSTITUTION|LEGAL_ENTITY
node_label · source_entity_id
source_table · risk_score 0-100
node_properties JSONB
is_flagged · flagging_reason
last_updated_at"]

    G_SCORE_HIST["<b>graph_node_score_history</b>
─────────────────────
history_id PK · node_id FK
previous_score · new_score
score_delta GENERATED STORED
change_reason
changed_at · changed_by_job_id"]
  end

  subgraph GEDGES["Graph Edges"]
    G_EDGE["<b>graph_edge</b>
─────────────────────
edge_id PK
source_node_id FK · target_node_id FK
edge_type SENT_TO|RECEIVED_FROM
OWNS_ACCOUNT|CONTROLS
SAME_DEVICE|SAME_IP
BLOCKCHAIN_TX|SAME_ADDRESS
edge_weight HKD or frequency
txn_count · total_amount_hkd
hop_count · edge_properties JSONB
event_timestamp"]

    G_EDGE_AGG["<b>graph_edge_daily_agg</b>
─────────────────────
agg_id PK · business_date
source_node_id FK · target_node_id FK
edge_type · txn_count
total_amount_hkd · max_single_txn_hkd
applicable_rail FIAT|STABLECOIN"]
  end

  subgraph GCOMM["Community Detection"]
    G_COMMUNITY["<b>graph_community</b>
─────────────────────
community_id PK
community_algorithm LOUVAIN
LABEL_PROPAGATION|WEAKLY_CONNECTED
run_date · community_size
community_risk_score · max_node_risk_score
total_txn_amount_hkd
is_suspicious
investigation_status UNREVIEWED
UNDER_REVIEW|CLEARED|ESCALATED
linked_case_id FK
detected_at · reviewed_at"]

    G_NODE_COMM["<b>graph_node_community</b>
─────────────────────
gnc_id PK · node_id FK
community_id FK · membership_score"]
  end

  G_ANALYTICS["<b>graph_analytics_run</b>
─────────────────────
run_id PK
algorithm_name PAGERANK
BETWEENNESS_CENTRALITY
LOUVAIN_COMMUNITY
CYCLE_DETECTION|SHORTEST_PATH
TRIANGLE_COUNT|WEAKLY_CONNECTED
run_type BATCH|INTERACTIVE
run_date · triggered_by_alert_id
triggered_by_case_id
nodes_analysed · edges_analysed
suspicious_clusters_found
started_at · completed_at · status"]

  G_PATH["<b>graph_path_query_cache</b>
─────────────────────
query_id PK
case_id FK · alert_id FK
source_node_id FK · target_node_id FK
algorithm SHORTEST_PATH|ALL_PATHS
result_path_nodes UUID[]
result_path_edges UUID[]
result_total_weight · result_hop_count
result_json JSONB
queried_at · expires_at
is_suspicious"]
end

subgraph REPORTING["📊  aml_reporting — KPI · Batch · Daily Summary"]
  direction TB

  BATCH["<b>batch_job</b>
─────────────────────
job_id PK · job_name
job_type T1_TM_RUN|T1_SCREENING
T1_KPI_CALCULATION|T1_GRAPH_REFRESH
T1_TRAVEL_RULE_CHECK|T1_ALERT_AGING
T1_WATCHLIST_SYNC
job_status PENDING|RUNNING|COMPLETED|FAILED
batch_date T · business_date T-1
started_at · completed_at
txn_records_processed · alerts_generated"]

  KPI["<b>kpi_snapshot</b>  ← HKMA KPI Dashboard
─────────────────────
kpi_id PK · snapshot_date
kpi_period DAILY|WEEKLY|MONTHLY|QUARTERLY
applicable_rail FIAT|STABLECOIN|ALL
── Volume: active_customers, txn_count, txn_hkd ──
── Alerts HKMA mandated ──
total_alerts · alerts_realtime · alerts_batch
true_positive · false_positive · fp_rate
── STR HKMA mandated ──
total_strs_filed
str_conversion_rate STRs/productive_cases
alert_to_str_rate
── Travel Rule stablecoin ──
travel_rule_compliant · non_compliant
travel_rule_compliance_rate
── Operational ──
alert_rate_per_1000_customers
avg_alert_review_hours
sla_breach_count · sla_breach_rate
── Blockchain Risk ──
high_risk_blockchain_alerts
unhosted_wallet_alerts · calculated_at"]

  KPI_RAIL["<b>kpi_daily_rail_breakdown</b>  ← Fiat vs Stablecoin
─────────────────────
breakdown_id PK · snapshot_date
applicable_rail FIAT|STABLECOIN
txn_count · txn_total_hkd
txn_cross_border_count · txn_cross_border_hkd
txn_by_channel JSONB · txn_by_type JSONB
alerts_total · alerts_critical · alerts_high
alerts_true_positive · alerts_false_positive
travel_rule_total · travel_rule_compliant
travel_rule_above_8k
travel_rule_above_8k_non_compliant
unhosted_wallet_txns
blockchain_risk_alerts · ba_avg_risk_score
strs_filed · calculated_at"]

  KPI_HEATMAP["<b>kpi_alert_heatmap</b>
─────────────────────
heatmap_id PK · snapshot_date
alert_hour 0-23 · scenario_id FK
applicable_rail
alert_count · true_positive_count
total_amount_hkd · calculated_at"]

  SCEN_KPI["<b>scenario_kpi</b>  ← Annual Tuning Report
─────────────────────
scenario_kpi_id PK
scenario_id FK · snapshot_date · kpi_period
alerts_generated · true_positives
false_positives · false_positive_rate
strs_from_scenario
avg_risk_score · min · max
tuning_recommendation
INCREASE|DECREASE|RETIRE|NO_CHANGE"]

  REG_LOG["<b>regulatory_submission_log</b>
─────────────────────
submission_id PK
submission_type STR_STREAMS2
HKMA_TM_KPI_QUARTERLY
HKMA_ANNUAL_TUNING
STABLECOIN_QUARTERLY
reporting_period_from · to
submitted_at · regulator_ref · status"]
end

subgraph AUDIT["🔒  aml_audit — Users · Immutable Audit Trail"]
  direction LR
  USER["<b>aml_user</b>
─────────────────────
user_id PK · full_name · email
role ANALYST_L1|ANALYST_L2|SUPERVISOR
MLRO|COMPLIANCE_OFFICER
GRAPH_ANALYST|ADMIN|READONLY
is_active · last_login_at"]

  AUDIT_LOG["<b>audit_log</b>  ← partitioned by year
─────────────────────
audit_id PK · user_id FK
schema_name · table_name · record_id
action INSERT|UPDATE|DELETE|VIEW|EXPORT
old_values JSONB · new_values JSONB
ip_address · user_agent · performed_at"]
end

%% ══════════════════════════════════════════════════════════════
%% RELATIONSHIPS
%% ══════════════════════════════════════════════════════════════
PARTY -->|"has docs"| PARTY_DOC
PARTY -->|"from"| PARTY_REL
PARTY -->|"to"| PARTY_REL
PARTY -->|"via"| ACCT_PARTY
ACCOUNT -->|"via"| ACCT_PARTY
ACCOUNT -->|"originates"| TXN
ACCOUNT -->|"receives"| TXN
PARTY -->|"originator"| TXN
PARTY -->|"beneficiary"| TXN
TXN -->|"1:1"| SC_DETAIL
TXN -->|"1:1 Travel Rule"| TRAVEL_RULE
TXN -->|"screened"| SCREENING
PARTY -->|"screened"| SCREENING
WATCHLIST -.->|"matched"| SCREENING
SCENARIO -->|"triggers"| ALERT
ALERT -->|"links"| ALERT_TXN
TXN -->|"linked"| ALERT_TXN
ALERT -->|"grouped"| CASE_ALERT
CASE -->|"contains"| CASE_ALERT
CASE -->|"involves"| CASE_PARTY
PARTY -->|"subject"| CASE_PARTY
CASE -->|"activity"| ACTIVITY
CASE -->|"STR"| STR
STR -->|"references"| STR_TXN
TXN -->|"cited"| STR_TXN
TXN -.->|"node"| G_NODE
PARTY -.->|"node"| G_NODE
ACCOUNT -.->|"node"| G_NODE
SC_DETAIL -.->|"wallet node"| G_NODE
G_NODE -->|"score hist"| G_SCORE_HIST
G_NODE -->|"source"| G_EDGE
G_NODE -->|"target"| G_EDGE
G_EDGE -.->|"daily agg"| G_EDGE_AGG
G_NODE -->|"member"| G_NODE_COMM
G_COMMUNITY -->|"contains"| G_NODE_COMM
G_COMMUNITY -->|"escalate"| CASE
G_ANALYTICS -->|"detects"| G_COMMUNITY
G_PATH -->|"cached for"| CASE
SCENARIO -->|"measured"| SCEN_KPI
BATCH -->|"produces"| KPI
BATCH -->|"produces"| KPI_RAIL
BATCH -->|"refreshes"| G_NODE
ALERT -->|"aggregated"| KPI
ALERT -->|"heatmap"| KPI_HEATMAP
STR -->|"counted"| KPI
TRAVEL_RULE -->|"counted"| KPI_RAIL
SC_DETAIL -->|"risk counted"| KPI_RAIL
USER -->|"reviews"| ALERT
USER -->|"analyst"| CASE
AUDIT_LOG -->|"by"| USER

%% ══════════════════════════════════════════════════════════════
%% PROCESSING FLOWS
%% ══════════════════════════════════════════════════════════════
subgraph RT_FLOW["⚡ Real-Time Processing Path"]
  direction LR
  RT1["Transaction<br/>Ingested"] --> RT2["Sanctions<br/>Screening"] --> RT3["Travel Rule<br/>Check"] --> RT4["Blockchain<br/>Risk Score"] --> RT5["High-Value<br/>Alert"]
end

subgraph BATCH_FLOW["🕐 T+1 Batch Path  HKT: 00:00 → 06:00"]
  direction LR
  B1["00:00 Watchlist<br/>Sync"] --> B2["00:30 Re-<br/>Screening"] --> B3["01:00 TM<br/>Batch Run"] --> B4["03:00 Travel<br/>Rule Audit"] --> B5["04:00 Graph<br/>Refresh"] --> B6["05:00 KPI<br/>Calculation"] --> B7["06:00 Alert<br/>Aging"]
end

subgraph GRAPH_FLOW["🕸️ Graph Analytics Flow"]
  direction LR
  GF1["Graph<br/>Refresh"] --> GF2["Run PageRank<br/>Louvain/Cycle"] --> GF3["Detect<br/>Communities"] --> GF4["Score &<br/>Flag Suspicious"] --> GF5["Escalate<br/>to Case"]
end

subgraph KPI_FLOW["📊 KPI Daily Summary Flow"]
  direction LR
  KF1["T-1 Txns<br/>Alerts STRs"] --> KF2["fn_compute_<br/>daily_kpi"] --> KF3["kpi_snapshot<br/>ALL rails"] --> KF4["kpi_daily_rail_<br/>breakdown FIAT+SC"] --> KF5["scenario_kpi<br/>+ heatmap"] --> KF6["Dashboard<br/>RAG Status"]
end

%% ══════════════════════════════════════════════════════════════
%% STYLING
%% ══════════════════════════════════════════════════════════════
classDef coreStyle fill:#1a3a5c,stroke:#4a90d9,color:#e0f0ff,rx:6
classDef detectStyle fill:#3a1a5c,stroke:#9a4ad9,color:#f0e0ff,rx:6
classDef caseStyle fill:#1a4a2a,stroke:#4ad96a,color:#e0ffe8,rx:6
classDef graphStyle fill:#4a2a0a,stroke:#d99a4a,color:#fff0e0,rx:6
classDef reportStyle fill:#3a2a0a,stroke:#d9c44a,color:#fffce0,rx:6
classDef auditStyle fill:#3a0a0a,stroke:#d94a4a,color:#ffe0e0,rx:6
classDef flowStyle fill:#0a2a3a,stroke:#4ac4d9,color:#e0f8ff,rx:4

class PARTY,PARTY_DOC,PARTY_REL,WATCHLIST,ACCOUNT,ACCT_PARTY,TXN,SC_DETAIL,TRAVEL_RULE coreStyle
class SCREENING,SCENARIO,ALERT,ALERT_TXN detectStyle
class CASE,CASE_ALERT,CASE_PARTY,ACTIVITY,STR,STR_TXN caseStyle
class G_NODE,G_SCORE_HIST,G_EDGE,G_EDGE_AGG,G_COMMUNITY,G_NODE_COMM,G_ANALYTICS,G_PATH graphStyle
class BATCH,KPI,KPI_RAIL,KPI_HEATMAP,SCEN_KPI,REG_LOG reportStyle
class USER,AUDIT_LOG auditStyle
class RT1,RT2,RT3,RT4,RT5,B1,B2,B3,B4,B5,B6,B7,GF1,GF2,GF3,GF4,GF5,KF1,KF2,KF3,KF4,KF5,KF6 flowStyle

```

---

## Processing Flow Architecture

### Four Processing Lanes

| Lane | Trigger | Latency | Key Outputs |
|---|---|---|---|
| ⚡ Real-Time | On transaction ingestion | < 1 second | Sanctions block, Travel Rule hold, Blockchain risk alert |
| 🕐 T+1 Batch | Nightly 00:00–06:00 HKT | Overnight | Structuring alerts, velocity alerts, KPI snapshot |
| 🕸️ Graph Analytics | After T1_GRAPH_REFRESH | 04:00–05:00 HKT | Community detection, flagged clusters, node risk scores |
| 📊 KPI Daily Summary | After all T+1 jobs | 05:00–06:00 HKT | kpi_snapshot, rail breakdown, heatmap, scenario KPIs |

### T+1 Batch Schedule (HKT)

| Time | Job | Description |
|---|---|---|
| 00:00 | `T1_WATCHLIST_SYNC` | Refresh OFAC/UNSC/EU/HMT watchlist_entry |
| 00:30 | `T1_SCREENING` | Re-screen all parties against refreshed lists |
| 01:00 | `T1_TM_RUN` | Execute all BATCH-mode detection scenarios on T-1 transactions |
| 03:00 | `T1_TRAVEL_RULE_CHECK` | Audit stablecoin Travel Rule completeness |
| 04:00 | `T1_GRAPH_REFRESH` | Materialise graph nodes + edges; run community detection |
| 05:00 | `T1_KPI_CALCULATION` | `fn_compute_daily_kpi()` — upsert kpi_snapshot + breakdowns |
| 06:00 | `T1_ALERT_AGING` | Flag SLA breaches; trigger supervisor escalations |

---

## Network Graph Layer

### Architecture

The `aml_graph` schema implements a **materialised property graph** compatible with:
- **Apache AGE** (PostgreSQL graph extension) — native Cypher queries
- **pg_graph** — PL/pgSQL traversal functions
- External export to **Neo4j** (via BOLT protocol connectors)

Graph nodes and edges are populated nightly by `fn_refresh_graph_nodes()` and
`fn_refresh_graph_edges()`, with on-demand refreshes during live case investigations.

### Node Types and Sources

| Node Type | Source Table | AML Use Case |
|---|---|---|
| `PARTY` | `aml_core.party` | Customer / UBO network mapping |
| `ACCOUNT` | `aml_core.account` | Fund flow, dormancy, layering |
| `TRANSACTION` | `aml_core.transaction` | Temporal pattern nodes |
| `BLOCKCHAIN_ADDRESS` | `stablecoin_txn_detail` | On-chain wallet clustering |
| `IP_ADDRESS` | Digital footprint | Coordinated account activity |
| `DEVICE` | Device fingerprint | Mule account ring detection |
| `INSTITUTION` | Correspondent banks | Correspondent bank risk |
| `LEGAL_ENTITY` | Corporate structure | UBO chain traversal |

### Edge Types

| Edge Type | Meaning | Weight |
|---|---|---|
| `SENT_TO` | Outgoing fund transfer | HKD amount |
| `RECEIVED_FROM` | Incoming fund transfer | HKD amount |
| `OWNS_ACCOUNT` | Party → account ownership | 1 |
| `CONTROLS` | UBO / director control | ownership % |
| `BLOCKCHAIN_TX` | On-chain stablecoin transfer | Token amount in HKD |
| `SAME_IP` / `SAME_DEVICE` | Shared digital infrastructure | Count |
| `SAME_ADDRESS` | Shared physical address | 1 |

### Graph Analytics Algorithms

| Algorithm | Batch/Interactive | AML Pattern Detected |
|---|---|---|
| Louvain Community | Batch nightly | Smurfing rings, layering networks |
| Label Propagation | Batch nightly | Fast cluster propagation |
| Weakly Connected Components | Batch nightly | Full relationship islands |
| Strongly Connected Components | Interactive | Circular fund flows |
| PageRank | Batch nightly | High-centrality hub accounts |
| Betweenness Centrality | Interactive | Intermediary / facilitator accounts |
| Shortest Path | Interactive (case trigger) | Fund flow trace between flagged parties |
| Cycle Detection | Interactive (case trigger) | Round-tripping detection |
| Triangle Count | Batch nightly | Concentrated mutual fund flows |

### Risk Score Evolution

The `graph_node_score_history` table tracks every change to a node's risk score with the
delta stored as a **generated computed column** (`score_delta GENERATED ALWAYS AS (new_score - COALESCE(previous_score, 0)) STORED`).
This feeds the `v_node_risk_trend` view, surfacing nodes whose risk has deteriorated significantly
— a key HKMA indicator of an emerging AML risk requiring EDD review.

---

## KPI Daily Summary Aggregation

### fn_compute_daily_kpi() — Idempotent Daily Function

The main computation function populates **four tables** in a single call:

```
fn_compute_daily_kpi(p_business_date := CURRENT_DATE - 1)
  ├─► kpi_snapshot          (ALL rails combined)          ← UPSERT
  ├─► kpi_daily_rail_breakdown (FIAT row + STABLECOIN row) ← UPSERT
  ├─► scenario_kpi          (per detection scenario)       ← UPSERT
  └─► kpi_alert_heatmap     (per scenario per hour)        ← UPSERT
```

The function is fully idempotent via `ON CONFLICT DO UPDATE`, so it can be safely
re-run if the batch job fails mid-execution.

### HKMA-Mandated KPI Fields

| KPI | Table.Column | Regulatory Reference |
|---|---|---|
| Active customer count | `kpi_snapshot.total_active_customers` | HKMA Apr 2024 TM Review |
| Total alerts generated | `kpi_snapshot.total_alerts_generated` | HKMA Apr 2024 TM Review |
| True positive alerts | `kpi_snapshot.true_positive_alerts` | HKMA Apr 2024 TM Review |
| **False positive rate** | `kpi_snapshot.false_positive_rate` | HKMA Apr 2024 TM Review |
| **STR conversion rate** | `kpi_snapshot.str_conversion_rate` | HKMA Apr 2024 TM Review |
| Alert rate per 1,000 customers | `kpi_snapshot.alert_rate_per_1000_customers` | HKMA Apr 2024 TM Review |
| Travel Rule compliance rate | `kpi_snapshot.travel_rule_compliance_rate` | AMLO Sch.2 s.13A / Cap.656 |
| SLA breach rate | `kpi_snapshot.sla_breach_rate` | HKMA operational requirement |

### Per-Rail Stablecoin KPIs (Cap.656, Aug 2025)

| KPI | Table.Column |
|---|---|
| Travel Rule: above HKD 8,000 non-compliant | `kpi_daily_rail_breakdown.travel_rule_above_8k_non_compliant` |
| Unhosted wallet transactions | `kpi_daily_rail_breakdown.unhosted_wallet_txns` |
| Average blockchain analytics risk score | `kpi_daily_rail_breakdown.ba_avg_risk_score` |
| Blockchain risk alerts | `kpi_daily_rail_breakdown.blockchain_risk_alerts` |

### Traffic Light RAG in v_daily_kpi_dashboard

The `v_daily_kpi_dashboard` view adds automatic RED/AMBER/GREEN status:

| KPI | GREEN | AMBER | RED |
|---|---|---|---|
| False Positive Rate | < 80% | 80–95% | > 95% |
| Travel Rule Compliance | ≥ 99% | 95–99% | < 95% |
| SLA Breach Rate | < 5% | 5–10% | > 10% |

### Alert Heatmap

The `kpi_alert_heatmap` table records alert counts by **hour of day × detection scenario**,
enabling analysts to identify intraday patterns (e.g., structuring alerts clustering around
business open/close, stablecoin blockchain alerts clustering at night when manual review
is reduced).

---

## Table Quick Reference

### aml_core (9 tables)

| Table | Partition | Est. Rows | Key Indexes |
|---|---|---|---|
| `party` | None | 1M–10M | risk_rating, is_pep, name (trgm) |
| `party_document` | None | 2M–30M | party_id |
| `party_relationship` | None | 500K–5M | party_id_from, party_id_to |
| `watchlist_entry` | None | 100K–1M | listed_name (trgm), list_type |
| `account` | None | 2M–20M | account_rail, blockchain_address |
| `account_party_link` | None | 3M–25M | account_id, party_id |
| `transaction` | Monthly by initiated_at | 10M–1B/yr | originator_party_id, hkd_amount |
| `stablecoin_txn_detail` | None | 1M–100M/yr | tx_hash, ba_risk_score, wallets |
| `travel_rule_record` | None | 1M–100M/yr | compliance_status |

### aml_graph (7 tables)

| Table | Refresh | Est. Rows |
|---|---|---|
| `graph_node` | Nightly T1_GRAPH_REFRESH | 5M–500M |
| `graph_node_score_history` | On risk score change | 10M–1B |
| `graph_edge` | Nightly T1_GRAPH_REFRESH | 50M–5B |
| `graph_edge_daily_agg` | Nightly, per business day | 1M–100M/day |
| `graph_community` | Post-algorithm run | 10K–1M |
| `graph_node_community` | Post-algorithm run | 50M–5B |
| `graph_analytics_run` | Per run log | Small |
| `graph_path_query_cache` | On interactive query | Small (24h TTL) |

### aml_reporting (6 tables)

| Table | Populated By | Granularity |
|---|---|---|
| `batch_job` | Each batch job start/end | Per run |
| `kpi_snapshot` | fn_compute_daily_kpi | DAILY/WEEKLY/MONTHLY/QUARTERLY |
| `kpi_daily_rail_breakdown` | fn_compute_daily_kpi | DAILY × FIAT/STABLECOIN |
| `kpi_alert_heatmap` | fn_compute_daily_kpi | DAILY × hour × scenario |
| `scenario_kpi` | fn_compute_daily_kpi | DAILY per scenario |
| `regulatory_submission_log` | Manual / STR workflow | Per submission |

---

## Graph Analytics Queries (Apache AGE)

### Setup

```sql
LOAD 'age';
SET search_path = ag_catalog, "$user", public;
```

### Q1: 3-hop traversal from flagged party

```sql
SELECT * FROM cypher('aml_graph', $$
  MATCH path = (flagged:graph_node {is_flagged: true})
               -[:graph_edge*1..3]->
               (connected:graph_node)
  WHERE connected.node_type IN ['ACCOUNT', 'BLOCKCHAIN_ADDRESS']
  RETURN connected.node_label AS node,
         connected.risk_score AS risk,
         length(path)         AS hops
  ORDER BY connected.risk_score DESC
  LIMIT 50
$$) AS (node agtype, risk agtype, hops agtype);
```

### Q2: Round-trip cycle detection (round-tripping / circular layering)

```sql
SELECT * FROM cypher('aml_graph', $$
  MATCH cycle = (origin:graph_node)-[:graph_edge*2..6]->(origin)
  WHERE origin.node_type = 'ACCOUNT'
  WITH origin,
       length(cycle) AS cycle_length,
       reduce(total=0, e IN relationships(cycle) | total + e.edge_weight) AS total_hkd
  WHERE total_hkd > 100000
  RETURN origin.node_label AS account,
         cycle_length,
         total_hkd
  ORDER BY total_hkd DESC
$$) AS (account agtype, cycle_length agtype, total_hkd agtype);
```

### Q3: Identify hub accounts by weighted PageRank

```sql
-- After running PageRank algorithm and storing results in node_properties
SELECT node_id, node_label, node_type, risk_score,
       (node_properties->>'pagerank_score')::NUMERIC AS pagerank
FROM aml_graph.graph_node
WHERE node_properties ? 'pagerank_score'
ORDER BY (node_properties->>'pagerank_score')::NUMERIC DESC
LIMIT 20;
```

### Q4: Smurfing ring detection (multiple senders → single receiver)

```sql
SELECT * FROM cypher('aml_graph', $$
  MATCH (sender:graph_node)-[e:graph_edge]->(receiver:graph_node)
  WHERE e.edge_type = 'SENT_TO'
    AND receiver.node_type = 'ACCOUNT'
  WITH receiver,
       count(DISTINCT sender) AS sender_count,
       sum(e.total_amount_hkd) AS total_received_hkd
  WHERE sender_count >= 5 AND total_received_hkd >= 500000
  RETURN receiver.node_label AS receiving_account,
         sender_count,
         total_received_hkd
  ORDER BY total_received_hkd DESC
$$) AS (receiving_account agtype, sender_count agtype, total_received_hkd agtype);
```

---

## Extensions Required

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- UUID primary keys
CREATE EXTENSION IF NOT EXISTS "pg_trgm";     -- Fuzzy name matching (sanctions)
CREATE EXTENSION IF NOT EXISTS "btree_gin";   -- Composite GIN indexes
-- Optional: Apache AGE for native Cypher queries
-- CREATE EXTENSION IF NOT EXISTS age;
```

---

## Files in This Package

| File | Description | Lines |
|---|---|---|
| `aml_data_model_full.md` | This file — embedded Mermaid + full documentation | ~600 |
| `aml_data_model_full.mmd` | Standalone Mermaid diagram file | ~534 |
| `aml_ddl_postgresql.sql` | Base DDL — all core tables, indexes, triggers, views | ~1,256 |
| `aml_ddl_extension.sql` | Extension DDL — graph tables, KPI functions, extended views | ~990 |

> Apply DDL in order: `aml_ddl_postgresql.sql` → `aml_ddl_extension.sql`

---

*Generated: April 2026 | Regulatory references current as of HKMA Apr 2024 Thematic Review
and Stablecoins Ordinance Cap.656 (effective 1 August 2025)*
