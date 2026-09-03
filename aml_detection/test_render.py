"""
Render snapshot + property tests (plan U6.3 — the critical de-risking suite).

Locks the concrete Cypher each profile gets for every scenario. This is where
the AGE label-union assumption (``Customer|Counterparty|Merchant``,
``PAID|TRANSFERRED``) is proven at the string level: if a profile's labels or
properties drift, or a token is left unresolved, a snapshot fails.

NOTE: these prove the RENDERED STRING is correct and well-formed. Whether AGE
actually accepts label-unions in variable-length relationships
(``[PAID|TRANSFERRED*2..5]``) still needs a live AGE check — see ADR 0001
risks and plan U7.2 verification. If AGE rejects multi-label variable paths,
the fallback is per-label UNION queries (renderer change only).

Run:  python aml_detection/test_render.py
  or: pytest aml_detection/test_render.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aml_detection.profiles import AML_NETWORK, TAP_AND_GO  # noqa: E402
from aml_detection.registry import SCENARIOS, resolve_params  # noqa: E402
from aml_detection.render import render  # noqa: E402


def _render(scenario, profile):
    return render(profile, scenario.build_query(resolve_params(profile)))


# ---------------------------------------------------------------------------
# Universal: every non-gated scenario renders for both profiles, cleanly.
# ---------------------------------------------------------------------------

def test_all_non_gated_scenarios_render_without_leftover_tokens():
    for s in SCENARIOS:
        for profile in (AML_NETWORK, TAP_AND_GO):
            if s.needs(__import__("aml_detection.contract", fromlist=["Capability"]).Capability.PARTY_DIMENSION) \
                    and not profile.has_party:
                continue  # cross-rail is gated for tap_and_go
            q = _render(s, profile)
            assert "<<" not in q and ">>" not in q, f"{s.code}@{profile.name}: leftover token\n{q}"
            assert "RETURN" in q and "agtype" in q, f"{s.code}@{profile.name}: malformed"
            assert f"cypher('{profile.graph_name}'" in q, f"{s.code}@{profile.name}: wrong graph"


# ---------------------------------------------------------------------------
# Label-union proof (the core de-risk): tap_and_go gets multi-label unions,
# aml_network gets its labels.
# ---------------------------------------------------------------------------

def test_tap_and_go_label_unions_present():
    q = _render(SCENARIOS[0], TAP_AND_GO)  # circular
    assert "Customer|Counterparty|Merchant" in q
    assert "PAID|TRANSFERRED" in q


def test_variable_length_union_label_rendered():
    # The riskiest construct: a multi-label variable-length relationship.
    q = _render(SCENARIOS[0], TAP_AND_GO)
    assert "[t:PAID|TRANSFERRED*2..5]" in q, f"union var-length not rendered:\n{q}"


def test_aml_network_labels_present():
    q = _render(SCENARIOS[0], AML_NETWORK)
    assert "Entity|SuperNode" in q and "[t:Transfer*2..5]" in q


# ---------------------------------------------------------------------------
# Property + currency substitution.
# ---------------------------------------------------------------------------

def test_property_substitution_per_profile():
    struct = next(s for s in SCENARIOS if s.code == "SCN_STRUCT_01")
    assert "t.amount_usd" in _render(struct, AML_NETWORK)
    assert "t.amount" in _render(struct, TAP_AND_GO)
    assert "t.ref_id" in _render(struct, AML_NETWORK)
    assert "t.txn_hash" in _render(struct, TAP_AND_GO)


def test_structuring_thresholds_are_currency_resolved():
    struct = next(s for s in SCENARIOS if s.code == "SCN_STRUCT_01")
    usd = _render(struct, AML_NETWORK)
    hkd = _render(struct, TAP_AND_GO)
    # USD policy: sub-10000; HKD policy: sub-8000, total 80000.
    assert "t.amount_usd < 10000" in usd and "total >= 10000" in usd
    assert "t.amount < 8000" in hkd and "total >= 80000" in hkd


def test_all_time_windows_use_epoch_ts():
    # Unification benefit: every time-window rule uses epoch ts (not ISO).
    for s in SCENARIOS:
        q_aml = _render(s, AML_NETWORK)
        if ".ts" in q_aml or "timestamp" in q_aml:
            assert "timestamp" not in q_aml, f"{s.code}: must use epoch ts, not ISO timestamp"


# ---------------------------------------------------------------------------
# Cross-rail gating + full golden for aml_network.
# ---------------------------------------------------------------------------

def test_cross_rail_renders_for_aml_network():
    from aml_detection.contract import Capability
    cr = next(s for s in SCENARIOS if s.code == "SCN_CROSS_RAIL_LAYER_01")
    assert cr.needs(Capability.PARTY_DIMENSION)
    q = _render(cr, AML_NETWORK)
    assert ":OWNED_BY" in q and ":UBO_OF*0..3" in q and ":Party" in q
    # <<fiat_node>> expanded to the rail-specific fiat account pattern.
    assert "(fiat:Entity|SuperNode {system: 'FIAT'})" in q
    assert "'USDT'" in q and "'USDC'" in q


def test_cross_rail_refuses_tap_and_go():
    from aml_detection.contract import Capability
    cr = next(s for s in SCENARIOS if s.code == "SCN_CROSS_RAIL_LAYER_01")
    try:
        render(TAP_AND_GO, cr.build_query(resolve_params(TAP_AND_GO)))
    except ValueError:
        return
    raise AssertionError("cross-rail must refuse profiles without the party dimension")


# ---------------------------------------------------------------------------
# Golden snapshots — exact locks on the deduped (merged) scenarios, both
# profiles. Any change to labels/props/structure surfaces here.
# ---------------------------------------------------------------------------

GOLDEN_CIRCULAR_AML = (
    "SELECT * FROM cypher('aml_network', $$\n"
    "    MATCH pth = (a:Entity|SuperNode)-[t:Transfer*2..5]->(a:Entity|SuperNode)\n"
    "    RETURN a.id AS entity_id, relationships(pth)\n"
    "$$) as (entity_id agtype, tx_hashes agtype);\n"
)

GOLDEN_CIRCULAR_TG = (
    "SELECT * FROM cypher('tap_and_go_network', $$\n"
    "    MATCH pth = (a:Customer|Counterparty|Merchant)-[t:PAID|TRANSFERRED*2..5]->(a:Customer|Counterparty|Merchant)\n"
    "    RETURN a.id AS entity_id, relationships(pth)\n"
    "$$) as (entity_id agtype, tx_hashes agtype);\n"
)

GOLDEN_STRUCT_AML = (
    "SELECT * FROM cypher('aml_network', $$\n"
    "    MATCH (a:Entity|SuperNode)-[t:Transfer]->(:Entity|SuperNode)\n"
    "    WHERE t.amount_usd < 10000\n"
    "    WITH a, count(t) AS tx_count, sum(t.amount_usd) AS total, collect(t.ref_id) AS tx_hashes\n"
    "    WHERE tx_count >= 5 AND total >= 10000\n"
    "    RETURN a.id AS entity_id, tx_hashes\n"
    "$$) as (entity_id agtype, tx_hashes agtype);\n"
)

GOLDEN_STRUCT_TG = (
    "SELECT * FROM cypher('tap_and_go_network', $$\n"
    "    MATCH (a:Customer|Counterparty|Merchant)-[t:PAID|TRANSFERRED]->(:Customer|Counterparty|Merchant)\n"
    "    WHERE t.amount < 8000\n"
    "    WITH a, count(t) AS tx_count, sum(t.amount) AS total, collect(t.txn_hash) AS tx_hashes\n"
    "    WHERE tx_count >= 5 AND total >= 80000\n"
    "    RETURN a.id AS entity_id, tx_hashes\n"
    "$$) as (entity_id agtype, tx_hashes agtype);\n"
)

GOLDEN_RAPID_MVMT_AML = (
    "SELECT * FROM cypher('aml_network', $$\n"
    "    MATCH (src:Entity|SuperNode)-[tin:Transfer]->(mule:Entity|SuperNode)\n"
    "    MATCH (mule)-[tout:Transfer]->(dst:Entity|SuperNode)\n"
    "    WHERE tout.ts >= tin.ts AND tout.ts - tin.ts < 86400\n"
    "    WITH mule, sum(tin.amount_usd) AS in_total, sum(tout.amount_usd) AS out_total,\n"
    "         collect(DISTINCT tin.ref_id) + collect(DISTINCT tout.ref_id) AS tx_hashes\n"
    "    WHERE in_total > 0 AND out_total >= in_total * 0.9\n"
    "    RETURN mule.id AS entity_id, tx_hashes\n"
    "$$) as (entity_id agtype, tx_hashes agtype);\n"
)


def test_golden_circular():
    s = next(x for x in SCENARIOS if x.code == "SCN_CIRCULAR_01")
    assert _render(s, AML_NETWORK) == GOLDEN_CIRCULAR_AML
    assert _render(s, TAP_AND_GO) == GOLDEN_CIRCULAR_TG


def test_golden_structuring():
    s = next(x for x in SCENARIOS if x.code == "SCN_STRUCT_01")
    assert _render(s, AML_NETWORK) == GOLDEN_STRUCT_AML
    assert _render(s, TAP_AND_GO) == GOLDEN_STRUCT_TG


def test_golden_rapid_movement():
    s = next(x for x in SCENARIOS if x.code == "SCN_RAPID_MVMT_01")
    assert _render(s, AML_NETWORK) == GOLDEN_RAPID_MVMT_AML


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
