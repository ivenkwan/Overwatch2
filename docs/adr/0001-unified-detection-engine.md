# ADR 0001: Unified rail/currency-aware detection engine (profile abstraction)

- **Status:** Accepted (2026-07-10)
- **Planning reference:** [Implementation_Plan/20260710_typology_gap_plan.md](../../Implementation_Plan/20260710_typology_gap_plan.md) §6.4 / §7
- **Implementation:** not yet started — this ADR is the spec the build (phases U1–U7) implements against.

## Context

Two parallel detection engines detect the same AML typologies against different graph schemas, so detection logic is duplicated and drifts between them:

| Dimension | `aml_network` (aml_platform) | `tap_and_go_network` (Dagster) |
|---|---|---|
| DB | `aml_platform` @ localhost:5432 | `age_prod_01` @ age_db:5432 |
| Node labels | `Entity`, `SuperNode`, `Party` | `Customer`, `Counterparty`, `Merchant` |
| Edge labels | `Transfer` | `PAID`, `TRANSFERRED` |
| Amount | `amount_usd` (USD) | `amount` (HKD) |
| Timestamp | `timestamp` (ISO string) | `ts` (epoch seconds) |
| Ref / Rail | `ref_id` / `system` (+ `asset`) | `txn_hash` / none (all FIAT) |
| Party/UBO | yes | no |
| Sink | `ag_catalog.alerts` | `core.alerts` |
| Scenarios | 7 (`aml_platform/etl/scenarios.py`) | 4 (`etl/detection.py`) |

Goal: **one scenario registry + one execution engine that serves both graphs**, so detection logic is authored once and tuned in one place.

## Decision

**Option A — a profile-abstracted shared core.** A new repo-root package `aml_detection/` owns a canonical abstract scenario registry, a per-graph *profile* that maps the abstract schema onto each graph's concrete labels/properties, a currency resolver, and an engine that renders concrete Cypher per profile and executes it. **Both physical graphs remain**; each engine run targets exactly one graph/DB.

Canonical abstract contract the registry is authored against:
- Abstract node **`Account`** → profile label(s), incl. openCypher label-unions (e.g. `Customer|Counterparty|Merchant`). Role distinctions are a property where the graph keeps them.
- Abstract edge **`Transfer`** with normalised properties: `value` (numeric), `ts` (epoch seconds), `ref` (id), optional `asset`, optional `rail`.
- Optional **party dimension** (`Party` + `owns`/`ubo_of`) — capability-gated; present only on profiles that have it.

`GraphProfile` fields: `name`, `graph_name`, db connection, `account_label`, `transfer_label`, `prop_value`, `base_ccy`, `prop_ts` (+ `ts_is_epoch`), `prop_ref`, `prop_rail` (or constant), `capabilities{has_party, party_label, owns_label, ubo_label}`, `alert_table` (schema-qualified).

## Alternatives considered

**Option B — migrate to one canonical physical graph.** Rejected (for now): requires re-projecting all historical data into a single schema and reconciling node identity (`Entity` ↔ `Customer`/`Counterparty`/`Merchant`); high risk to two working pipelines for no near-term benefit. The stated intent is "one engine serves both **graphs**" (plural), which Option A satisfies. Option B remains a deferred milestone if a federated single-DB view is ever required.

## Consequences

**Positive**
- Single source of truth for detection logic; tune thresholds once.
- Non-invasive: no historical data migration (Option A); both pipelines keep working.
- Incremental and reversible — the legacy `scenarios.py`/`detection.py` become thin shims.

**Negative / risks**
- An adapter layer (profiles + renderer) adds indirection and its own test surface.
- **AGE label-union `(A|B|C)` support is unverified** — the `tap_and_go` profile depends on it; must be proven by render-snapshot tests (plan task U6.3). Fallback: expand to a `UNION` of per-label queries.
- Each run still targets one graph/DB — **cross-graph / federated detection remains out of scope** (would require a single DB = Option B).
- `aml_network` edges must gain epoch `ts` (plan task U4) before unified time-window rules work there.

## Decisions locked here

- **Package location:** repo-root `aml_detection/`.
- **Import boundary:** `aml_detection` must NOT import `dagster` or `psycopg2` at module top — connections are passed in, so the package is unit-testable and importable from both runtimes.
- **Currency (v1):** per-currency thresholds via a `CurrencyResolver` (no FX dependency, no in-query math). An FX-normaliser to base HKD is a reserved interface, not built in v1.
- **Canonical timestamp:** epoch seconds. `aml_network` gains a `ts` epoch property alongside its existing ISO `timestamp` (additive — task U4).
- **Currency base (if/when FX added):** HKD (the regulatory currency).

## References

- Plan §7 — full atomic task breakdown (phases U0–U8).
- Plan §5.2 / §6.4 — origin of the unification requirement.
