"""Tests for aml_detection.alerts (plan U1.5 / U6). No DB.

Verifies the AlertSink adapts to each table's column set (the column-superset
diff between ag_catalog.alerts and core.alerts) and that ``resolve_columns``
parses the schema-qualified table name.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aml_detection.alerts import AlertSink, resolve_columns  # noqa: E402
from aml_detection.contract import Category, Mode, Rail, Scenario, Severity  # noqa: E402
from aml_detection.profiles import AML_NETWORK, TAP_AND_GO  # noqa: E402


class FakeCur:
    def __init__(self):
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return []


_S = Scenario(code="SCN_STRUCT_01", name="STRUCTURING", category=Category.STRUCTURING,
              rail=Rail.FIAT, mode=Mode.BATCH, severity=Severity.HIGH, description="d")

AML_COLS = {
    "alert_id", "alert_type", "scenario_code", "scenario_category", "rail",
    "ml_typology", "severity", "trigger_entity", "related_transactions",
    "window_start", "window_end", "rule_version", "status", "created_at", "resolved_at",
}
TG_COLS = {
    "alert_id", "scenario_code", "scenario_category", "rail", "severity",
    "trigger_entity", "related_transactions", "rule_version", "status", "created_at", "resolved_at",
}


def test_aml_network_sink_writes_full_superset():
    cur = FakeCur()
    AlertSink(AML_NETWORK, cur, columns=AML_COLS).sink(
        scenario=_S, entity_id="ACC_1", tx_hashes=["h1", "h2"], rule_version="v1",
    )
    sql, params = cur.executed[-1]
    assert "INSERT INTO ag_catalog.alerts" in sql
    # aml_network table has alert_type and ml_typology => they are written.
    assert "alert_type" in sql and "ml_typology" in sql
    assert "STRUCTURING" in params and "SCN_STRUCT_01" in params
    # 10 authored columns present in this table.
    assert sql.count("%s") == 10


def test_tap_and_go_sink_omits_absent_columns():
    cur = FakeCur()
    AlertSink(TAP_AND_GO, cur, columns=TG_COLS).sink(
        scenario=_S, entity_id="C_9", tx_hashes=["t1"], rule_version="v1",
    )
    sql, params = cur.executed[-1]
    assert "INSERT INTO core.alerts" in sql
    # core.alerts lacks alert_type and ml_typology => must NOT appear.
    assert "alert_type" not in sql and "ml_typology" not in sql
    assert "scenario_code" in sql and "trigger_entity" in sql
    assert sql.count("%s") == 8  # the 8 authored cols present in core.alerts


def test_resolve_columns_parses_schema_qualified_table():
    seen = {}

    class Cur:
        def execute(self, sql, params=None):
            seen["sql"] = sql
            seen["params"] = params

        def fetchall(self):
            # Pretend the table has these columns.
            return [("scenario_code",), ("severity",)]

    cols = resolve_columns(Cur(), "ag_catalog.alerts")
    assert cols == {"scenario_code", "severity"}
    assert seen["params"] == ("ag_catalog", "alerts")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for fn in fns:
        try:
            fn(); print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failures += 1; print(f"FAIL  {fn.__name__}: {e}")
        except Exception as e:  # pragma: no cover
            failures += 1; print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failures}/{len(fns)} passed")
    sys.exit(1 if failures else 0)
