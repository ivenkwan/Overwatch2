# Graph Report - .  (2026-07-09)

## Corpus Check
- 175 files · ~498,615 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 586 nodes · 675 edges · 74 communities (37 shown, 37 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 96 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- AML Data Model & Build Spec
- Platform Architecture & Concepts
- Alerts & Cases API
- AML Spec: Detection & Controls
- Frontend Dependencies
- Frontend Page Components
- Platform Services & Compose
- Build Spec: Microservices
- STR Reporting API
- ETL Ledger Ingest Pipeline
- TypeScript Config
- Auth & JWT Module
- Admin & Keycloak User Mgmt
- Agentic Harness Lessons
- Frontend Layout & Error Boundary
- STR API Tests
- PII Masking Service
- Graph Loader (ETL->AGE)
- User Models
- Batch Normalization
- User & Role Mgmt Pages
- Dashboard UI Screenshots
- Flowable BPMN Client
- Graph Query Service
- Dependency Security Audit
- AML Detection Typologies
- Demo Data Loader
- Next.js Root Layout
- Governance MIS & KPI Cards
- Hermes & OpenCode Integration
- Daily KPI Mart
- Env Reload & Demo Reset
- Cypher Rule Engine
- AML Services PowerShell Scripts
- Database-Native Rule Engine
- Graphify Skill Docs
- Frontend Agent Config Docs
- ESLint Config
- Next.js Config
- PostCSS Config
- Audit Schema & Service
- Normalisation & Rail Abstraction
- Debug History & Notes
- Modular Backend Architecture
- Docs Lint CI
- File Icon Asset
- Globe Icon Asset
- Next.js Logo Asset
- Vercel Logo Asset
- Window Icon Asset
- Frontend README
- Lesson: Agent Config Convention
- Lesson: Compliance-First Design
- Lesson: Dead Letter Queue Pattern
- Lesson: Explicit Orchestration Layer
- Lesson: Idempotency via Hashing
- Lesson: Incremental Honesty
- Lesson: Spec-First Design
- Agent Foundational Principle
- Risk Scoring Service
- Squad D: Platform & Infra
- Continuous Improvement & HITL
- Alert Triage Swimlanes
- Unified Risk Scoring Engine
- Agentic AI Security Controls
- ETL Pipeline Module
- Governance/MIS Module

## God Nodes (most connected - your core abstractions)
1. `compilerOptions` - 16 edges
2. `Overwatch AML Platform Complete Codebase Analysis (Repo Scan and Doc)` - 13 edges
3. `tme-engine` - 11 edges
4. `Project Overwatch Build Specification and Engineering Plan` - 10 edges
5. `get_user_and_tenant()` - 8 edges
6. `Project Overwatch Next Generation of Transaction Monitoring` - 8 edges
7. `api` - 7 edges
8. `Dagster etl_pipeline` - 7 edges
9. `ingestion-service` - 7 edges
10. `case-management-service` - 7 edges

## Surprising Connections (you probably didn't know these)
- `Peeling Chain Typology (5-20% peels)` --semantically_similar_to--> `Circular Flow Detection (2-5 hop cycles)`  [INFERRED] [semantically similar]
  Implementation_Plan/20260402.md → AML_spec.md
- `High-Velocity Layering Typology (fan-out/fan-in)` --semantically_similar_to--> `Rapid Movement Detection (money mules)`  [INFERRED] [semantically similar]
  Implementation_Plan/20260402.md → AML_spec.md
- `Evidentiary Audit Trail (every read/expansion logged)` --semantically_similar_to--> `Audit Logging Policy (12-month retention, SIEM export)`  [INFERRED] [semantically similar]
  AML_spec.md → SECURITY.md
- `AML Admin Portal` --semantically_similar_to--> `AML Admin Portal — Functional & Non-Functional Requirements Specification`  [INFERRED] [semantically similar]
  docs/new_v5_spec/Project_Overwatch_Build_Specification_and_Engineering_Plan.pdf → tmp/AML Admin Portal — Functional & Non-Functional Requirements Specification.pdf
- `Screening Module (sanctions/PEP/wallet)` --semantically_similar_to--> `Sanctions Screening Service`  [INFERRED] [semantically similar]
  tmp/Project Overwatch Business Requirements.pdf → docs/new_v5_spec/Project_Overwatch_Build_Specification_and_Engineering_Plan.pdf

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **AML Typology Detection Rules (Cypher Rule Engine)** — aml_spec_circular_flow_detection, aml_spec_smurfing_detection, aml_spec_rapid_movement_detection, implementation_plan_20260402_peeling_chain, implementation_plan_20260402_high_velocity_layering, aml_spec_cypher_rule_engine [INFERRED 0.95]
- **HKMA Dashboard Module Suite (6 modules)** — implementation_plan_20260406_rebuilt_dashboard_to_meet_hk_req_walkthrough_hkma_modules, readme_hkma_compliance, readme_case_management, readme_jfiu_str_reporting, readme_kpi_framework, readme_stablecoin_monitoring [INFERRED 0.85]
- **Backend Boot Failure Debug Chain (sequential import errors resolved)** — implementation_plan_debug_backend_logs_db_connection_failure, implementation_plan_debug_backend_logs2_get_db_import_error, implementation_plan_debug_backend_logs3_graph_service_import_error, implementation_plan_debug_backend_logs4_missing_email_validator, implementation_plan_debug_backend_logs5_successful_startup [EXTRACTED 0.95]
- **AML Platform microservice architecture (all services depend on age_db)** — aml_platform_docker_compose_age_db, aml_platform_docker_compose_aml_backend, aml_platform_docker_compose_dagster_etl, aml_platform_docker_compose_keycloak, aml_platform_docker_compose_flowable, aml_platform_docker_compose_aml_frontend [EXTRACTED 1.00]
- **Dagster production ETL pipeline (raw -> cleaned -> relational -> graph)** — docs_etl_dagster_production_raw_ledger_data, docs_etl_dagster_production_cleaned_ledger_data, docs_etl_dagster_production_load_relational_tables, docs_etl_dagster_production_update_age_graph [EXTRACTED 1.00]
- **Hermes-OpenCode two-agent integration loop** — docs_hermes_opencode_manual_hermes_agent, docs_hermes_opencode_manual_opencode_cli, docs_hermes_opencode_manual_omo, docs_hermes_opencode_manual_sisyphus [EXTRACTED 1.00]
- **Real-Time AML Detection Pipeline** — docs_new_v5_spec_project_overwatch_agent_squad_specs_ingestion_service, docs_new_v5_spec_project_overwatch_agent_squad_specs_tme_engine, docs_new_v5_spec_project_overwatch_agent_squad_specs_sanctions_service, docs_new_v5_spec_project_overwatch_agent_squad_specs_wallet_analytics_adapter, docs_new_v5_spec_project_overwatch_agent_squad_specs_case_management_service [EXTRACTED 1.00]
- **Tamper-Proof Forensic Audit Chain** — docs_new_v5_spec_doc_full_forensicdb, docs_new_v5_spec_project_overwatch_agent_squad_specs_forensic_audit_service, docs_new_v5_spec_doc_full_forensic_verifier, docs_new_v5_spec_doc_full_aml_forensic_schema [EXTRACTED 1.00]
- **T+1 Batch Scanning 8-Stage Pipeline** — docs_new_v5_spec_project_overwatch_agent_squad_specs_batch_scanning_service, docs_new_v5_spec_aml_converged_data_model_aml_reporting_schema, docs_new_v5_spec_aml_converged_data_model_aml_behaviour_schema, docs_new_v5_spec_aml_converged_data_model_aml_graph_schema [INFERRED 0.85]
- **Maker-Checker Case Workflow Design (Flowable integration)** — docs_working_doc_20260409_multi_agent_brainstorming_identity_delegation_decision, docs_working_doc_20260409_multi_agent_brainstorming_dual_state_data_storage, docs_working_doc_20260409_multi_agent_brainstorming_bpmn_auto_deploy, docs_working_doc_20260602_code_explain_flowable_maker_checker [EXTRACTED 0.95]
- **RBAC Multi-Tenant Authorization Stack (Keycloak + PostgreSQL RLS + Case ACL)** — docs_working_doc_aml_rbac_starter_00__rbac_with_postgresql_and_keycloak_postgresql_keycloak_choice, docs_working_doc_aml_rbac_starter_01__map_this_into_a_concrete_rbac_design_for_your_aml_keycloak_realm_client_roles, docs_working_doc_aml_rbac_starter_01__map_this_into_a_concrete_rbac_design_for_your_aml_rls_multi_tenant_isolation, docs_working_doc_aml_rbac_starter_keycloak_composite_role_plan_composite_roles [INFERRED 0.85]
- **Overwatch Full-Stack Architecture (AGE Graph + ETL + RBAC + PII)** — docs_working_doc_20260407_repo_scan_and_doc_apache_age_graph, docs_working_doc_20260407_repo_scan_and_doc_dagster_etl_pipeline, docs_working_doc_20260407_repo_scan_and_doc_rbac_role_hierarchy, docs_working_doc_20260407_repo_scan_and_doc_pii_masking_service, docs_working_doc_20260407_repo_scan_and_doc_jwt_authentication [INFERRED 0.85]
- **T+1 Batch Alert Pipeline (Ingestion -> Canonical -> Batch Scan -> CMS)** — docs_new_v5_spec_project_overwatch_build_specification_and_engineering_plan_ingestion_service, docs_new_v5_spec_project_overwatch_build_specification_and_engineering_plan_canonical_transaction_schema, docs_new_v5_spec_project_overwatch_build_specification_and_engineering_plan_batch_scanning_service, docs_new_v5_spec_project_overwatch_build_specification_and_engineering_plan_case_management_service [INFERRED 0.95]
- **ForensicDB Manual-Interaction Event Publication** — docs_new_v5_spec_project_overwatch_build_specification_and_engineering_plan_case_management_service, docs_new_v5_spec_project_overwatch_build_specification_and_engineering_plan_aml_admin_portal, docs_new_v5_spec_project_overwatch_build_specification_and_engineering_plan_regulatory_reporting_service, docs_new_v5_spec_project_overwatch_build_specification_and_engineering_plan_forensicdb [EXTRACTED 0.95]
- **AML Admin Portal Four-Module Architecture** — tmp_aml_admin_portal___functional___non_functional_requirements_specification_kpi_dashboard_module, tmp_aml_admin_portal___functional___non_functional_requirements_specification_case_management_module, tmp_aml_admin_portal___functional___non_functional_requirements_specification_network_visualization_module, tmp_aml_admin_portal___functional___non_functional_requirements_specification_etl_pipeline_module [EXTRACTED 0.95]
- **Multi-panel layout (sidebar + content + toolbar)** — docs_working_doc_screenshot_2026_04_04_094642_ui_layout, docs_working_doc_screenshot_2026_04_04_094642_navigation_sidebar, docs_working_doc_screenshot_2026_04_04_094642_content_area [INFERRED 0.85]
- **Default Next.js template public assets** — aml_platform_frontend_public_file_fileicon, aml_platform_frontend_public_globe_globeicon, aml_platform_frontend_public_next_nextjslogo, aml_platform_frontend_public_vercel_vercellogo, aml_platform_frontend_public_window_windowicon [EXTRACTED 1.00]

## Communities (74 total, 37 thin omitted)

### Community 0 - "AML Data Model & Build Spec"
Cohesion: 0.06
Nodes (50): AML Data Model Converged Specification, aml_behaviour Schema, aml_case_mgmt Schema, aml_core Schema, aml_detection Schema, aml_graph Schema (Apache AGE), aml_reporting Schema, Project Overwatch Build Specification and Engineering Plan (+42 more)

### Community 1 - "Platform Architecture & Concepts"
Cohesion: 0.06
Nodes (43): Overwatch AML Platform Complete Codebase Analysis (v2), Overwatch AML Platform Complete Codebase Analysis (Repo Scan and Doc), AML Typology Detection (Circular Flow, Smurfing, Rapid Movement), Apache AGE Graph Extension (PostgreSQL openCypher), Dagster ETL Pipeline (raw_ledger_data -> cleaned -> relational -> AGE graph), JWT Authentication (HS256 + bcrypt), Maker-Checker Alert Lifecycle Workflow, OFAC Screening Procedure (sp_screen_ofac) (+35 more)

### Community 2 - "Alerts & Cases API"
Cohesion: 0.07
Nodes (31): approve_close(), assign_alert(), get_alert_detail(), get_alerts(), get_monitoring_feed(), propose_close(), Connection, reject_close() (+23 more)

### Community 3 - "AML Spec: Detection & Controls"
Cohesion: 0.06
Nodes (34): Apache AGE openCypher Extension, Evidentiary Audit Trail (every read/expansion logged), Dead Letter Queue (failed ETL rows), OFAC/FATF Regulatory Gate, PII Masking for unauthorized roles, Query Capping (30s timeout on Cypher traversals), RBAC (Viewer, Reviewer, Senior Investigator, Admin), SuperNode Handling (exclude hubs from cycle detection) (+26 more)

### Community 4 - "Frontend Dependencies"
Cohesion: 0.06
Nodes (31): dependencies, axios, clsx, cytoscape, framer-motion, lucide-react, next, react (+23 more)

### Community 5 - "Frontend Page Components"
Cohesion: 0.08
Nodes (8): ContextMenu, GraphExplorerProps, api, Alert, Case, Channel, Customer, Payment

### Community 6 - "Platform Services & Compose"
Cohesion: 0.09
Nodes (27): age_db (Apache AGE / PostgreSQL), aml-backend (FastAPI), aml-frontend (Next.js), dagster_etl service, flowable (BPMN Workflow Engine), keycloak (Identity Management), etl/error_trace.txt, Overwatch AML Platform API Reference (+19 more)

### Community 7 - "Build Spec: Microservices"
Cohesion: 0.10
Nodes (27): Lesson 5: Dual-Layer State Management (Workflow Engine + DB), Lesson 9: Hybrid Data Topology (PostgreSQL + Apache AGE), Apache Airflow (batch scheduling), AML Admin Portal, Apache AGE (PostgreSQL graph extension), Audit Trail Service, T+1 Batch Transaction Scanning Service, Canonical Transaction Schema (+19 more)

### Community 8 - "STR Reporting API"
Cohesion: 0.15
Nodes (20): create_str_draft(), get_str_detail(), get_user_and_tenant(), list_strs(), Connection, Retrieve a specific STR by its ID., Update fields of a draft STR., Helper to resolve DB user_id and tenant_id from username, with fallbacks. (+12 more)

### Community 9 - "ETL Ledger Ingest Pipeline"
Cohesion: 0.13
Nodes (19): Config, DataFrame, Projects relational PostgreSQL tables into Apache AGE Graph., update_age_graph(), cleaned_ledger_data(), IngestConfig, load_relational_tables(), Reads the raw CSV file and performs basic column renaming and typing. (+11 more)

### Community 10 - "TypeScript Config"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 11 - "Auth & JWT Module"
Cohesion: 0.11
Nodes (14): login_for_access_token(), Authenticate user and return JWT token.     Uses PostgreSQL DB to read user cre, create_access_token(), get_current_user(), get_current_user_with_scope(), log_audit_event(), log_unmasking_event(), Decode JWT and return user info. (+6 more)

### Community 12 - "Admin & Keycloak User Mgmt"
Cohesion: 0.22
Nodes (13): assign_role(), create_user(), get_keycloak_admin(), get_roles(), get_tenant_users(), BaseModel, Connection, Get all users mapped to the current tenant. (+5 more)

### Community 13 - "Agentic Harness Lessons"
Cohesion: 0.17
Nodes (12): Lesson 8: Codebase Cartography (knowledge graph navigation), graphify (codebase knowledge graph tool), 10 Lessons Learned from the Overwatch Agentic Harness Implementation, AutoGen, CrewAI, LangGraph, Developing Agentic Systems: 10 Lessons from the Overwatch Harness & the Open-Source Ecosystem, Blockchain Indexer (EVM + Solana) (+4 more)

### Community 14 - "Frontend Layout & Error Boundary"
Cohesion: 0.22
Nodes (4): ErrorBoundary, Props, State, DashboardLayout()

### Community 16 - "PII Masking Service"
Cohesion: 0.31
Nodes (7): mask_pii(), mask_value(), Apply masking logic to a specific field value., Recursively mask PII in dictionaries or lists based on user role.     Only SENI, test_junior_masking(), test_senior_unmasking(), Any

### Community 17 - "Graph Loader (ETL->AGE)"
Cohesion: 0.33
Nodes (8): get_db_connection(), get_super_nodes(), promote_crypto_to_graph(), promote_fiat_to_graph(), Fetches the super-nodes from the relational database., Translates tabular SCREENED fiat elements into openCypher MERGE commands., Translates Tabular SCREENED crypto elements into openCypher MERGE commands., run_graph_promotion()

### Community 18 - "User Models"
Cohesion: 0.39
Nodes (7): Config, BaseModel, Token, TokenData, UserBase, UserCreate, UserOut

### Community 19 - "Batch Normalization"
Cohesion: 0.43
Nodes (6): get_db_connection(), normalize_crypto_txn(), normalize_fiat_swift(), Simulates parsing messy TradFi SWIFT payloads into the relational     staging_f, Simulates parsing Web3/Crypto block explorer API or Node RPC data (e.g. UTXO/Acc, run_t1_batch_job()

### Community 21 - "Dashboard UI Screenshots"
Cohesion: 0.43
Nodes (5): Main content/workspace area, Navigation sidebar pattern, UI layout (multi-panel application view), Toolbar / action bar pattern, UI view (application screen)

### Community 22 - "Flowable BPMN Client"
Cohesion: 0.60
Nodes (5): complete_task(), deploy_process(), get_active_task(), get_auth(), start_case_process()

### Community 23 - "Graph Query Service"
Cohesion: 0.47
Nodes (5): get_full_network(), get_neighborhood(), parse_agtype(), Connection, Fetches a subgraph centered around entity_id up to 'depth' hops away.

### Community 24 - "Dependency Security Audit"
Cohesion: 0.47
Nodes (5): backend/requirements.txt, requirements.txt (root platform), Dependency Security Audit & Supply Chain Report, Dependency Security Audit (FAIL 47.7/100), Unpinned Python Dependencies Risk

### Community 25 - "AML Detection Typologies"
Cohesion: 0.33
Nodes (6): Circular Flow Detection (2-5 hop cycles), Rapid Movement Detection (money mules), Smurfing Detection (sub-$10k layering), High-Velocity Layering Typology (fan-out/fan-in), Peeling Chain Typology (5-20% peels), Stablecoin Monitoring (fiat + on-chain unified model)

### Community 26 - "Demo Data Loader"
Cohesion: 0.70
Nodes (4): ensure_schema_exists(), load_sql_bulk(), main(), run_command()

### Community 27 - "Next.js Root Layout"
Cohesion: 0.40
Nodes (3): geistMono, geistSans, metadata

### Community 29 - "Hermes & OpenCode Integration"
Cohesion: 0.60
Nodes (5): Hermes Agent + OpenCode CLI Integration Manual, Hermes Agent (Nous Research), oh-my-opencode (OMO), OpenCode CLI, Sisyphus agent

### Community 30 - "Daily KPI Mart"
Cohesion: 0.67
Nodes (3): compute_daily_kpi(), setup_schema(), date

### Community 31 - "Env Reload & Demo Reset"
Cohesion: 0.83
Nodes (3): drop_and_recreate_data(), main(), run_command()

### Community 35 - "Database-Native Rule Engine"
Cohesion: 0.67
Nodes (3): Cypher Rule Engine (openCypher templates), Database-Native Cypher Rule Engine (Option A, YAGNI), Rule Engine Module (rule_engine.py, 3 typologies)

## Knowledge Gaps
- **150 isolated node(s):** `DatabaseState`, `Config`, `Config`, `eslintConfig`, `nextConfig` (+145 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **37 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `NetworkPage()` connect `Frontend Dependencies` to `Frontend Page Components`?**
  _High betweenness centrality (0.006) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `Overwatch AML Platform Complete Codebase Analysis (Repo Scan and Doc)` (e.g. with `Overwatch AML Platform Complete Codebase Analysis (v2)` and `Overwatch Code Explanation and Architecture Walkthrough`) actually correct?**
  _`Overwatch AML Platform Complete Codebase Analysis (Repo Scan and Doc)` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `tme-engine` (e.g. with `aml_detection Schema` and `End-to-End AML Detection Lifecycle`) actually correct?**
  _`tme-engine` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Provisions a user in Keycloak and maps them to the local `app_users` table`, `Get all users mapped to the current tenant.`, `Fetch predefined roles that an admin can assign to a user.` to the rest of the system?**
  _204 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `AML Data Model & Build Spec` be split into smaller, more focused modules?**
  _Cohesion score 0.05959183673469388 - nodes in this community are weakly interconnected._
- **Should `Platform Architecture & Concepts` be split into smaller, more focused modules?**
  _Cohesion score 0.05758582502768549 - nodes in this community are weakly interconnected._
- **Should `Alerts & Cases API` be split into smaller, more focused modules?**
  _Cohesion score 0.06666666666666667 - nodes in this community are weakly interconnected._