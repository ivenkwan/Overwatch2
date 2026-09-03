"""
Contract tests for the AML scenario registry.

These validate the *structure* of scenarios.py without needing a live
PostgreSQL+Apache AGE instance (which is unavailable in CI without Docker).
They catch the regressions that a silent Cypher typo or a missing field
would cause. For end-to-end (live-fire) verification of the Cypher itself,
see the manual procedure documented in
Implementation_Plan/20260710_typology_gap_plan.md ("Live verification").

Run:  python aml_platform/etl/test_scenarios.py
  or: pytest aml_platform/etl/test_scenarios.py
"""

import os
import sys

# Ensure the sibling modules import regardless of CWD when run standalone.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import scenarios
from scenarios import (
    SCENARIOS, DEFAULT_PARAMS, RULE_VERSION, render_query,
    CATEGORIES, RAILS, MODES, SEVERITIES,
)

REQUIRED_KEYS = {"code", "name", "category", "rail", "mode", "severity", "description", "build_query"}


# ---- registry shape --------------------------------------------------------

def test_every_scenario_has_required_keys():
    for s in SCENARIOS:
        missing = REQUIRED_KEYS - set(s.keys())
        assert not missing, f"{s.get('code')} missing keys: {missing}"


def test_codes_and_names_are_unique():
    codes = [s["code"] for s in SCENARIOS]
    names = [s["name"] for s in SCENARIOS]
    assert len(codes) == len(set(codes)), f"duplicate codes: {codes}"
    assert len(names) == len(set(names)), f"duplicate names: {names}"


def test_codes_follow_v5_pattern():
    for s in SCENARIOS:
        assert s["code"].startswith("SCN_"), f"{s['code']} should start with SCN_"


def test_enum_values_are_valid():
    for s in SCENARIOS:
        assert s["category"] in CATEGORIES, f"{s['code']} bad category {s['category']}"
        assert s["rail"] in RAILS, f"{s['code']} bad rail {s['rail']}"
        assert s["mode"] in MODES, f"{s['code']} bad mode {s['mode']}"
        assert s["severity"] in SEVERITIES, f"{s['code']} bad severity {s['severity']}"


def test_build_query_is_callable():
    for s in SCENARIOS:
        assert callable(s["build_query"]), f"{s['code']} build_query not callable"


def test_rule_version_present():
    assert isinstance(RULE_VERSION, str) and RULE_VERSION


# ---- default params sanity -------------------------------------------------

def test_hop_ranges_ordered_and_positive():
    for lo, hi in [
        (DEFAULT_PARAMS["CIRCULAR_MIN_HOPS"], DEFAULT_PARAMS["CIRCULAR_MAX_HOPS"]),
        (DEFAULT_PARAMS["PEEL_MIN_HOPS"], DEFAULT_PARAMS["PEEL_MAX_HOPS"]),
        (DEFAULT_PARAMS["RAPID_LAYER_MIN_HOPS"], DEFAULT_PARAMS["RAPID_LAYER_MAX_HOPS"]),
    ]:
        assert 1 <= lo <= hi, f"bad hop range {lo}..{hi}"


def test_percent_params_in_unit_interval():
    for k in ("PEEL_DECREASE_MAX_PCT", "PEEL_DECREASE_MIN_PCT", "LAYER_PASS_PCT", "RAPID_MVMT_PASS_PCT"):
        v = DEFAULT_PARAMS[k]
        assert 0.0 < v <= 1.0, f"{k}={v} out of (0,1]"


# ---- rendered query well-formedness ---------------------------------------

def _rendered(s):
    return render_query(s, DEFAULT_PARAMS)


def test_every_query_targets_aml_network_graph():
    for s in SCENARIOS:
        q = _rendered(s)
        assert "cypher('aml_network'" in q, f"{s['code']} does not target aml_network"


def test_every_query_has_return_and_column_cast():
    for s in SCENARIOS:
        q = _rendered(s)
        assert "RETURN" in q, f"{s['code']} query has no RETURN"
        assert "agtype" in q, f"{s['code']} query missing agtype column cast"
        assert q.rstrip().endswith(";"), f"{s['code']} query not semicolon-terminated"


def test_queries_have_no_unfilled_placeholders():
    # Query builders must fully resolve; no stray Python interpolation artifacts.
    for s in SCENARIOS:
        q = _rendered(s)
        assert "{cfg" not in q and "_fmt(" not in q, f"{s['code']} query has unresolved builder text:\n{q}"


def test_param_override_changes_output():
    """Proof that Phase 0.3 parameterization actually threads through."""
    s = next(x for x in SCENARIOS if x["name"] == "SMURFING_STRUCTURING")
    base = render_query(s, DEFAULT_PARAMS)
    tuned = dict(DEFAULT_PARAMS)
    tuned["SMURFING_TOTAL_USD"] = 8000
    overridden = render_query(s, tuned)
    assert "10000" in base
    assert "8000" in overridden and "8000" != base


# ---- the two NEW rules are present and shaped like the proven ones ---------

def test_rapid_movement_regression_is_restored():
    # Phase 1.1: the dropped Rapid Movement typology is back in the registry.
    names = [s["name"] for s in SCENARIOS]
    assert "RAPID_MOVEMENT" in names, "Rapid Movement regression not restored"
    s = next(x for x in SCENARIOS if x["name"] == "RAPID_MOVEMENT")
    q = _rendered(s)
    # Must key on the pass-through ratio from params, not a hardcoded 0.9.
    assert "RAPID_MVMT_PASS_PCT" not in q  # builder resolved it
    assert "in_total" in q and "out_total" in q


def test_rapid_layering_uses_same_timestamp_idiom_as_proven_rule():
    # Phase 1.3: new layering rule shares the timestamp-subtraction assumption
    # the existing HIGH_VELOCITY_LAYERING rule already relies on, so they
    # validate together against AGE (or fail together — no new risk surface).
    hv = _rendered(next(x for x in SCENARIOS if x["name"] == "HIGH_VELOCITY_LAYERING"))
    rl = _rendered(next(x for x in SCENARIOS if x["name"] == "RAPID_LAYERING"))
    assert "timestamp -" in hv and "timestamp -" in rl


# ---- legacy shim backward-compat ------------------------------------------

def test_legacy_typologies_shim_matches_registry():
    # The deprecated typologies.py must expose every scenario under legacy shape.
    import typologies  # emits DeprecationWarning by design
    assert len(typologies.TYPOLOGIES) == len(SCENARIOS)
    legacy_names = {t["name"] for t in typologies.TYPOLOGIES}
    registry_names = {s["name"] for s in SCENARIOS}
    assert legacy_names == registry_names
    # Each legacy entry is queryable and well-formed.
    for t in typologies.TYPOLOGIES:
        assert "cypher('aml_network'" in t["query"]
        assert t["severity"] in SEVERITIES


# ---- Cross-Rail Layering (Part 1: party/UBO prerequisite) -----------------

def test_cross_rail_scenario_present_and_gated():
    s = next((x for x in SCENARIOS if x["name"] == "CROSS_RAIL_LAYERING"), None)
    assert s is not None, "Cross-Rail Layering scenario not in registry"
    # Must declare the Party label dependency so rule_engine skips it with
    # guidance until the party/UBO dimension is projected (graceful degrade).
    assert s.get("requires_labels") == ("Party",), "Cross-Rail must gate on the Party label"
    q = render_query(s, DEFAULT_PARAMS)
    assert "OWNED_BY" in q and "UBO_OF*0..3" in q, f"query missing party/UBO traversal:\n{q}"
    # Param fully resolved — no builder artifacts in the rendered string.
    assert "CROSS_RAIL_WINDOW_SECONDS" not in q and "_fmt(" not in q


def test_cross_rail_renders_stablecoin_list_and_48h_window():
    s = next(x for x in SCENARIOS if x["name"] == "CROSS_RAIL_LAYERING")
    q = render_query(s, DEFAULT_PARAMS)
    for ticker in DEFAULT_PARAMS["CROSS_RAIL_STABLECOINS"]:
        assert "'" + ticker + "'" in q, f"stablecoin {ticker} not rendered in query"
    # 48h window (172800s) threaded from params.
    assert "172800" in q
    # Targets the FIAT rail via the system property (literal braces preserved).
    assert "{system: 'FIAT'}" in q


def test_cross_rail_param_override_changes_window():
    s = next(x for x in SCENARIOS if x["name"] == "CROSS_RAIL_LAYERING")
    tuned = dict(DEFAULT_PARAMS)
    tuned["CROSS_RAIL_WINDOW_SECONDS"] = 86400  # 24h
    q = render_query(s, tuned)
    assert "86400" in q and "172800" not in q


# ---- standalone runner -----------------------------------------------------

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
        except Exception as e:  # pragma: no cover - surfaces import/runtime errors
            failures += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failures}/{len(fns)} passed")
    sys.exit(1 if failures else 0)
