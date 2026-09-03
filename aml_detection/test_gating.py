"""Tests for aml_detection.gating (plan U2.3 / U6). No DB."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aml_detection.contract import Capability  # noqa: E402
from aml_detection.gating import is_applicable, missing_capabilities  # noqa: E402
from aml_detection.profiles import AML_NETWORK, TAP_AND_GO  # noqa: E402
from aml_detection.registry import SCENARIOS  # noqa: E402


def _by_code(code):
    return next(s for s in SCENARIOS if s.code == code)


def test_cross_rail_requires_party():
    cr = _by_code("SCN_CROSS_RAIL_LAYER_01")
    assert cr.requires_capabilities == (Capability.PARTY_DIMENSION,)


def test_cross_rail_applicable_to_aml_network():
    cr = _by_code("SCN_CROSS_RAIL_LAYER_01")
    assert missing_capabilities(cr, AML_NETWORK) == []
    assert is_applicable(cr, AML_NETWORK) is True


def test_cross_rail_not_applicable_to_tap_and_go():
    cr = _by_code("SCN_CROSS_RAIL_LAYER_01")
    assert missing_capabilities(cr, TAP_AND_GO) == [Capability.PARTY_DIMENSION]
    assert is_applicable(cr, TAP_AND_GO) is False


def test_non_party_scenarios_apply_to_both():
    for code in ("SCN_CIRCULAR_01", "SCN_STRUCT_01", "SCN_RAPID_MVMT_01"):
        s = _by_code(code)
        assert is_applicable(s, AML_NETWORK) and is_applicable(s, TAP_AND_GO), code


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
