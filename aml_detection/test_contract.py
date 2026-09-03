"""
Contract tests for aml_detection.contract (plan U1.2 / U6.1).

Validates the abstract type invariants — the bedrock every later phase
(registry, renderer, engine, profiles) relies on. No DB, no dagster.

Run:  python aml_detection/test_contract.py
  or: pytest aml_detection/test_contract.py
"""

import os
import sys

# Make `aml_detection` importable when run standalone (script dir is aml_detection/).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aml_detection.contract import (  # noqa: E402
    Capabilities, Capability, Category, Currency, GraphProfile,
    Mode, PartyDimension, Rail, Scenario, Severity,
)


# ---- enums -----------------------------------------------------------------

def test_enums_have_expected_members():
    assert {c.value for c in Category} >= {
        "CIRCULAR_FLOW", "STRUCTURING", "LAYERING", "RAPID_MOVEMENT", "VELOCITY",
    }
    assert {r.value for r in Rail} == {"FIAT", "STABLECOIN", "BOTH"}
    assert {m.value for m in Mode} == {"REALTIME", "BATCH"}
    assert {s.value for s in Severity} == {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert {c.value for c in Currency} == {"HKD", "USD"}


def test_currency_base():
    assert Currency.HKD.is_base is True
    assert Currency.USD.is_base is False


# ---- Scenario ---------------------------------------------------------------

def _scenario(**over):
    base = dict(
        code="SCN_TEST_01", name="TEST", category=Category.CIRCULAR_FLOW,
        rail=Rail.BOTH, mode=Mode.BATCH, severity=Severity.HIGH, description="d",
    )
    base.update(over)
    return Scenario(**base)


def test_scenario_defaults():
    s = _scenario()
    assert s.requires_capabilities == ()
    assert s.build_query is None
    assert s.needs(Capability.PARTY_DIMENSION) is False


def test_scenario_requires_capabilities():
    s = _scenario(requires_capabilities=(Capability.PARTY_DIMENSION,))
    assert s.needs(Capability.PARTY_DIMENSION) is True


def test_scenario_build_query_is_callable():
    s = _scenario(build_query=lambda p: f"/* {p['x']} */")
    assert callable(s.build_query)
    assert s.build_query({"x": 1}) == "/* 1 */"


def test_scenario_rejects_bad_code():
    for bad in ("", "TG_FOO", "circular", "SCN"):
        try:
            _scenario(code=bad)
        except ValueError:
            continue
        raise AssertionError(f"code {bad!r} should have been rejected")


def test_scenario_rejects_non_enum_fields():
    # Plain strings must not silently stand in for enums.
    try:
        _scenario(category="CIRCULAR_FLOW")  # type: ignore[arg-type]
    except ValueError:
        return
    raise AssertionError("plain-string category should be rejected")


# ---- GraphProfile -----------------------------------------------------------

def _profile(**over):
    base = dict(
        name="p", graph_name="g", account_label="Entity", transfer_label="Transfer",
        prop_value="amount_usd", base_ccy=Currency.USD, prop_ts="ts",
        prop_rail="system", rail_constant=None,
    )
    base.update(over)
    return GraphProfile(**base)


def test_profile_rail_via_property():
    p = _profile(prop_rail="system", rail_constant=None)
    assert p.has_party is False


def test_profile_rail_via_constant():
    p = _profile(prop_rail=None, rail_constant="FIAT")
    assert p.prop_rail is None and p.rail_constant == "FIAT"


def test_profile_rejects_both_rail_sources():
    try:
        _profile(prop_rail="system", rail_constant="FIAT")
    except ValueError:
        return
    raise AssertionError("setting both prop_rail and rail_constant should be rejected")


def test_profile_rejects_neither_rail_source():
    try:
        _profile(prop_rail=None, rail_constant=None)
    except ValueError:
        return
    raise AssertionError("setting neither prop_rail nor rail_constant should be rejected")


def test_profile_rejects_non_epoch_ts():
    try:
        _profile(ts_is_epoch=False)
    except ValueError:
        return
    raise AssertionError("non-epoch ts should be rejected (unified renderer needs epoch)")


def test_profile_rejects_non_enum_ccy():
    try:
        _profile(base_ccy="USD")  # type: ignore[arg-type]
    except ValueError:
        return
    raise AssertionError("plain-string base_ccy should be rejected")


def test_profile_has_party_via_capabilities():
    caps = Capabilities(party_dimension=PartyDimension("Party", "OWNED_BY", "UBO_OF"))
    p = _profile(capabilities=caps)
    assert p.has_party is True
    assert p.capabilities.supports(Capability.PARTY_DIMENSION) is True


# ---- frozen -----------------------------------------------------------------

def test_types_are_frozen():
    s = _scenario()
    try:
        s.code = "SCN_OTHER_01"  # type: ignore[misc]
    except AttributeError:
        return
    raise AssertionError("Scenario should be frozen")


# ---- standalone runner ------------------------------------------------------

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
