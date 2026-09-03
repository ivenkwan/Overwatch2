"""
Contract tests for the tap_and_go T+1 detection module (etl/detection.py).

Validates scenario structure and query contents without a live
Postgres+Apache AGE instance or Dagster runtime. Stubs dagster/psycopg2 only
if they are not already importable (so the same file works in CI once those
deps are installed).

Run:  python etl/test_detection.py
  or: pytest etl/test_detection.py
"""

import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _ensure_lightweight_deps():
    """Stub dagster/psycopg2 when absent so detection.py can be imported."""
    if "dagster" not in sys.modules:
        try:
            import dagster  # noqa: F401
        except ImportError:
            def _dec(*a, **k):
                def deco(fn):
                    return fn
                return deco
            m = types.ModuleType("dagster")
            for name in ("op", "job", "schedule", "asset", "Definitions", "load_assets_from_modules"):
                setattr(m, name, _dec)
            m.DefaultScheduleStatus = types.SimpleNamespace(RUNNING="running")
            m.RunRequest = lambda **k: k
            m.Config = object
            m.Failure = Exception
            m.Out = lambda *a, **k: None
            sys.modules["dagster"] = m
    sys.modules.setdefault("psycopg2", types.ModuleType("psycopg2"))


_ensure_lightweight_deps()
import detection  # noqa: E402

REQUIRED_KEYS = {"code", "name", "category", "rail", "severity", "kind", "description", "query"}
VALID_KINDS = {"cypher", "sql"}


def test_every_scenario_has_required_keys():
    for s in detection.SCENARIOS:
        missing = REQUIRED_KEYS - set(s.keys())
        assert not missing, f"{s.get('code')} missing keys: {missing}"


def test_codes_unique_and_tg_prefixed():
    codes = [s["code"] for s in detection.SCENARIOS]
    assert len(codes) == len(set(codes)), f"duplicate codes: {codes}"
    for c in codes:
        assert c.startswith("TG_SCN_"), f"{c} should start with TG_SCN_"


def test_kinds_valid():
    for s in detection.SCENARIOS:
        assert s["kind"] in VALID_KINDS, f"{s['code']} bad kind {s['kind']}"


def test_cypher_scenarios_target_tap_and_go():
    for s in detection.SCENARIOS:
        if s["kind"] == "cypher":
            assert "cypher('tap_and_go_network'" in s["query"], f"{s['code']} not on tap_and_go_network"
            assert "RETURN" in s["query"] and "agtype" in s["query"]


def test_rapid_movement_uses_projected_ts():
    # The timestamp-gap closure: rapid-movement relies on the ts epoch now
    # projected onto edges by graph_projection.py / daily_pipeline.py.
    s = next(x for x in detection.SCENARIOS if x["name"] == "RAPID_MOVEMENT")
    q = s["query"]
    assert "tout.ts - tin.ts" in q, "rapid-movement must window on projected ts"
    assert "86400" in q, "rapid-movement must use the 24h window"


def test_velocity_is_sql_window_over_transactions():
    # Velocity uses a SQL window (cleaner than Cypher for time-bucket counts).
    s = next(x for x in detection.SCENARIOS if x["name"] == "VELOCITY_BURST")
    assert s["kind"] == "sql"
    q = s["query"]
    assert "OVER w" in q and "INTERVAL '1 hour'" in q, "velocity must use a 1h window function"
    assert "core.transactions" in q
    assert "array_agg(DISTINCT txn_hash)" in q, "velocity must return tx_hashes list"


def test_sql_scenarios_return_two_columns():
    # The op fetches (entity_id, tx_hashes) from every scenario, so SQL rules
    # must alias exactly those two columns.
    for s in detection.SCENARIOS:
        if s["kind"] == "sql":
            assert "AS entity_id" in s["query"] and "AS tx_hashes" in s["query"], (
                f"{s['code']} SQL query must alias entity_id and tx_hashes")


def test_rule_version_bumped():
    assert detection.RULE_VERSION and detection.RULE_VERSION.endswith("detection-2"), (
        "RULE_VERSION should reflect the velocity/rapid-movement addition")


def test_job_and_schedule_wired():
    # Detection must be reachable as a Dagster job + schedule (registered in repo.py).
    assert callable(getattr(detection, "run_typology_detection", None))
    assert getattr(detection, "t1_detection_job", None) is not None
    assert getattr(detection, "t1_detection_schedule", None) is not None
    # Cron string lives in the module source (the dagster stub can't introspect
    # the ScheduleDefinition object, so assert on source instead).
    src = open(os.path.join(os.path.dirname(__file__), "detection.py"), encoding="utf-8").read()
    assert '"30 0 * * *"' in src, "t1_detection_schedule must use the 00:30 T+1 cron"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {fn.__name__}: {e}")
        except Exception as e:  # pragma: no cover
            failures += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failures}/{len(fns)} passed")
    sys.exit(1 if failures else 0)
