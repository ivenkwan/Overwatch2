"""
Tests for the two concrete GraphProfiles (plan U1.4 / U6.5). No DB, no deps.

Validates that each profile correctly captures its graph's contract and that
the two profiles diverge exactly where the abstraction must span (currency,
labels, ref/rail properties, party capability). A regression here would
silently break the renderer (U2.2).

Run:  python aml_detection/profiles/test_profiles.py
  or: pytest aml_detection/profiles/test_profiles.py
"""

import os
import sys

# repo root (three levels up from profiles/test_profiles.py)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from aml_detection.contract import Currency  # noqa: E402
from aml_detection.profiles import AML_NETWORK, TAP_AND_GO  # noqa: E402


def test_aml_network_contract():
    p = AML_NETWORK
    assert p.name == "aml_network"
    assert p.graph_name == "aml_network"
    assert "Entity" in p.account_label and "SuperNode" in p.account_label
    assert p.transfer_label == "Transfer"
    assert p.prop_value == "amount_usd"
    assert p.base_ccy is Currency.USD
    assert p.prop_ts == "ts" and p.ts_is_epoch is True
    assert p.prop_ref == "ref_id"
    assert p.prop_rail == "system" and p.rail_constant is None
    assert p.alert_table == "ag_catalog.alerts"


def test_aml_network_has_party_dimension():
    p = AML_NETWORK
    assert p.has_party is True
    pd = p.capabilities.party_dimension
    assert pd is not None
    assert (pd.party_label, pd.owns_label, pd.ubo_label) == ("Party", "OWNED_BY", "UBO_OF")


def test_tap_and_go_contract():
    p = TAP_AND_GO
    assert p.name == "tap_and_go"
    assert p.graph_name == "tap_and_go_network"
    for label in ("Customer", "Counterparty", "Merchant"):
        assert label in p.account_label
    assert p.transfer_label == "PAID|TRANSFERRED"
    assert p.prop_value == "amount"
    assert p.base_ccy is Currency.HKD
    assert p.prop_ts == "ts" and p.ts_is_epoch is True
    assert p.prop_ref == "txn_hash"
    assert p.prop_rail is None and p.rail_constant == "FIAT"
    assert p.alert_table == "core.alerts"


def test_tap_and_go_has_no_party_dimension():
    assert TAP_AND_GO.has_party is False


def test_profiles_diverge_where_the_abstraction_spans():
    # The whole point of unification: these MUST differ.
    assert AML_NETWORK.base_ccy is not TAP_AND_GO.base_ccy          # USD vs HKD
    assert AML_NETWORK.prop_value != TAP_AND_GO.prop_value          # amount_usd vs amount
    assert AML_NETWORK.prop_ref != TAP_AND_GO.prop_ref              # ref_id vs txn_hash
    assert AML_NETWORK.graph_name != TAP_AND_GO.graph_name
    assert AML_NETWORK.has_party != TAP_AND_GO.has_party


def test_both_profiles_use_epoch_ts():
    # Unified renderer does epoch arithmetic — both must be epoch.
    assert AML_NETWORK.ts_is_epoch and TAP_AND_GO.ts_is_epoch


def test_both_profiles_specify_exactly_one_rail_source():
    for p in (AML_NETWORK, TAP_AND_GO):
        assert (p.prop_rail is None) != (p.rail_constant is None)  # XOR


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
