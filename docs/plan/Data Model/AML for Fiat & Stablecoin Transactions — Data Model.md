# AML Data Model: Fiat & Stablecoin Transactions
### Hong Kong Regulatory Compliant | T+1 Batch + Real-Time | Network Graph Exploration
---
## Executive Summary
This data model provides a production-grade Anti-Money Laundering (AML) infrastructure for financial institutions supervised by the Hong Kong Monetary Authority (HKMA). It spans both traditional fiat payment rails and stablecoin/crypto rails, supports both real-time and T+1 batch detection modes, and implements all mandatory KPI measures and reporting obligations required under Hong Kong law.

The model is anchored in:
- **AMLO Cap.615** — the Anti-Money Laundering and Counter-Terrorist Financing Ordinance[^1]
- **Stablecoins Ordinance Cap.656** — effective 1 August 2025, establishing a licensing regime for fiat-referenced stablecoin issuers supervised by the HKMA[^2][^3]
- **HKMA AML/CFT Guideline** (Chapter 5 — Transaction Monitoring Systems)[^4]
- **HKMA Thematic Review** (April 2024) — KPI and optimisation requirements[^5]
- **JFIU STREAMS 2** — mandatory electronic STR filing regime[^6]
- **FATF Travel Rule** — implemented in HK via AMLO Schedule 2, Section 13A[^7][^8]

***
## Regulatory Architecture
### Hong Kong AML/CFT Legal Framework
The HKMA and HKAB published updated AML/CFT FAQs on 30 December 2024, clarifying operational requirements under the existing AML/CFT Guideline. Three categories of HKMA-supervised institutions now carry AML/CFT obligations: Authorized Institutions (conventional and digital banks), Stored Value Facility (SVF) licensees, and — as of August 2025 — Licensed Stablecoin Issuers.[^1][^9]

The HKMA's April 2024 thematic review established that AIs must maintain KPIs including numbers of active customers, alerts and productive cases, and the STR conversion rate, reported quarterly to the AML oversight committee. Annual tuning reports must be compiled to identify enhancements to detection scenarios, thresholds, and customer segments.[^5]
### Travel Rule — Zero Threshold for Stablecoins
Unlike jurisdictions that set minimum thresholds for Travel Rule compliance, Hong Kong takes a zero-threshold approach: Travel Rule compliance is required for every stablecoin transfer, no matter the value. For transfers above HKD 8,000, institutions must obtain and transmit verified originator and beneficiary information including name, account reference, address, and customer identification number. This is implemented in the `travel_rule_record` table with the `above_hkd8000_threshold` flag and `missing_fields_list` column.[^7]
### STR Reporting — JFIU STREAMS 2
Any person who knows or suspects that property represents proceeds of crime or terrorist property must disclose that knowledge or suspicion to the JFIU as soon as reasonably practicable. There is no monetary threshold for STR filing in Hong Kong, and cross-border reporting obligations apply without limit. All STRs must be submitted electronically through STREAMS 2 — the e-reporting system operated by the Joint Financial Intelligence Unit. Failure to report is a criminal offence carrying a maximum penalty of a HKD 50,000 fine and three months' imprisonment.[^10][^6][^11][^12]

***
## Data Model Architecture
The model is organised into **6 PostgreSQL schemas** separating concerns across functional domains.

| Schema | Purpose | Key Tables |
|---|---|---|
| `aml_core` | KYC, accounts, transactions | `party`, `account`, `transaction`, `stablecoin_txn_detail`, `travel_rule_record` |
| `aml_detection` | Screening, scenarios, alerts | `screening_result`, `detection_scenario`, `aml_alert` |
| `aml_case_mgmt` | Cases, STR, activity logs | `aml_case`, `str_report`, `case_activity_log` |
| `aml_reporting` | Batch jobs, KPI snapshots | `batch_job`, `kpi_snapshot`, `scenario_kpi` |
| `aml_graph` | Network graph exploration | `graph_node`, `graph_edge`, `graph_community` |
| `aml_audit` | Immutable audit trail | `aml_user`, `audit_log` |

| Domain                      | Entities                                         |
| --------------------------- | ------------------------------------------------ |
| KYC / Party                 | `PARTY`, `BENEFICIAL_OWNER`, `PEP_RECORD`        |
| Core Banking / Fiat         | `ACCOUNT`, `FIAT_TRANSACTION`, `WIRE_TRANSFER`   |
| Virtual Asset / Stablecoin  | `WALLET`, `VA_TRANSACTION`, `TRAVEL_RULE_RECORD` |
| AML Detection               | `DETECTION_RULE`, `SANCTIONS_SCREENING`, `ALERT` |
| Case / Regulatory Reporting | `CASE_RECORD`, `STR_REPORT`, `AUDIT_LOG`         |

***
## Section 1: Core Party & KYC Domain
### party
The central customer registry satisfying HKMA Customer Due Diligence (CDD) requirements under the AML/CFT Guideline Chapter 2. Key design decisions:

- `customer_risk_rating` ENUM: `LOW | MEDIUM | HIGH | PEP | SANCTIONED` — supports risk-based threshold segmentation per HKMA guidance[^5]
- `is_pep` flag: Politically Exposed Persons require Enhanced Due Diligence (EDD) and senior management approval for relationships[^13]
- `onboarding_channel`: includes `iAM_SMART` per the December 2024 HKMA/HKAB FAQ clarifications[^1]
- `cdd_last_reviewed_at` / `edd_required_at`: tracks periodic CDD review obligations
- Full-text fuzzy search index using `pg_trgm` for name screening performance
### party_relationship
Maps beneficial ownership, corporate structure, and UBO chains. The `ownership_percentage` field and `relationship_type` ENUM (`DIRECTOR`, `SHAREHOLDER`, `BENEFICIAL_OWNER`) supports the HKMA's beneficial ownership identification requirements clarified in the December 2024 FAQ. This table also feeds the graph layer for UBO traversal queries.[^1]
### watchlist_entry
Consolidated watchlist reference data covering OFAC SDN, UNSC Consolidated, EU Consolidated, HMT, HKMA sanctioned entities, Interpol, and PEP databases (both global and HK-specific). The `last_synced_at` field supports daily automated watchlist refresh via the `T1_WATCHLIST_SYNC` batch job type.

***
## Section 2: Account Domain
The `account` table uses a unified design covering fiat accounts (CURRENT, SAVINGS, FIXED_DEPOSIT, LOAN), SVF wallets (HKMA-licensed Stored Value Facilities), and stablecoin/crypto wallets.

Stablecoin-specific fields follow HKMA guidance on customer wallet CDD:[^9]
- `blockchain_address`: on-chain wallet address for Travel Rule and blockchain analytics
- `wallet_custody_type`: `HOSTED | UNHOSTED | EXCHANGE_CUSTODIED | MULTI_SIG` — critical for HKMA's enhanced requirements for transactions involving unhosted wallets
- `is_hosted_wallet`: drives scenario `SCN_UNHOSTED_WALLET_01` for enhanced monitoring

***
## Section 3: Transaction Domain
### Unified Transaction Table
The `transaction` table handles both fiat and stablecoin events on a single schema, with `txn_rail` (`FIAT` | `STABLECOIN`) as the primary discriminator. This unified design enables cross-rail customer behavioural analysis, which Deloitte/Hawk identify as essential for effective risk management — linking fiat and crypto transactions to display overall customer behaviour[^14].

The table is **partitioned by `initiated_at` (monthly)** to support T+1 batch queries over large date ranges while maintaining real-time write performance. The `processing_mode` column (`REALTIME` | `BATCH`) records how each transaction was ingested.

Key fiat channels supported: `SWIFT`, `CHATS` (HK interbank), `FPS` (Faster Payment System), `JETCO`, `ACH`, `RTGS`
Key crypto channels: `BLOCKCHAIN` (on-chain transfers), `SVF`

The `hkd_equivalent_amount` column normalises all transaction values to HKD for consistent threshold-based rule evaluation — essential for the HKD 8,000 Travel Rule threshold and HKD 120,000 structuring threshold.
### stablecoin_txn_detail
Extended on-chain metadata for stablecoin transactions, linked 1:1 to `transaction`. Critical fields:
- `blockchain_tx_hash`: immutable on-chain reference for audit
- `ba_risk_score` (0–100): blockchain analytics risk score from Chainalysis, Elliptic, or TRM Labs
- `ba_risk_flags` TEXT[]: array of risk categories (`MIXER`, `DARKNET_MARKET`, `RANSOMWARE`, `SANCTIONS_DIRECT`) — triggers `SCN_BLOCKCHAIN_RISK_01`
- `is_unhosted_wallet_involved`: triggers EDD requirement per HKMA stablecoin AML/CFT guideline[^9]
### travel_rule_record
Implements the FATF Travel Rule as mandated by AMLO Schedule 2, Section 13A, extended to stablecoin transfers by the HKMA's proposed AML/CFT requirements. The function `fn_check_travel_rule()` automatically creates a Travel Rule record for every stablecoin transaction, setting `above_hkd8000_threshold` based on HKD equivalent amount. Supported transmission protocols: IVMS101, TRISA, OpenVASP, Sygna.[^7][^8]

***
## Section 4: Screening Domain
The `screening_result` table supports six screen types spanning both real-time (pre-execution) and T+1 batch (retrospective) modes:

| Screen Type | Mode | Description |
|---|---|---|
| `SANCTIONS` | REALTIME + BATCH | OFAC/UNSC/EU/HMT/HKMA lists[^4] |
| `PEP` | REALTIME + BATCH | Politically Exposed Persons[^13] |
| `ADVERSE_MEDIA` | BATCH | Negative news screening |
| `BLOCKCHAIN_RISK` | REALTIME | On-chain wallet analytics[^14] |
| `HIGH_RISK_COUNTRY` | REALTIME + BATCH | Jurisdictions with strategic AML deficiencies |
| `DUAL_USE_GOODS` | BATCH | Controls per HKMA Dec 2024 FAQ[^1] |

Fuzzy name matching is achieved via the `pg_trgm` extension with a `gin_trgm_ops` index on `matched_name`, supporting approximate name matching for sanctions screening with configurable `match_score` thresholds.

***
## Section 5: Detection Scenario Library
The model pre-seeds 11 detection scenarios covering all key FATF ML typologies and HK-specific regulatory requirements. Each scenario stores a `threshold_config` JSONB document for flexible parameterisation without schema changes — supporting the threshold tuning cycle required by the HKMA.[^5]

| Scenario Code | Category | Rail | Mode | Key Threshold |
|---|---|---|---|---|
| SCN_STRUCT_FIAT_01 | Structuring | FIAT | BATCH | HKD 120,000 CTR |
| SCN_STRUCT_SC_01 | Structuring | STABLECOIN | BATCH | HKD 8,000 Travel Rule |
| SCN_LAYER_RAPID_01 | Layering | BOTH | REALTIME | 24h roundtrip, 3+ hops |
| SCN_TRAVEL_RULE_01 | Travel Rule Breach | STABLECOIN | REALTIME | Zero threshold (every txn) |
| SCN_SANCTIONS_RT_01 | Sanctions Evasion | BOTH | REALTIME | 85% match score |
| SCN_BLOCKCHAIN_RISK_01 | Blockchain Risk | STABLECOIN | REALTIME | BA risk score > 70 |
| SCN_UNHOSTED_WALLET_01 | Unhosted Wallet | STABLECOIN | BATCH | Monthly > HKD 50,000 |
| SCN_VELOCITY_01 | Velocity | BOTH | REALTIME | 3x count, 5x amount vs baseline |
| SCN_HIGHVAL_01 | High Value | BOTH | REALTIME | Single txn > HKD 1,000,000 |
| SCN_DORMANT_01 | Dormant Account | BOTH | BATCH | 12+ months dormant |
| SCN_PEP_01 | PEP Monitoring | BOTH | BATCH | EDD; HKD 200,000 approval |

The HKMA's April 2024 thematic review found that AIs adopting a risk-based approach to threshold setting using statistical analysis — standard deviations, percentile ranks, clustering analysis, and above/below-the-line testing — produce better-calibrated scenarios. The `threshold_config` JSONB field stores these parameters and feeds the annual tuning report.[^5]

***
## Section 6: Alert Management
The `aml_alert` table tracks the full lifecycle from automated generation to disposition, supporting both real-time and batch alerts in a single table differentiated by `alert_mode`. Key design choices:

- `risk_score` (0–100): used for ML-model-based prioritisation — the HKMA cites a case study where a machine learning model assigns an additional risk score to each alert, enabling auto-discounting of low-risk cases with sample checking[^5]
- `sla_due_at`: tracks SLA compliance (typically 3 days for HKMA-regulated institutions)
- `triggered_rule_detail` JSONB: snapshots the exact rule parameters that fired, providing the audit trail required by the HKMA[^4]
- `disposition`: feeds the KPI calculation for false positive rate and STR conversion rate

The `v_open_alerts_dashboard` view surfaces all open alerts with SLA breach status calculated in real time, including hours remaining to SLA breach.

***
## Section 7: Case Management & STR Filing
### aml_case
The investigation case entity manages the full workflow from alert escalation through to STR filing or case closure. The `ml_typology` field categorises the suspected laundering method, including crypto-specific typologies: `CRYPTO_MIXING`, `DEFI_LAUNDERING`, `SANCTIONS_EVASION`.

The `case_activity_log` table provides an immutable chronological log of all case actions — ASSIGNED, NOTE_ADDED, ESCALATED, STR_DRAFTED, STR_SUBMITTED — satisfying the HKMA's audit trail requirements.[^4]
### str_report
Designed to the JFIU STREAMS 2 STR format. Key regulatory compliance features:
- `applicable_ordinances` TEXT[]: references the specific ordinances triggered — Cap.405 (DTROP), Cap.455 (OSCO), Cap.575 (UNATMO)[^10][^12]
- `no_tipping_off_confirmed` BOOLEAN: mandatory acknowledgment of tipping-off prohibition under AMLO[^11]
- `submission_channel`: STREAMS2_WEBFORM, STREAMS2_XML (requires HK Post e-cert), or STREAMS2_PDF — per JFIU mandate that all STRs be submitted electronically[^6]
- `is_supplemental` flag with `original_str_id` FK: supports supplemental STR filing for evolving investigations
- `reasons_for_suspicion`: structured to support the JFIU SAFE approach (Screen, Ask, Find, Evaluate)[^10]

***
## Section 8: Batch Processing (T+1)
The `batch_job` table tracks all scheduled overnight jobs. The T+1 processing cycle includes:

1. **T1_TM_RUN** — Main transaction monitoring: applies all BATCH-mode scenarios to prior business day's transactions
2. **T1_SCREENING** — Retrospective sanctions/PEP re-screening for newly listed entities
3. **T1_TRAVEL_RULE_CHECK** — Audits all stablecoin transactions for Travel Rule completeness
4. **T1_KPI_CALCULATION** — Populates `kpi_snapshot` for dashboard and regulatory reporting
5. **T1_GRAPH_REFRESH** — Materialises updated `graph_node` and `graph_edge` records from core transaction data
6. **T1_ALERT_AGING** — Flags SLA breaches on open alerts
7. **T1_WATCHLIST_SYNC** — Refreshes `watchlist_entry` from OFAC/UNSC/HMT feeds

The `business_date` (T–1) vs `batch_date` (T) separation ensures clear lineage between the data being processed and the processing execution date.

***
## Section 9: KPI & Management Reporting
The `kpi_snapshot` table materialises all KPIs required by the HKMA, computed by the T+1 KPI batch job and stored per period (DAILY, WEEKLY, MONTHLY, QUARTERLY) and per rail (FIAT, STABLECOIN, ALL).
### HKMA-Mandated KPIs
The following KPIs are explicitly required by the HKMA's April 2024 thematic review:[^5]

| KPI | Field | HKMA Reference |
|---|---|---|
| Active customer count | `total_active_customers` | Baseline for alert rate |
| Alerts generated | `total_alerts_generated` | Core volume metric |
| Productive cases | Derived: TP alerts | Effectiveness measure |
| STR conversion rate | `str_conversion_rate` | Quality metric — STRs / Productive Cases |
| False positive rate | `false_positive_rate` | Efficiency metric |
| Alert rate per 1,000 customers | `alert_rate_per_1000_customers` | Normalised volume |
| SLA breach count | `sla_breach_count` | Operational metric |

Stablecoin-specific KPIs added for the post-August 2025 regulatory environment:[^3]

| KPI | Field |
|---|---|
| Travel Rule compliance rate | `travel_rule_compliance_rate` |
| Unhosted wallet alerts | `unhosted_wallet_alerts` |
| High-risk blockchain alerts | `high_risk_blockchain_alerts` |

The `scenario_kpi` table enables per-scenario tuning analysis, storing `tuning_recommendation` values (`INCREASE_THRESHOLD`, `DECREASE_THRESHOLD`, `RETIRE_SCENARIO`) that feed the annual tuning report reviewed by the AML committee.[^5]

***
## Section 10: Network Graph Exploration Layer
The graph layer implements HKMA's recommendation for network analytics in AML/CFT, as detailed in "AML Regtech: Network Analytics" (May 2023) and highlighted in the 2024 thematic review. Several HKMA-regulated banks have adopted network analytics to facilitate investigation of unusual transactions from TM alerts, allowing them to identify hidden relationships demonstrating suspicious behaviour.[^5]
### Architecture
The graph layer uses a **materialised property graph** approach compatible with Apache AGE (the PostgreSQL graph extension) and pg_graph. Nodes and edges are populated from core tables via the `T1_GRAPH_REFRESH` batch job, with on-demand refreshes triggered during real-time alert investigation.[^15]
### graph_node
Supports 8 node types covering all entity types relevant to ML investigation:

| Node Type | Source | AML Use Case |
|---|---|---|
| `PARTY` | `aml_core.party` | Customer/UBO identification |
| `ACCOUNT` | `aml_core.account` | Fund flow mapping |
| `TRANSACTION` | `aml_core.transaction` | Pattern nodes in flow graphs |
| `BLOCKCHAIN_ADDRESS` | `stablecoin_txn_detail` | On-chain wallet clustering |
| `IP_ADDRESS` | Digital footprint | Shared infrastructure detection |
| `DEVICE` | Device fingerprint | Coordinated activity detection |
| `INSTITUTION` | Correspondent banks | Correspondent risk analysis |
| `LEGAL_ENTITY` | Corporate structure | UBO chain traversal |
### graph_edge
Directed edges with aggregated `txn_count` and `total_amount_hkd` support volume-weighted graph algorithms. Edge types cover both direct transaction flows (`SENT_TO`, `RECEIVED_FROM`, `BLOCKCHAIN_TX`) and structural relationships (`OWNS_ACCOUNT`, `CONTROLS`, `SAME_IP`, `SAME_DEVICE`).

The graph model can catch layering in real time by tracking behavioural anomalies across hops, and Cypher queries can identify accounts transacting with more than 5 different accounts within short time windows — patterns that prove graph traversal outperforms SQL joins for network-based fraud.[^16]
### Community Detection
The `graph_community` table stores results from community detection algorithms (Louvain, Label Propagation, Weakly Connected Components). Communities are scored with `community_risk_score` and flagged as `is_suspicious`. The `v_suspicious_communities` view surfaces unreviewed suspicious communities ranked by risk score for analyst triage.
### Supported Graph Analytics
| Algorithm | Use Case |
|---|---|
| PageRank | Identify high-centrality nodes (hubs) in money flow |
| Betweenness Centrality | Find intermediary/facilitation accounts |
| Louvain Community | Detect smurfing rings and layering networks |
| Cycle Detection | Identify round-tripping and circular fund flows |
| Shortest Path | Trace fund flow between flagged entities |
| Weakly Connected Components | Map full relationship clusters |
| Triangle Count | Detect concentrated mutual fund flows |
### Apache AGE Integration
Tables are designed for compatibility with the Apache AGE extension. To query the graph in Cypher:

```sql
-- Load AGE extension
LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- Example: Find all accounts within 3 hops of a flagged party
SELECT * FROM cypher('aml_graph', $$
    MATCH path = (p:graph_node {is_flagged: true})-[:graph_edge*1..3]-(n:graph_node)
    WHERE n.node_type IN ['ACCOUNT', 'BLOCKCHAIN_ADDRESS']
    RETURN n.node_label, n.risk_score, length(path) AS hops
    ORDER BY n.risk_score DESC
$$) AS (node_label agtype, risk_score agtype, hops agtype);
```

***
## Section 11: Dual-Mode Processing Design
### Real-Time Path (sub-second)
Real-time detection is triggered on transaction ingestion, typically via a stream processing engine (Apache Kafka + Flink). The following scenarios execute in REALTIME mode:[^17]
- Sanctions screening (pre-execution block capability)
- Travel Rule completeness check (`fn_check_travel_rule()`)
- Rapid layering detection (SCN_LAYER_RAPID_01)
- High-value transaction alert (SCN_HIGHVAL_01)
- Blockchain risk score check (SCN_BLOCKCHAIN_RISK_01)

Transactions flagged by real-time rules set `txn_status = 'HELD'` or `'BLOCKED'` pending analyst review. The `is_aml_processed = FALSE` index enables efficient real-time queue querying.
### T+1 Batch Path
Overnight batch processing handles pattern-based scenarios requiring multi-day aggregation windows (structuring over 30 days, velocity vs 90-day baseline). The batch pipeline:

1. Queries the transaction partition for `business_date` where `is_aml_processed = FALSE`
2. Applies all BATCH-mode scenarios using aggregation windows defined in `threshold_config`
3. Generates `aml_alert` records with `alert_mode = 'BATCH'` and `batch_job_id`
4. Runs `T1_TRAVEL_RULE_CHECK` for stablecoin compliance audit
5. Executes `T1_GRAPH_REFRESH` to materialise updated graph edges
6. Computes `kpi_snapshot` for daily KPI dashboard
7. Updates `is_aml_processed = TRUE` on processed transactions

This architecture matches industry best practice: real-time for sanctions/critical thresholds and batch for aggregated structuring/layering patterns.[^18]

***
## Section 12: Security & Compliance Controls
### Row-Level Security
Row-Level Security (RLS) is enabled on `str_report` and `aml_alert`. The MLRO, Compliance Officer, and Admin roles can access all STRs; Analysts only access alerts and cases assigned to them. This enforces need-to-know principles and supports the no tipping-off requirement — analysts cannot see STRs for customers they continue to service.
### Immutable Audit Log
The `audit_log` table is partitioned by year and records INSERT, UPDATE, DELETE, VIEW, and EXPORT actions on all sensitive tables. The `fn_audit_trigger()` function captures old and new JSON values for every change, providing the comprehensive audit trail required by the HKMA. The table is append-only by design — no DELETE privilege should be granted.[^4]
### Critical Data Elements
The HKMA's 2024 thematic review identifies Critical Data Elements (CDEs) as fundamental to effective TM systems. The model ensures CDE completeness through:[^5]
- NOT NULL constraints on `party.full_name`, `transaction.txn_amount`, `transaction.initiated_at`
- `hkd_equivalent_amount` mandatory for threshold comparisons
- `blockchain_tx_hash` UNIQUE on `stablecoin_txn_detail`
- Data lineage tracked via `source_system_id` and `batch_job_id` on transactions

***
## Deployment Notes
### Extensions Required
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pg_trgm";     -- Fuzzy name matching
CREATE EXTENSION IF NOT EXISTS "btree_gin";   -- Composite GIN indexes
-- CREATE EXTENSION IF NOT EXISTS age;        -- Apache AGE (for Cypher queries)
```
### Partition Management
The `transaction` and `audit_log` tables use range partitioning by date. Monthly partitions for `transaction` and annual partitions for `audit_log` should be created programmatically (e.g., via pg_partman or a scheduled job) before the partition date arrives.
### Recommended Additional Tooling
- **Stream processing**: Apache Kafka + Flink for real-time transaction ingestion[^17]
- **Blockchain analytics**: Chainalysis, Elliptic, or TRM Labs API for `ba_risk_score` and `ba_risk_flags`[^14]
- **Graph visualisation**: Neo4j Bloom or custom D3.js dashboard consuming `aml_graph` tables[^19]
- **Watchlist feeds**: OFAC SDN, UNSC Consolidated List, HMT Financial Sanctions, EU Consolidated List (daily refresh)

***
## Files Delivered
The following artifacts are included:

1. **`aml_data_model.mmd`** — Mermaid ER diagram showing all 24 tables, their fields with types, and all relationships across the 6 schemas
2. **`aml_ddl_postgresql.sql`** — Full PostgreSQL DDL (1,256 lines) including:
   - All table definitions with constraints and comments
   - Performance indexes
   - Pre-seeded detection scenarios
   - Operational dashboard views
   - Audit trigger functions
   - Travel Rule check function
   - Row-Level Security policies
   - Schema and extension setup

---

## References

1. [Frequently Asked Questions in relation to Anti-Money Laundering ...](https://www.timothyloh.com/insights/latest-news/frequently-asked-questions-in-relation-to-anti-money-laundering-and-counter-financing-of-terrorism-developed-by-the-hong-kong-association-of-banks-20241230) - On 30 Dec 2024, the HKMA and HKAB published updated AML/CFT FAQs clarifying operational requirements...

2. [Hong Kong's stablecoin regulations unveiled: Bill passed…](https://www.reedsmith.com/articles/hong-kongs-stablecoin-regulations-unveiled-bill-passed-licensee-guidelines/)

3. [Hong Kong Implements New Regulatory Framework for Stablecoins](https://www.sidley.com/en/insights/newsupdates/2025/08/hong-kong-implements-new-regulatory-framework-for-stablecoins)

4. [GUIDANCE PAPER - Transaction Monitoring, Screening ...](https://www.hkma.gov.hk/media/eng/doc/key-information/guidelines-and-circular/2023/20230209e2a2.pdf) - The AML/CFT Guideline sets out relevant statutory1 and regulatory requirements. While this Guidance ...

5. [[PDF] Insights for Design, Implementation and Optimisation of Transaction ...](https://www.hkma.gov.hk/media/eng/doc/key-information/guidelines-and-circular/2024/20240417e2a1.pdf)

6. [How to identify a Suspicion? | Joint Financial Intelligence Unit](https://www.jfiu.gov.hk/en/str.html) - Joint Financial Intelligence Unit

7. [HKMA Stablecoin Licensing Decisions Are Coming](https://notabene.id/post/hong-kong-stablecoin-travel-rule-compliance-standard) - Hong Kong just released groundbreaking guidelines requiring Travel Rule compliance for ALL stablecoi...

8. [Consultation Paper on the Proposed AML/CFT ...](https://www.hkma.gov.hk/media/eng/regulatory-resources/consultations/20250526_Consultation_Paper_on_the_Proposed_AMLCFT_Req_for_Regulated_Stablecoin_Activities.pdf)

9. [What Hong Kong stablecoin issuers need to know about the latest ...](https://www.jsm.com/publications/2025/what-hong-kong-stablecoin-issuers-need-to-know-about-the-latest-aml-cft-compliance/) - What Hong Kong stablecoin issuers need to know about the latest AML/CFT compliance? · Adopt a risk-b...

10. [Reporting Suspicious Transactions - TCSP Registry](https://www.tcsp.cr.gov.hk/tcspls/portal/aml-str) - Use the STR proforma or the e-reporting system named Suspicious Transaction Report and Management Sy...

11. [Suspicious Transaction Report](https://www.ia.org.hk/en/supervision/antimoney_laundering/files/20241029_AML_Seminar_Eng_JFIU.pdf) - • No threshold or cross boundary reporting ... RECOMMENDED STRUCTURE OF STR. Page 20. 20. ©Hong Kong...

12. [Joint Financial Intelligence Unit & Suspicious Transaction ...](https://www.fstb.gov.hk/fsb/aml/en/edu-publicity/seminar2018/Suspicious%20Transaction%20Reporting.pdf) - Any person, who knows / suspects that any property represents proceeds of crime / terrorist property...

13. [Guideline on Anti-Money Laundering and Counter](https://www.hkma.gov.hk/media/eng/doc/key-information/guidelines-and-circular/guideline/Guideline_on_AML-CFT_(for_SVFs)_eng_May%202023.pdf) - The HKMA is empowered to exercise various provisions under the PSSVFO in case of non-compliance with...

14. [Conquering Crypto Crime Combining Blockchain Analytics ...](https://hawk.ai/sites/default/files/2025-01/AML-for-Crypto-Deloitte-Hawk-Whitepaper.pdf) - These solutions are designed to process fiat transactions and analyze them based on complex scenario...

15. [Working with Graph Data in Neo4j, PostgreSQL, and Oracle - Baremon](https://www.baremon.eu/graph-databases-in-practice/) - Explore how graph databases model relationships, key use cases, and how to get started with graph qu...

16. [AML Detection with Graph Data: Smurfing, Layering and Entity ...](https://www.linkedin.com/posts/kristian-aryanto-wibowo_aml-graphdata-neo4j-activity-7419399839739994112-22fx) - ... graph model, you can catch layering in real time — if you track behavioral anomalies across hops...

17. [AML Functional Specification - BizFirstFi](https://www.bizfirstfi.com/public-documentation/aml/functional-spec.html)

18. [AML Transaction Monitoring in Power BI: Detecting Suspicious ...](https://www.linkedin.com/posts/amit-kumar-rajan-ba85a010b_aml-powerbi-transactionmonitoring-activity-7427350783807062016-5MpI) - Building an AML Transaction Monitoring Dashboard in Power BI Money laundering rarely looks dramatic....

19. [[PDF] Graph Technology for Financial Services - Neo4j](https://go.neo4j.com/rs/710-RRC-335/images/Neo4j-Graphs-in-Financial-Services-white-paper-EN-A4.pdf) - The graph data model below represents how the data actually looks to the graph database, and illustr...

