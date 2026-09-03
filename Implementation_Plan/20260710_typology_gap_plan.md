# Typology Detection — Gap Analysis & Materialized Build Plan

**Date:** 2026-07-10
**Trace origin:** graphify communities `C32 Cypher Rule Engine` ↔ `C3 AML Spec: Detection & Controls` ↔ `C25 AML Detection Typologies` ↔ `C1 Implementation Plans / Repo Scan`
**Question answered:** How do the detection rules, spec typologies, and planned-but-unimplemented typologies actually connect — and what gaps remain?

---

## 1. The path through the graph — and where the graph's story breaks

The graph (community hubs + "surprising connections") reported the rule engine implements **3 typologies** (Circular Flow, Smurfing, Rapid Movement) and that **Peeling Chain** and **High-Velocity Layering** were *inferred/planned* (semantically-similar edges back to the base typologies).

**Code reality** ([aml_platform/etl/typologies.py](../aml_platform/etl/typologies.py)):

| Rule in code | Status |
|---|---|
| `CIRCULAR_TRANSACTION` (Circular Flow) | Implemented ✓ |
| `SMURFING_STRUCTURING` (Smurfing) | Implemented ✓ |
| `PEELING_CHAIN` | Implemented ✓ — marked "(New)" |
| `HIGH_VELOCITY_LAYERING` | Implemented ✓ — marked "(New)" |
| **Rapid Movement / Mule Funneling** | **DROPPED ✗** — mandated by [AML_spec.md](../AML_spec.md) L31 and built per [20260402.md](./20260402.md) §4, but absent from current code |

**Conclusion:** The graph's "planned-but-unimplemented" inference was *inverted*. The two typologies it flagged as merely planned (Peeling Chain, High-Velocity Layering) **are** in the code; the real gaps are (a) a **regression** — Rapid Movement was removed — and (b) a large **spec-vs-code shortfall** against the v5 requirements. The graph missed this because extraction was split across chunks and the code community (C32) never got cross-linked to the spec community (C3/C25).

**Bridge nodes on the path:** `tme-engine` (v5 Squad A, the Transaction Monitoring Engine that *should* own these rules) → `Cypher Rule Engine` / `rule_engine.py` → `typologies.py` → `AML_spec.md` → `Implementation_Plan/20260402.md`.

---

## 2. Gap analysis

### 2a. v5-mandated detection scenarios vs. implemented

v5 spec §15.1 ([Project-Overwatch-Full-Requirements-Specification.md](../docs/new_v5_spec/Project-Overwatch-Full-Requirements-Specification.md) L1676–1691) defines a **14-scenario pre-seeded library**. Coverage today:

| v5 Scenario | Category | Mode | Implemented? | Notes |
|---|---|---|---|---|
| `SCN_STRUCT_FIAT_01` | Structuring | BATCH | **Partial** | Smurfing rule exists but uses flat USD 10k, not HKD 120k CTR + 30-day window |
| `SCN_STRUCT_SC_01` | Structuring (stablecoin) | BATCH | **No** | No HKD 8k Travel-Rule threshold |
| `SCN_LAYER_RAPID_01` | Layering | REALTIME | **Partial** | Peeling/High-Velocity touch layering but not "24h roundtrip, 3+ hops" |
| `SCN_TRAVEL_RULE_01` | Travel Rule Breach | REALTIME | **No** | Not in rule engine |
| `SCN_SANCTIONS_RT_01` | Sanctions Evasion | REALTIME | **Partial** | OFAC relational exact-match only; no 85% fuzzy, not in AGE |
| `SCN_BLOCKCHAIN_RISK_01` | Blockchain Risk | REALTIME | **No** | Needs `ba_risk_score` |
| `SCN_UNHOSTED_WALLET_01` | Unhosted Wallet | BATCH | **No** | |
| `SCN_VELOCITY_01` | Velocity | REALTIME | **No** | Needs 90-day behavioural baseline |
| `SCN_HIGHVAL_01` | High Value | REALTIME | **No** | |
| `SCN_DORMANT_01` | Dormant Account | BATCH | **No** | |
| `SCN_PEP_01` | PEP Monitoring | BATCH | **No** | |
| `SCN_MIXER_EXPOSURE_01` | Mixer/Darknet | BATCH | **No** | Needs wallet baseline |
| `SCN_PROFILE_MISMATCH_01` | Profile Mismatch | BATCH | **No** | |
| `SCN_CROSS_RAIL_LAYER_01` | Cross-Rail Layering | BATCH | **No** | **Headline gap** — the v5 differentiator |

**Coverage: ~2 fully, ~3 partial, ~9 absent.** The platform's stated reason for existing — *cross-rail* laundering detection — has zero rule coverage.

### 2b. Regression
- **Rapid Movement / Mule Funneling** (single entity forwarding >90% of incoming funds within a window) — in v1 spec and the 20260402 build, gone from `typologies.py`. Not equivalent to High-Velocity Layering (fan-out→fan-in through *multiple* mules).

### 2c. Scaffolding / infrastructure gaps (block all the above)

1. **Alert schema drift.** [01-init.sql](../aml_platform/init-scripts/01-init.sql) L67–76 `alerts` table has only `(alert_type, severity, trigger_entity, related_transactions, status, created_at, resolved_at)`. v5 converged model wants `scenario_category` enum, `rail`, `ml_typology`, time window, and links to behavioural baselines. **Every new scenario has nowhere to record its category/rail.**
2. **No scenario-config abstraction.** Thresholds (10000, 0.95, 0.80, 3600s, mule_count≥3) are hardcoded inside Cypher strings. No `SCN_*` identity, no per-rail/per-window parameters, no tuning surface.
3. **No production scheduling.** `execute_rules_and_sink_alerts()` is invoked only by demo scripts ([run_demo_demo.py](../aml_platform/etl/run_demo_demo.py) L105, [reload_env_and_demo.py](../aml_platform/etl/reload_env_and_demo.py) L101). No Dagster T+1 batch asset, no realtime ingestion hook. v5 wants nightly BATCH (00:00–06:00 HKT) + REALTIME rules.
4. **No tests.** No `test_typologies.py` / `test_rule_engine.py` (STR module has tests; rules don't). Regressions like the dropped Rapid Movement rule went undetected.

---

## 3. Materialized build plan

Sequenced so each phase is independently shippable and unblocks the next. Target files are concrete.

### Phase 0 — Stabilize scaffolding (do first; everything depends on it)
- [ ] **0.1** Migrate `alerts` schema to v5: add `scenario_code`, `scenario_category` (enum), `rail`, `ml_typology`, `window_start`/`window_end`, `behavioural_input_ref`. New init script `init-scripts/04-alert-schema-v5.sql` (additive `ALTER TABLE`; keep back-compat columns).
- [ ] **0.2** Introduce a scenario registry: `aml_platform/etl/scenarios.py` — each entry = `{code, name, category, rail, mode, query|strategy, params, severity}`. Refactor `typologies.py` rules into this registry with stable `SCN_*` codes. `rule_engine.py` iterates the registry instead of `TYPOLOGIES`.
- [ ] **0.3** Parameterize Cypher thresholds via `params` (read from env / a `scenario_config` table) so tuning doesn't require code edits.
- [ ] **0.4** Add `test_rule_engine.py` + `test_typologies.py` with synthetic graph fixtures (seed a known circular / smurfing / peeling pattern, assert the expected alert). **Acceptance:** the Rapid-Movement regression is caught if re-introduced.
- [ ] **0.5** Write `typologies.py` → `scenarios.py` migration so existing 4 rules keep firing under the new registry (green tests).

### Phase 1 — Close the regression + highest-value typologies
- [ ] **1.1** Re-implement **Rapid Movement** (`SCN_RAPID_MVMT_01`): entity forwarding ≥90% of incoming funds within a window. Restore the 20260402 behaviour under the new registry.
- [ ] **1.2** Implement **Cross-Rail Layering** (`SCN_CROSS_RAIL_LAYER_01`): stablecoin inflow → fiat outflow within 48h, same beneficial owner. Requires the unified party/UBO graph edge (fiat account ↔ wallet via beneficial owner). This is the v5 headline — prioritize.
- [ ] **1.3** Implement **Rapid Layering realtime** (`SCN_LAYER_RAPID_01`): 24h roundtrip, 3+ hops (distinct from fan-out/fan-in).
- [ ] **1.4** Add fixtures + tests for 1.1–1.3.

### Phase 2 — Behavioural / baseline scenarios (T+1 batch)
- [ ] **2.1** **Structuring fiat + stablecoin** windows: 30-day rolling window, HKD 120k CTR (fiat) / HKD 8k Travel-Rule (stablecoin) thresholds. Replace the flat USD-10k Smurfing rule.
- [ ] **2.2** **Velocity** (`SCN_VELOCITY_01`): 3× count or 5× amount vs 90-day `customer_behaviour_baseline`. Needs the baseline table populated by the ETL.
- [ ] **2.3** **Dormant reactivation** (`SCN_DORMANT_01`): 12+ months dormant → large movement.
- [ ] **2.4** **Profile mismatch** (`SCN_PROFILE_MISMATCH_01`): actual vs `party.expected_txn_profile`.

### Phase 3 — Stablecoin / blockchain scenarios
- [ ] **3.1** **Blockchain risk** (`SCN_BLOCKCHAIN_RISK_01`, realtime): `ba_risk_score > 70`. Requires wallet-analytics adapter feed.
- [ ] **3.2** **Unhosted wallet** (`SCN_UNHOSTED_WALLET_01`): monthly volume > HKD 50k.
- [ ] **3.3** **Mixer/darknet exposure** (`SCN_MIXER_EXPOSURE_01`): >0 exposure in 90d.
- [ ] **3.4** **Travel Rule breach** (`SCN_TRAVEL_RULE_01`) and **fuzzy sanctions** (`SCN_SANCTIONS_RT_01`, 85% match) — promote from relational exact-match to AGE/fuzzy.

### Phase 4 — Graph-analytic typologies (beyond pairwise Cypher)
- [ ] **4.1** **Betweenness-centrality facilitation** detection (intermediary accounts in layering chains).
- [ ] **4.2** **Louvain community** detection for smurfing rings / coordinated mule networks.
- [ ] **4.3** Formal **cycle detection** as a named scenario (generalizes Circular Flow with window/rail).

### Phase 5 — Scheduling, observability, tuning loop
- [ ] **5.1** Wire BATCH scenarios into a **Dagster T+1 asset** (nightly 00:00–06:00 HKT) and REALTIME scenarios into the **ingestion hook**.
- [ ] **5.2** Alert-severity routing + dedupe across scenarios (one entity, multiple SCN hits → one case).
- [ ] **5.3** Tuning surface: scenario precision/recall dashboard; feedback from L2 outcomes → threshold adjustment (ties to v5 "Continuous Improvement & HITL" diagram, community 66).
- [ ] **5.4** Re-run `graphify --update` after Phase 1–2 land so the code↔spec communities finally link and the "surprising connections" reflect reality rather than drift.

---

## 4. Priority call

If only one phase ships first, it is **Phase 0 + 1.2 (Cross-Rail Layering)**: the scaffolding makes every later scenario cheap, and Cross-Rail Layering is the single scenario that justifies the platform's existence ("entirely invisible to siloed monitoring systems" — v5 spec). Rapid Movement (1.1) is a same-day fix and should ride along to close the regression.

> **Update (2026-07-10):** on review, Cross-Rail Layering (1.2) is **blocked** — see §5.2. Phase 0 + 1.1 + 1.3 shipped instead.

---

## 5. Execution log & review corrections (2026-07-10)

### 5.1 Shipped this increment (Phase 0 + Phase 1.1 + 1.3)

| Item | Artifact | Status |
|---|---|---|
| 0.1 Alerts schema v5 | [init-scripts/05-alert-schema-v5.sql](../aml_platform/init-scripts/05-alert-schema-v5.sql) | done — additive `ALTER`s (scenario_code/category/rail/ml_typology/window/rule_version) + indexes |
| 0.2 Scenario registry | [etl/scenarios.py](../aml_platform/etl/scenarios.py) | done — 6 scenarios, v5 enums, `RULE_VERSION` |
| 0.3 Parameterized thresholds | `scenarios.DEFAULT_PARAMS` + `rule_engine.resolve_params()` (env overrides) | done |
| 0.5 Migrate existing 4 rules | moved into registry verbatim | done |
| 1.1 Rapid Movement (regression fix) | `SCN_RAPID_MVMT_01` | done |
| 1.3 Rapid Layering realtime | `SCN_LAYER_RAPID_01` | done |
| 0.4 Contract tests | [etl/test_scenarios.py](../aml_platform/etl/test_scenarios.py) | done — **15/15 passing** |
| — rule_engine rewired to registry | [etl/rule_engine.py](../aml_platform/etl/rule_engine.py) | done — enriched alert insert |
| — backward-compat shim | [etl/typologies.py](../aml_platform/etl/typologies.py) | done — `TYPOLOGIES` derived from registry |

Run tests without a DB: `python aml_platform/etl/test_scenarios.py`

### 5.2 Deferred — blocked, with prerequisite

- **1.2 Cross-Rail Layering (`SCN_CROSS_RAIL_LAYER_01`)** — BLOCKED. The v5 scenario requires "stablecoin inflow → fiat outflow, **same beneficial owner**." The graph ([graph_loader.py](../aml_platform/etl/graph_loader.py)) only sets `Entity{id, system}` — there is **no party / beneficial-owner dimension** linking fiat accounts to wallets. Prerequisite: add a `party`/UBO model and a graph edge linking accounts/wallets to beneficial owners. Until then a cross-rail rule would be a weak "different rails near each other" heuristic, not the spec's intent.
- **Phase 2 (Velocity, Dormant, Profile Mismatch, Structuring-by-window + HKD thresholds)** — BLOCKED. Requires `customer_behaviour_baseline` / `wallet_behaviour_baseline` / `party.expected_txn_profile` / `account.account_status` tables (none exist), and amounts are stored as **USD** (`amount_usd`) while the v5 thresholds are **HKD** (120k CTR / 8k Travel Rule). Prerequisite: the baseline-table ETL + an HKD amount column (or FX rate).
- **Phase 3 (Blockchain risk, Unhosted wallet, Mixer, Travel Rule, fuzzy sanctions)** — BLOCKED on the wallet-analytics adapter feed + baseline tables.
- **Phase 4 (Betweenness / Louvain / formal cycle)** — separate graph-analytics effort.
- **Phase 5 (Dagster T+1 + realtime scheduling)** — belongs in the newer root [`etl/`](../etl/) Dagster tree, not `aml_platform/etl/`. Separate migration.

### 5.3 Review corrections to the original plan

- The alerts migration is **`05`**, not `04` — `04-users-and-workflow.sql` already exists.
- There are **two ETL trees**: the typology rules in `aml_platform/etl/` and a newer Dagster pipeline in root `etl/`. Phase 5 must target the Dagster tree.
- The graph is **USD-denominated** and **has no rail/UBO properties** beyond `system` — this is what blocks 1.2 and the Phase 2/3 thresholds.

### 5.4 Verification caveat (honesty)

Cypher correctness could **not** be live-fired here — no Docker/Postgres+AGE runtime (the 20260402 walkthrough notes the same constraint). The 4 migrated rules are preserved verbatim from the prior build; the 2 new rules reuse its timestamp-subtraction idiom so they validate together. **Before merge to production, run the live verification procedure:**

1. `cd aml_platform && docker-compose up -d`
2. Apply init scripts in order (01–05), then load demo data (`etl/run_demo_demo.py` or `reload_env_and_demo.py`).
3. `python etl/rule_engine.py` and confirm 6 scenarios execute; check `SELECT alert_type, severity, scenario_code FROM ag_catalog.alerts;` — expect rows for the seeded circular / smurfing patterns and **no** unhandled rule errors in the log.
4. Tune a threshold via env (`SMURFING_TOTAL_USD=8000 python etl/rule_engine.py`) and confirm the alert count changes — proving the param thread-through end to end.

---

## 6. Execution log — Part 2: party/UBO dimension + Dagster T+1 (2026-07-10)

### 6.1 Party/UBO dimension (unblocks 1.2 Cross-Rail Layering)

| Item | Artifact | Status |
|---|---|---|
| Party/UBO relational model + graph labels | [init-scripts/06-party-ubo-model.sql](../aml_platform/init-scripts/06-party-ubo-model.sql) | done — `party` / `party_instrument` / `party_ubo` + `Party`/`OWNED_BY`/`UBO_OF` labels + seed |
| Graph projection | [etl/party_loader.py](../aml_platform/etl/party_loader.py) | done — projects Party vertices, `OWNED_BY` (Entity→Party), `UBO_OF` (Party→Party) into aml_network |
| Cross-Rail scenario | `SCN_CROSS_RAIL_LAYER_01` in [scenarios.py](../aml_platform/etl/scenarios.py) | done — stablecoin inflow → fiat outflow, same UBO within 48h via `OWNED_BY` + `UBO_OF*0..3`; `CROSS_RAIL_WINDOW_SECONDS` / `CROSS_RAIL_STABLECOINS` params |
| Label gating | [rule_engine.py](../aml_platform/etl/rule_engine.py) | done — queries `ag_catalog.ag_label`, skips scenarios whose `requires_labels` are absent (logs guidance instead of erroring) |
| Tests | [test_scenarios.py](../aml_platform/etl/test_scenarios.py) | done — **18/18 passing** (+3 for Cross-Rail) |

Cross-Rail now degrades gracefully: it is skipped with a clear log line until `06` + `party_loader.py` run, then activates automatically. The original §5.2 "1.2 BLOCKED" is resolved.

### 6.2 Dagster T+1 detection (Phase 5 first increment)

**Key finding: the root `etl/` Dagster pipeline is a SEPARATE system from `aml_platform/etl/`.** Different database (`age_prod_01` vs `aml_platform`), different graph (`tap_and_go_network` with `Customer`/`Merchant`/`Counterparty` + `PAID`/`TRANSFERRED`, HKD — vs `aml_network` `Entity`/`Transfer`, USD). The aml_network scenarios **cannot** run against the Dagster-populated graph. So Phase 5 detection is implemented native to `tap_and_go`, as a parallel detection engine.

| Item | Artifact | Status |
|---|---|---|
| Alert sink (tap_and_go DB) | [etl/sql/alerts_schema.sql](../etl/sql/alerts_schema.sql) | done — `core.alerts`, v5-shaped |
| Detection module | [etl/detection.py](../etl/detection.py) | done — 2 tap_and_go-native scenarios (Structuring sub-HKD-8k; Circular Customer→Counterparty→Customer) + `run_typology_detection` op + `t1_detection_job` + `t1_detection_schedule` (cron `30 0 * * *`) |
| Registration | [etl/repo.py](../etl/repo.py) | done — job + schedule registered |

The detection schedule is **decoupled from the file-gated ingest job** — it runs nightly at 00:30 (after the 00:00 ingest+graph, within the v5 T+1 window) whether or not a new file arrived, so alerts are produced every T+1. The original §5.2 "Phase 5 — separate migration" has its first increment.

**Limitation:** `tap_and_go` edges project only `{txn_hash, amount}` — no timestamp — so only amount/topology rules are expressible today. Velocity & rapid-movement require projecting `core.transactions.txn_date` onto edges (follow-up).

### 6.3 Verification caveat (Part 2)

Neither live Postgres+AGE nor a Dagster daemon was available here. All modules compile; contract tests 18/18; Cypher rendered and inspected for both engines. Before production: apply `06` + `alerts_schema.sql`, run `party_loader.py` then `rule_engine.py` (aml_platform); and bring up the Dagster daemon to confirm `t1_detection_schedule` fires and `core.alerts` populates (extend the §5.4 procedure to both systems).

### 6.4 Open: unify the two ETL/graph systems

`aml_platform` (`aml_network`, USD, `Entity`/`Transfer`) and `etl/` Dagster (`tap_and_go_network`, HKD, `Customer`/`Counterparty`) are parallel implementations of the same product. Consolidating them — one graph schema, one rail/currency-aware scenario registry — is the strategic follow-up that would let a single detection engine serve both. Tracked, not started.

### 6.5 Timestamp-gap closure — velocity & rapid-movement land (2026-07-10)

Closes the §6.2 limitation (tap_and_go edges lacked timestamps, so only amount/topology rules were expressible).

| Item | Artifact | Status |
|---|---|---|
| Project `ts` onto edges | [etl/assets/graph_projection.py](../etl/assets/graph_projection.py) + [etl/daily_pipeline.py](../etl/daily_pipeline.py) `update_graph_model` | done — PAID/TRANSFERRED edges now carry `ts = EXTRACT(EPOCH FROM txn_date)::bigint` (COALESCE 0). Minimal-risk: the proven MERGE pattern `{txn_hash, amount}` is preserved and `SET e.ts = %s` appends the epoch, so existing edges are updated, not duplicated |
| Rapid-movement rule | `TG_SCN_RAPID_MVMT_01` in [etl/detection.py](../etl/detection.py) | done — Customer receiving funds then forwarding ≥90% within 24h, windowed on projected `ts` |
| Velocity rule | `TG_SCN_VELOCITY_BURST_01` | done — SQL window: ≥10 payments totaling ≥HKD 50k in any trailing 1h window over `core.transactions.txn_date` |
| Contract tests | [etl/test_detection.py](../etl/test_detection.py) | done — **9/9 passing** |

tap_and_go detection is now 4 scenarios (Structuring, Circular, Rapid Movement, Velocity Burst); `RULE_VERSION` bumped to `2026.07-tap-and-go-detection-2`.

NOTE: the velocity rule is an **absolute burst**, not baseline-relative — the v5 `SCN_VELOCITY_01` ("3× count or 5× amount vs a 90-day baseline") still needs a `customer_behaviour_baseline` table (not built). Same verification caveat as §6.3: not live-fired here.

---

## 7. Unification — one rail/currency-aware detection engine for both graphs

**Status: PLANNED (not started).** This section is the atomic build plan for the §6.4 follow-up. No code is written in this pass — this is the breakdown.

### 7.1 Goal & strategy decision

Goal: a **single scenario registry + execution engine** that serves BOTH physical graphs (`aml_network` and `tap_and_go_network`), so detection logic is authored once and tuned in one place.

**Decision — Option A: profile-abstracted shared core; both physical graphs remain.** The engine renders concrete Cypher per graph via a *profile* that maps a canonical abstract schema onto each graph's labels/properties, and a *currency resolver* normalizes thresholds. **Rejected — Option B** (migrate to one canonical physical graph): high migration risk, requires re-projecting all historical data and reconciling node identity (`Entity` ↔ `Customer`/`Counterparty`/`Merchant`); deferred until a federated/single-DB need materialises.

Rationale: matches the stated intent ("one engine serves both graphs"), non-invasive (no historical data migration), incremental, reversible. Each engine run still targets **one** graph/DB — cross-graph/federated detection is explicitly out of scope (would need a single DB = Option B).

### 7.2 Current divergences (the contract the abstraction must span)

| Dimension | aml_network (aml_platform) | tap_and_go_network (Dagster) |
|---|---|---|
| DB | `aml_platform` @ localhost:5432 | `age_prod_01` @ age_db:5432 |
| Node labels | `Entity`, `SuperNode`, `Party` | `Customer`, `Counterparty`, `Merchant` |
| Edge labels | `Transfer` | `PAID`, `TRANSFERRED` |
| Amount prop | `amount_usd` (USD) | `amount` (HKD) |
| Timestamp prop | `timestamp` (ISO string) | `ts` (epoch seconds) |
| Ref prop | `ref_id` | `txn_hash` |
| Rail prop | `system` (FIAT/chain) + `asset` | none (all FIAT) |
| Party/UBO | yes (`Party`, `OWNED_BY`, `UBO_OF`) | no |
| Alert sink | `ag_catalog.alerts` (+ v5 cols) | `core.alerts` |
| Scenarios | 7 (`scenarios.py`) | 4 (`detection.py`) |

### 7.3 Canonical abstract contract (the registry is authored against this)

- Abstract node **`Account`** → mapped by profile to concrete label(s) (incl. label-unions like `Customer|Counterparty|Merchant`). Role distinctions (customer/merchant/wallet) carried as a property where the graph keeps them.
- Abstract edge **`Transfer`** with normalised properties: `value` (numeric), `ts` (epoch seconds), `ref` (id), optional `asset`, optional `rail`.
- Optional **party dimension**: `Party` + `owns` / `ubo_of` edges (capability-gated — present only on profiles that have it).

### 7.4 GraphProfile spec (dataclass)

`name`, `graph_name`, db connection; `account_label`, `transfer_label`; `prop_value`, `base_ccy`; `prop_ts` (+ `ts_is_epoch`); `prop_ref`; `prop_rail` (or constant); `capabilities{has_party, party_label, owns_label, ubo_label}`; `alert_table` (schema-qualified).

- **aml_network**: `account_label="Entity|SuperNode"`, `transfer_label="Transfer"`, `prop_value="amount_usd"`, `base_ccy="USD"`, `prop_ts="ts"` *(after U4)*, `prop_ref="ref_id"`, `prop_rail="system"`, `has_party=True`, `alert_table="ag_catalog.alerts"`.
- **tap_and_go**: `account_label="Customer|Counterparty|Merchant"`, `transfer_label="PAID|TRANSFERRED"`, `prop_value="amount"`, `base_ccy="HKD"`, `prop_ts="ts"`, `prop_ref="txn_hash"`, `prop_rail="FIAT"` (constant), `has_party=False`, `alert_table="core.alerts"`.

### 7.5 Currency handling decision

Default: **per-currency thresholds** via a `CurrencyResolver` — a scenario declares thresholds keyed by currency, the profile selects its currency's value. Robust, no FX dependency, no in-query math. Optional future enhancement: an FX normaliser to a base HKD once an FX source exists (interface reserved, not built in the first increment).

### 7.6 Atomic task breakdown

Sequencing: **U0 → (U1 ∥ U4) → U2 → U3 → U5 → U7**, with U6 tests authored alongside each phase (test-first where feasible).

#### Phase U0 — Decide & document (no code)
- [x] **U0.1** Write ADR `docs/adr/0001-unified-detection-engine.md`: record Option A chosen, Option B rejected (with reasons), the abstract contract, profile spec.
- [x] **U0.2** In the ADR, define the canonical abstract contract (§7.3) and profile fields (§7.4) as the spec the rest of the work implements against.

#### Phase U1 — Shared core skeleton (new top-level package `aml_detection/`)
- [x] **U1.1** Create `aml_detection/` package (`__init__.py`); decide import boundary (no dagster/psycopg2 at import time — pass connections in).
- [x] **U1.2** `aml_detection/contract.py`: enums (`Category`, `Rail`, `Severity`, `Currency`), `Scenario` dataclass, `GraphProfile` dataclass, `Capabilities` dataclass.
- [x] **U1.3** `aml_detection/currency.py`: `CurrencyResolver` (per-currency threshold lookup + reserved FX-hook) with unit tests.
- [x] **U1.4** `aml_detection/profiles/aml_network.py` + `tap_and_go.py`: instantiate the two `GraphProfile` objects.
- [x] **U1.5** `aml_detection/alerts.py`: `AlertSink` — schema-qualified insert adapter that handles the column-superset diff (`ag_catalog.alerts` has extra `alert_type`/`ml_typology`/`window_*`; `core.alerts` does not) by inserting only columns the target table exposes.

#### Phase U4 — Prereq: normalise aml_network timestamps to epoch (enables unified time-window rules)
- [x] **U4.1** Migrate `aml_platform/etl/graph_loader.py` to project `ts` (epoch) on `Transfer` edges alongside the existing ISO `timestamp` (mirror what tap_and_go already does). Additive — keep `timestamp` for back-compat.
- [ ] **U4.2** Back-fill note: existing aml_network edges need re-projection (`run_graph_promotion()` re-run) to gain `ts`; document in the runbook. *(code migration done; back-fill is an operational runbook step — see U7.2)*

#### Phase U2 — Canonical registry + renderer
- [x] **U2.1** `aml_detection/registry.py`: merge the 7 aml_network + 4 tap_and_go scenarios into ONE abstract registry, **deduplicating** the overlaps (Structuring, Circular, Rapid Movement exist in both → become single abstract scenarios rendered per profile). Add `requires_capabilities` to scenarios that need the party dimension (Cross-Rail). *(SCOPE NOTE: the tap_and_go SQL velocity rule `TG_SCN_VELOCITY_BURST_01` is NOT ported — it's a SQL window rule with no aml_network equivalent and doesn't fit the abstract-Cypher model; it stays in `etl/detection.py` until the engine grows SQL-rule support. Registry = 7 abstract Cypher scenarios.)*
- [x] **U2.2** `aml_detection/render.py`: the renderer — abstract scenario + profile + resolved params/currency → concrete Cypher (substitute `account_label`, `transfer_label`, `prop_value`, `prop_ts`, `prop_ref`, `graph_name`; apply per-currency threshold).
- [x] **U2.3** Capability gating: scenario declares `requires_capabilities` (e.g. `PARTY_DIMENSION`); engine skips with a guidance log when the profile lacks it (generalises the aml_network-only label gate from §6.1).

#### Phase U3 — Unified engine
- [x] **U3.1** `aml_detection/engine.py`: `detect(profile, conn)` — introspect graph capabilities (labels), iterate registry, render per profile, gate, execute, sink via `AlertSink`; return a run summary. No dagster/psycopg2 imports at module top (connection passed in).
- [x] **U3.2** Per-rule error isolation (rollback + log + continue) — port the pattern both existing engines already use. *(Refined: commit-per-rule so a later rollback cannot drop earlier rules' alerts — stronger than the original engines' single end-commit.)*

#### Phase U5 — Wire both consumers to the shared engine
- [ ] **U5.1** aml_platform: rewrite `aml_platform/etl/rule_engine.py` to call `aml_detection.engine.detect(AML_NETWORK_PROFILE, conn)`; reduce `scenarios.py`/`typologies.py` to back-compat shims.
- [ ] **U5.2** Dagster: rewrite `etl/detection.py` `run_typology_detection` to call `aml_detection.engine.detect(TAP_AND_GO_PROFILE, conn)`; keep the Dagster job/schedule wrapper intact.
- [ ] **U5.3** Packaging: make `aml_detection/` importable from the Dagster container (update `etl/Dockerfile` COPY + requirements) and from the aml_platform venv.

#### Phase U6 — Tests (authored alongside each phase; collected here)
- [ ] **U6.1** `test_contract.py`: `Scenario`/`GraphProfile`/`Capabilities` invariants (required fields, enum validity, unique codes).
- [ ] **U6.2** `test_currency.py`: per-currency resolution + FX-hook behaviour.
- [x] **U6.3** `test_render.py`: **snapshot** concrete Cypher per profile (aml_network + tap_and_go) for every scenario; assert well-formed + correct label/property/currency substitution. This is where AGE label-union support gets proven out. *(12/12 passing — label-unions render incl. `[PAID|TRANSFERRED*2..5]`; exact golden snapshots lock the 3 deduped scenarios. NOTE: proves the rendered STRING; live AGE acceptance of multi-label variable paths still needs the U7.2 check, fallback = per-label UNION queries.)*
- [ ] **U6.4** `test_engine.py`: engine over a fake cursor — capability gating fires, per-rule isolation, alert sinking through both `AlertSink` variants.
- [ ] **U6.5** `test_profiles.py`: each profile resolves every abstract field (no missing props); currency/threshold coverage for each scenario the profile will run.
- [ ] **U6.6** Regression: port/keep the existing 18 (aml_platform) + 9 (tap_and_go) contract tests green against the shims, or migrate them into `aml_detection/tests/`.

#### Phase U7 — Deprecation, runbook, closeout
- [ ] **U7.1** Deprecation warnings on `aml_platform/etl/scenarios.py`, `typologies.py`, `etl/detection.py` pointing at `aml_detection`.
- [ ] **U7.2** Migration runbook: no data migration (Option A); deploy shared package, re-point engines, re-project aml_network edges for `ts` (U4.2), verify per §5.4/§6.3 on both graphs.
- [ ] **U7.3** Update this section with a completion log + mark §6.4 resolved.

#### Phase U8 — Out-of-scope, documented (future)
- [ ] **U8.1** Document that cross-graph/federated detection is out of scope (each run targets one graph/DB); a federated single-DB view is the deferred Option B milestone.

### 7.7 Risks & open questions
- **AGE label-union `(A|B|C)` support is unverified** — the tap_and_go profile depends on it; U2.2/U6.3 must confirm against a live AGE instance (fallback: the profile expands to a UNION of per-label queries).
- **aml_network ISO→epoch `ts` migration (U4)** changes `graph_loader.py`; existing edges must be re-projected — coordinate the runbook.
- **AGE `MERGE … SET` semantics** — already flagged in earlier phases; carried forward.
- **Dagster container packaging (U5.3)** — the shared package must be on the image path; verify the COPY + import in the Dagster run.
- **Currency** — per-currency thresholds are the pragmatic default; revisit if an FX source appears and a single HKD-normalised threshold is preferred.
