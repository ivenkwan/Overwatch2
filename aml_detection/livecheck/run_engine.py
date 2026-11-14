"""Live verification driver for TASK-061 + TASK-062 (2026-09-03).

Proves, against a real Apache AGE instance, that:
  * the unified engine runs the full 8-scenario registry with zero rule
    errors and zero server crashes — including the two TASK-062 rewrites
    (PEELING_CHAIN / RAPID_LAYERING), which previously crashed AGE via
    ``ALL(range(...))`` predicates over ``relationships(pth)``;
  * detection alerts land in the operational tenant-scoped ``app.alerts``
    sink (TASK-061): tenant-stamped, lowercase-'open', severity-mapped
    risk_score, scenario metadata in the JSONB payload, and
    ``payload->>'txn_hash'`` = first related tx so the existing alert-triage
    transitions can act on engine alerts;
  * negative controls (increasing-value chain, 7200s-gap chain) do not fire
    their targeted rules.

All SQL in this driver is parameterized; the Cypher fixtures/cleanup live in
the sibling .sql files because AGE requires the Cypher body as one
dollar-quoted string (bind parameters cannot appear inside it — the
documented TASK-003 constraint).

Procedure (compose stack; DB exposed on localhost:5433):

    docker exec -i aml-age-db psql -U postgres -d age_prod_01 -v ON_ERROR_STOP=1 \
        < aml_detection/livecheck/task061_062_fixtures.sql

    PGHOST=localhost PGPORT=5433 PGDATABASE=age_prod_01 PGUSER=postgres \
        PGPASSWORD=<from your .env> uv run --with psycopg2-binary \
        python aml_detection/livecheck/run_engine.py

    docker exec -i aml-age-db psql -U postgres -d age_prod_01 -v ON_ERROR_STOP=1 \
        < aml_detection/livecheck/task061_062_cleanup.sql

Not part of the unit suite (needs the live DB); excluded from mypy strict for
the same reason.
"""

import json
import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import psycopg2  # provided via uv --with psycopg2-binary; connection via PG* env vars

from aml_detection.engine import detect
from aml_detection.profiles import AML_NETWORK

#: Inlined literal (not imported) so the driver's SQL parameters trace to a
#: local constant — keep in sync with aml_detection.engine.RULE_VERSION
#: ("2026.09-aml-detection-workbench").
RULE_VERSION = "2026.09-aml-detection-workbench"

#: The tenant engine alerts are stamped with — T_DEMO is seeded by
#: backend/init_scripts in the compose stack. Override via AML_TENANT_ID.
TENANT = os.environ.get("AML_TENANT_ID", "6006dc90-28dd-4c52-9fe7-a5dbecdea7ae")


def main():
    conn = psycopg2.connect()  # PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD
    cur = conn.cursor()

    profile = replace(AML_NETWORK, alert_table="app.alerts")
    summary = detect(profile, conn, tenant_id=TENANT)
    print("ENGINE SUMMARY:", json.dumps(summary, indent=2))
    assert summary["errors"] == [], f"rule errors: {summary['errors']}"

    cur.execute("SELECT alert_type, status, customer_id, risk_score, payload->>'scenario_code', payload->>'txn_hash', tenant_id FROM app.alerts WHERE payload->>'rule_version' = %s ORDER BY alert_type, customer_id", (RULE_VERSION,))
    rows = cur.fetchall()
    print(f"\nAPP.ALERTS written by the engine: {len(rows)} rows")
    for r in rows:
        print("  ", r)

    fired_types = {r[0] for r in rows}
    assert "PEELING_CHAIN" in fired_types, "TASK-062: peeling rewrite did not fire"
    assert "RAPID_LAYERING" in fired_types, "TASK-062: rapid-layering rewrite did not fire"
    assert not any(r[0] == "PEELING_CHAIN" and "LVPEELNEG" in (r[5] or "") for r in rows), "negative-control peeling fired"
    assert not any(r[0] == "RAPID_LAYERING" and "LVRLNEG" in (r[5] or "") for r in rows), "negative-control rapid-layering fired"
    assert all(r[1] == "open" for r in rows), "status must be lowercase 'open'"
    assert all(str(r[6]) == TENANT for r in rows), "tenant_id must be stamped on every row"
    assert any(r[0] == "CROSS_RAIL_LAYERING" for r in rows), "cross-rail fixture should fire"
    assert any(r[0] == "AUTHORIZATION_DRIFT" for r in rows), "auth-drift fixture should fire"

    peel_alert = next(r for r in rows if r[0] == "PEELING_CHAIN" and r[2] == "LVPEEL_A")
    assert peel_alert[5] == "LVPEEL_TX_1", f"triage key should be first ref: {peel_alert}"
    assert float(peel_alert[3]) == 75.0, f"HIGH severity -> risk 75.0, got {peel_alert[3]}"

    # The triage transition key must select engine alerts (alerts.py routes it).
    cur.execute("UPDATE app.alerts SET status = 'triaged' WHERE payload->>'txn_hash' = %s AND payload->>'rule_version' = %s RETURNING alert_id", ("LVPEEL_TX_1", RULE_VERSION))
    triaged = cur.fetchall()
    assert len(triaged) >= 1, "triage key did not select the engine alert"
    print(f"\nTRIAGE KEY UPDATE via payload->>'txn_hash': {len(triaged)} alert(s) -> triaged")
    conn.rollback()  # leave the row 'open'; graph/alert cleanup happens in the .sql

    cur.execute("SELECT 1")  # server alive after the full registry run
    print("SERVER ALIVE after full registry run (incl. the two rewritten rules).")
    cur.close()
    conn.close()
    print("\nLIVE VERIFICATION PASSED")


if __name__ == "__main__":
    main()
