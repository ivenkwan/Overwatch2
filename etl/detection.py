"""
T+1 typology detection for the tap_and_go pipeline (Dagster).

NATIVE to the tap_and_go_network graph (Customer / Counterparty / Merchant
nodes; PAID / TRANSFERRED edges carrying {txn_hash, amount_in_HKD}). This is
a SEPARATE detection engine from aml_platform/etl/scenarios.py, which targets
the aml_network graph in a different database — see
Implementation_Plan/20260710_typology_gap_plan.md §5.2 / §6 (two systems).

Runs as a decoupled nightly job so alerts are produced every T+1 window
regardless of whether a new ingest file arrived (the ingest daily_update_job
is file-gated and skips no-file days). Scheduled at 00:30 — after the 00:00
ingest+graph, inside the v5 T+1 window 00:00-06:00 HKT.

Each scenario is a SELECT returning (entity_id, tx_hashes); the op executes
them uniformly. Cypher scenarios target tap_and_go_network (edges now carry
{txn_hash, amount, ts} where ts = EXTRACT(EPOCH FROM txn_date), projected by
graph_projection.py / daily_pipeline.py). SQL scenarios query
core.transactions directly where window functions are cleaner (velocity).

NOTE: SCN_VELOCITY_BURST_01 is absolute (>= N txns / >= HKD S in a 1h window),
NOT baseline-relative — the v5 SCN_VELOCITY_01 ("3x count or 5x amount vs a
90-day baseline") still needs a customer_behaviour_baseline table (not built).

Cypher correctness could not be live-fired here (no Docker/Postgres+AGE
runtime); verify per the plan's §5.4 procedure before production.
"""

import os
import json
import psycopg2
from dagster import op, job, schedule, RunRequest, DefaultScheduleStatus

POSTGRES_URI = os.getenv("POSTGRES_URI", "postgresql://postgres:password@age_db:5432/age_prod_01")
RULE_VERSION = "2026.07-tap-and-go-detection-2"

# tap_and_go-native scenarios. Thresholds are HKD (tap_and_go is a HK fiat rail).
# `kind` is documentary — every scenario is a SELECT returning (entity_id,
# tx_hashes) and the op executes them uniformly. Cypher rules use the `ts`
# epoch now projected onto edges; the SQL rule uses core.transactions.txn_date.
SCENARIOS = [
    {
        "code": "TG_SCN_STRUCT_01",
        "name": "STRUCTURING_SUB_THRESHOLD",
        "category": "STRUCTURING",
        "rail": "FIAT",
        "severity": "HIGH",
        "kind": "cypher",
        "description": "Customer making many sub-HKD-8k payments that aggregate past HKD 20k.",
        "query": (
            "SELECT * FROM cypher('tap_and_go_network', $$\n"
            "    MATCH (c:Customer)-[e:PAID|TRANSFERRED]->(x)\n"
            "    WHERE e.amount < 8000\n"
            "    WITH c, count(e) AS tx_count, sum(e.amount) AS total_hkd, collect(e.txn_hash) AS hashes\n"
            "    WHERE tx_count >= 5 AND total_hkd >= 20000\n"
            "    RETURN c.id AS entity_id, hashes\n"
            "$$) as (entity_id agtype, tx_hashes agtype);\n"
        ),
    },
    {
        "code": "TG_SCN_CIRCULAR_01",
        "name": "CIRCULAR_FLOW",
        "category": "CIRCULAR_FLOW",
        "rail": "FIAT",
        "severity": "CRITICAL",
        "kind": "cypher",
        "description": "Funds leaving a Customer to a Counterparty and returning (round-tripping).",
        "query": (
            "SELECT * FROM cypher('tap_and_go_network', $$\n"
            "    MATCH (c:Customer)-[e1:TRANSFERRED]->(cp:Counterparty)-[e2:TRANSFERRED]->(c:Customer)\n"
            "    WITH c, collect(DISTINCT e1.txn_hash) + collect(DISTINCT e2.txn_hash) AS hashes\n"
            "    RETURN c.id AS entity_id, hashes\n"
            "$$) as (entity_id agtype, tx_hashes agtype);\n"
        ),
    },
    {
        "code": "TG_SCN_RAPID_MVMT_01",
        "name": "RAPID_MOVEMENT",
        "category": "RAPID_MOVEMENT",
        "rail": "FIAT",
        "severity": "HIGH",
        "kind": "cypher",
        "description": "Customer receiving funds then forwarding >=90% of the received amount "
                       "within 24h (mule pass-through). Uses the projected ts epoch for the window.",
        "query": (
            "SELECT * FROM cypher('tap_and_go_network', $$\n"
            "    MATCH (cp:Counterparty)-[tin:TRANSFERRED]->(c:Customer)\n"
            "    MATCH (c)-[tout:PAID|TRANSFERRED]->(dst)\n"
            "    WHERE tout.ts >= tin.ts AND tout.ts - tin.ts < 86400\n"
            "    WITH c, sum(tin.amount) AS in_total, sum(tout.amount) AS out_total,\n"
            "         collect(DISTINCT tin.txn_hash) + collect(DISTINCT tout.txn_hash) AS hashes\n"
            "    WHERE in_total > 0 AND out_total >= in_total * 0.90\n"
            "    RETURN c.id AS entity_id, hashes\n"
            "$$) as (entity_id agtype, tx_hashes agtype);\n"
        ),
    },
    {
        "code": "TG_SCN_VELOCITY_BURST_01",
        "name": "VELOCITY_BURST",
        "category": "VELOCITY",
        "rail": "FIAT",
        "severity": "HIGH",
        "kind": "sql",
        "description": "Customer with >= 10 payments totaling >= HKD 50k in any trailing 1h window "
                       "(absolute burst; baseline-relative v5 SCN_VELOCITY_01 needs a baseline table).",
        "query": (
            "WITH windows AS (\n"
            "    SELECT customer_num, txn_hash,\n"
            "           COUNT(*) OVER w AS win_count,\n"
            "           SUM(txn_amount_in_hkd) OVER w AS win_total\n"
            "    FROM core.transactions\n"
            "    WINDOW w AS (PARTITION BY customer_num ORDER BY txn_date\n"
            "                 RANGE BETWEEN INTERVAL '1 hour' PRECEDING AND CURRENT ROW)\n"
            ")\n"
            "SELECT customer_num AS entity_id, array_agg(DISTINCT txn_hash) AS tx_hashes\n"
            "FROM windows\n"
            "WHERE win_count >= 10 AND win_total >= 50000\n"
            "GROUP BY customer_num;\n"
        ),
    },
]


def get_db_connection():
    try:
        return psycopg2.connect(POSTGRES_URI)
    except psycopg2.OperationalError:
        # Fallback for local dev (host-mapped port 5433, matching daily_pipeline.py)
        return psycopg2.connect("postgresql://postgres:password@localhost:5433/age_prod_01")


@op
def run_typology_detection(context):
    """Evaluate tap_and_go typology rules and sink hits into core.alerts.

    Requires core.alerts (etl/sql/alerts_schema.sql) and a populated
    tap_and_go_network graph (daily_pipeline.update_graph_model). Per-rule
    errors are rolled back and logged so one bad rule never halts the batch.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    fired = 0
    try:
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, public;")

        for scenario in SCENARIOS:
            context.log.info("Evaluating %s [%s] (%s)", scenario["name"], scenario["code"], scenario["rail"])
            try:
                cur.execute(scenario["query"])
                hits = cur.fetchall()
                if hits:
                    context.log.info("%s fired %d alert(s)", scenario["name"], len(hits))
                for entity_id, tx_hashes in hits:
                    cur.execute(
                        "INSERT INTO core.alerts "
                        "(scenario_code, scenario_category, rail, severity, trigger_entity, "
                        " related_transactions, rule_version) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (
                            scenario["code"], scenario["category"], scenario["rail"], scenario["severity"],
                            str(entity_id), json.dumps(tx_hashes), RULE_VERSION,
                        ),
                    )
                    fired += 1
            except Exception as e:
                conn.rollback()
                context.log.error("Rule %s failed: %s", scenario["name"], e)
                continue

        conn.commit()
    finally:
        cur.close()
        conn.close()

    context.log.info("T+1 detection complete: %d alert(s) sunk (rule_version=%s).", fired, RULE_VERSION)
    return fired


@job
def t1_detection_job():
    """Nightly T+1 typology detection over the tap_and_go graph."""
    run_typology_detection()


@schedule(
    job=t1_detection_job,
    cron_schedule="30 0 * * *",  # 00:30 daily — after the 00:00 ingest+graph, within T+1 window
    default_status=DefaultScheduleStatus.RUNNING,
)
def t1_detection_schedule(context):
    """T+1 detection schedule. Runs every night regardless of ingest files.

    Set the Dagster daemon timezone to Asia/Hong_Kong for correct local
    scheduling (the existing daily_update_schedule uses the same convention).
    """
    return RunRequest(run_key="t1_detection_" + context.scheduled_execution_time.strftime("%Y%m%d"))
