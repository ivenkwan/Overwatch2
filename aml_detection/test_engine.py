"""Tests for aml_detection.engine (plan U3 / U6.4). No DB — uses a fake conn.

Verifies: capability gating (Cross-Rail skipped on tap_and_go), full
evaluation on aml_network, per-rule failure isolation (rollback + continue),
alert sinking through both AlertSink column sets, and the summary return.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aml_detection.alerts import AlertSink  # noqa: E402
from aml_detection.engine import detect  # noqa: E402
from aml_detection.profiles import AML_NETWORK, TAP_AND_GO  # noqa: E402


AML_COLS = {
    "alert_id", "alert_type", "scenario_code", "scenario_category", "rail",
    "ml_typology", "severity", "trigger_entity", "related_transactions",
    "rule_version", "status", "created_at", "resolved_at",
}
TG_COLS = {
    "alert_id", "scenario_code", "scenario_category", "rail", "severity",
    "trigger_entity", "related_transactions", "rule_version", "status", "created_at", "resolved_at",
}


class FakeCur:
    def __init__(self, hits=None, fail_on=()):
        self.hits = hits or []          # returned by fetchall() for every query
        self.fail_on = fail_on          # substrings that make execute() raise
        self.executed = []
        self.rolled_back = 0

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        for sub in self.fail_on:
            if sub in sql:
                raise RuntimeError(f"simulated failure matching {sub!r}")

    def fetchall(self):
        # A hit row is returned for EVERY label-variant statement (the fake
        # cannot know which variant a node belongs to); the assertions below
        # therefore multiply by the per-profile statement count.
        return list(self.hits)

    def close(self):
        pass


class FakeConn:
    def __init__(self, cur):
        self._cur = cur
        self.commits = 0

    def cursor(self):
        return self._cur

    def commit(self):
        self.commits += 1

    def rollback(self):
        self._cur.rolled_back += 1


def _sink_with(columns):
    """A sink class that injects a fixed column set (no information_schema)."""
    class _S(AlertSink):
        def __init__(self, profile, cur):
            super().__init__(profile, cur, columns=columns)
    return _S


# ---- capability gating -----------------------------------------------------

def test_tap_and_go_skips_cross_rail_and_drift():
    cur = FakeCur(hits=[("E1", ["h1"])])
    summary = detect(TAP_AND_GO, FakeConn(cur), sink_class=_sink_with(TG_COLS))
    assert summary["skipped"] == 2, summary          # Cross-Rail + Auth Drift
    assert summary["evaluated"] == 6                  # the other 6 scenarios
    # 6 evaluated scenarios x 6 label-variant statements = 36 sink calls
    assert summary["fired"] == 36
    assert summary["errors"] == []


def test_aml_network_evaluates_all():
    cur = FakeCur(hits=[("E1", ["h1"])])
    summary = detect(AML_NETWORK, FakeConn(cur), sink_class=_sink_with(AML_COLS))
    assert summary["skipped"] == 0
    assert summary["evaluated"] == 8
    # 8 evaluated scenarios x 2 label-variant statements = 16 sink calls
    assert summary["fired"] == 16
    assert summary["errors"] == []


# ---- per-rule failure isolation --------------------------------------------

def test_one_rule_failure_does_not_halt_the_batch():
    # "tx_count" appears only in the structuring query => that rule fails.
    cur = FakeCur(hits=[("E1", ["h1"])], fail_on=("tx_count",))
    summary = detect(TAP_AND_GO, FakeConn(cur), sink_class=_sink_with(TG_COLS))
    assert summary["errors"] == ["SCN_STRUCT_01"], summary
    assert summary["evaluated"] == 6                  # structuring was attempted (then failed)
    assert cur.rolled_back >= 1                       # the failed rule rolled back
    # The other 5 evaluated rules still fired and persisted (6 variants each).
    assert summary["fired"] == 5 * 6


def test_failed_rule_does_not_drop_prior_alerts():
    # Commit-per-rule: a later rollback only undoes the failing rule's own work.
    cur = FakeCur(hits=[("E1", ["h1"])], fail_on=("tx_count",))
    conn = FakeConn(cur)
    detect(AML_NETWORK, conn, sink_class=_sink_with(AML_COLS))
    # 7 successful rules committed + 1 failed rule rolled back.
    assert conn.commits == 7


# ---- alert sinking ---------------------------------------------------------

def test_alerts_sunk_to_each_profile_table():
    cur = FakeCur(hits=[("ACC_X", ["h1", "h2"])])
    detect(AML_NETWORK, FakeConn(cur), sink_class=_sink_with(AML_COLS))
    inserts = [(s, p) for s, p in cur.executed if s.startswith("INSERT")]
    assert inserts, "expected alert inserts"
    assert all("ag_catalog.alerts" in s for s, _ in inserts)
    # Every variant statement produced an insert (8 scenarios x 2 variants).
    assert len(inserts) == 16


def test_summary_profile_name():
    cur = FakeCur()
    assert detect(TAP_AND_GO, FakeConn(cur), sink_class=_sink_with(TG_COLS))["profile"] == "tap_and_go"


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
