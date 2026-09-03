"""Canonical abstract scenario registry (plan U2.1 / ADR 0001 §7.3).

Merges the 7 aml_network scenarios (aml_platform/etl/scenarios.py) and the
3 Cypher tap_and_go scenarios (etl/detection.py) into ONE abstract registry,
deduplicating the overlaps (Circular, Structuring, Rapid Movement).

Abstract queries use ``<<token>>`` placeholders for profile-specific names
(account/transfer labels, value/ts/ref properties, graph name, party labels).
``aml_detection.render.render()`` substitutes them per profile. Monetary
thresholds are per-currency (resolved by CurrencyResolver); structural params
(hops, ratios, windows) are flat canonical defaults.

SCOPE NOTE — ``TG_SCN_VELOCITY_BURST_01`` (the tap_and_go SQL window rule) is
NOT ported here: it is a SQL rule over ``core.transactions`` with no aml_network
equivalent and doesn't fit the abstract-Cypher model. It remains in
etl/detection.py until the engine grows SQL-rule support (tracked in plan U7).
"""

from __future__ import annotations

from typing import Any, Callable

from .contract import (
    Capability, Category, Currency, Mode, Rail, Scenario, Severity,
)
from .currency import BASE_CURRENCY, CurrencyResolver, DEFAULT as DEFAULT_RESOLVER

#: Flat structural defaults (currency-independent).
DEFAULT_PARAMS: dict[str, Any] = {
    "CIRCULAR_MIN_HOPS": 2,
    "CIRCULAR_MAX_HOPS": 5,
    "STRUCT_MIN_COUNT": 5,
    "PEEL_MIN_HOPS": 3,
    "PEEL_MAX_HOPS": 6,
    "PEEL_DEC_MAX": 0.95,
    "PEEL_DEC_MIN": 0.80,
    "LAYER_MULE_COUNT": 3,
    "LAYER_WINDOW_S": 3600,
    "LAYER_PASS": 0.98,
    "RAPID_MVMT_PASS": 0.90,
    "RAPID_MVMT_WINDOW_S": 86400,
    "RAPID_LAYER_MIN_HOPS": 3,
    "RAPID_LAYER_MAX_HOPS": 6,
    "RAPID_LAYER_GAP_S": 3600,
    "CROSS_RAIL_WINDOW_S": 172800,
    "CROSS_RAIL_STABLECOINS": ("USDT", "USDC", "DAI", "BUSD", "USDS"),
}

#: Per-currency monetary thresholds (resolved per profile by CurrencyResolver).
MONETARY_THRESHOLDS: dict[str, dict[Currency, float]] = {
    "STRUCT_TX_MAX": {Currency.USD: 10000, Currency.HKD: 8000},
    "STRUCT_TOTAL":  {Currency.USD: 10000, Currency.HKD: 80000},
}


def resolve_params(profile, resolver: CurrencyResolver = DEFAULT_RESOLVER) -> dict[str, Any]:
    """Flat params for ``profile`` — structural defaults + currency-resolved thresholds."""
    params: dict[str, Any] = dict(DEFAULT_PARAMS)
    for key, by_ccy in MONETARY_THRESHOLDS.items():
        params[key] = resolver.resolve(by_ccy, profile.base_ccy)
    return params


def _fmt(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return repr(float(value))


# ---------------------------------------------------------------------------
# Abstract query builders. Each takes resolved params and returns an abstract
# Cypher string carrying <<token>> placeholders (substituted by render.py).
# Variable name `pth` avoids clashing with the Cypher path var `p`.
# ---------------------------------------------------------------------------

def _q_circular(p: dict) -> str:
    return (
        "SELECT * FROM cypher('<<graph>>', $$\n"
        f"    MATCH pth = (a:<<account>>)-[t:<<transfer>>*{p['CIRCULAR_MIN_HOPS']}..{p['CIRCULAR_MAX_HOPS']}]->(a:<<account>>)\n"
        "    RETURN a.id AS entity_id, relationships(pth)\n"
        "$$) as (entity_id agtype, tx_hashes agtype);\n"
    )


def _q_structuring(p: dict) -> str:
    return (
        "SELECT * FROM cypher('<<graph>>', $$\n"
        "    MATCH (a:<<account>>)-[t:<<transfer>>]->(:<<account>>)\n"
        f"    WHERE t.<<value>> < {_fmt(p['STRUCT_TX_MAX'])}\n"
        "    WITH a, count(t) AS tx_count, sum(t.<<value>>) AS total, collect(t.<<ref>>) AS tx_hashes\n"
        f"    WHERE tx_count >= {_fmt(p['STRUCT_MIN_COUNT'])} AND total >= {_fmt(p['STRUCT_TOTAL'])}\n"
        "    RETURN a.id AS entity_id, tx_hashes\n"
        "$$) as (entity_id agtype, tx_hashes agtype);\n"
    )


def _q_peeling(p: dict) -> str:
    return (
        "SELECT * FROM cypher('<<graph>>', $$\n"
        f"    MATCH pth = (a:<<account>>)-[t:<<transfer>>*{p['PEEL_MIN_HOPS']}..{p['PEEL_MAX_HOPS']}]->(n:<<account>>)\n"
        "    WHERE ALL(idx IN range(0, size(relationships(pth))-2)\n"
        f"          WHERE (relationships(pth)[idx+1]).<<value>> < (relationships(pth)[idx]).<<value>> * {_fmt(p['PEEL_DEC_MAX'])}\n"
        f"            AND (relationships(pth)[idx+1]).<<value>> > (relationships(pth)[idx]).<<value>> * {_fmt(p['PEEL_DEC_MIN'])})\n"
        "    RETURN a.id AS entity_id, relationships(pth)\n"
        "$$) as (entity_id agtype, tx_hashes agtype);\n"
    )


def _q_high_velocity_layering(p: dict) -> str:
    return (
        "SELECT * FROM cypher('<<graph>>', $$\n"
        "    MATCH (source:<<account>>)-[t1:<<transfer>>]->(mule:<<account>>)-[t2:<<transfer>>]->(sink:<<account>>)\n"
        f"    WHERE t2.<<ts>> - t1.<<ts>> < {_fmt(p['LAYER_WINDOW_S'])}\n"
        f"      AND t2.<<value>> >= t1.<<value>> * {_fmt(p['LAYER_PASS'])}\n"
        "    WITH source, sink, count(mule) AS mule_count, collect(t1.<<ref>>) + collect(t2.<<ref>>) AS tx_hashes\n"
        f"    WHERE mule_count >= {_fmt(p['LAYER_MULE_COUNT'])}\n"
        "    RETURN source.id AS entity_id, tx_hashes\n"
        "$$) as (entity_id agtype, tx_hashes agtype);\n"
    )


def _q_rapid_movement(p: dict) -> str:
    # Both MATCHes precede the WITH so tin/tout are in scope for the window.
    return (
        "SELECT * FROM cypher('<<graph>>', $$\n"
        "    MATCH (src:<<account>>)-[tin:<<transfer>>]->(mule:<<account>>)\n"
        "    MATCH (mule)-[tout:<<transfer>>]->(dst:<<account>>)\n"
        f"    WHERE tout.<<ts>> >= tin.<<ts>> AND tout.<<ts>> - tin.<<ts>> < {_fmt(p['RAPID_MVMT_WINDOW_S'])}\n"
        "    WITH mule, sum(tin.<<value>>) AS in_total, sum(tout.<<value>>) AS out_total,\n"
        "         collect(DISTINCT tin.<<ref>>) + collect(DISTINCT tout.<<ref>>) AS tx_hashes\n"
        f"    WHERE in_total > 0 AND out_total >= in_total * {_fmt(p['RAPID_MVMT_PASS'])}\n"
        "    RETURN mule.id AS entity_id, tx_hashes\n"
        "$$) as (entity_id agtype, tx_hashes agtype);\n"
    )


def _q_rapid_layering(p: dict) -> str:
    return (
        "SELECT * FROM cypher('<<graph>>', $$\n"
        f"    MATCH pth = (a:<<account>>)-[t:<<transfer>>*{p['RAPID_LAYER_MIN_HOPS']}..{p['RAPID_LAYER_MAX_HOPS']}]->(b:<<account>>)\n"
        "    WHERE ALL(idx IN range(0, size(relationships(pth))-2)\n"
        f"          WHERE (relationships(pth)[idx+1]).<<ts>> - (relationships(pth)[idx]).<<ts>> < {_fmt(p['RAPID_LAYER_GAP_S'])})\n"
        "    RETURN a.id AS entity_id, relationships(pth)\n"
        "$$) as (entity_id agtype, tx_hashes agtype);\n"
    )


def _q_cross_rail_layering(p: dict) -> str:
    # Requires the party/UBO dimension; gated by the engine to party-capable
    # profiles (aml_network). <<fiat_node>> expands to the rail-specific fiat
    # account pattern in render.py.
    stablecoins = ", ".join("'" + s + "'" for s in p["CROSS_RAIL_STABLECOINS"])
    return (
        "SELECT * FROM cypher('<<graph>>', $$\n"
        "    MATCH (wallet:<<account>>)<-[tin:<<transfer>>]-(src:<<account>>)\n"
        f"    WHERE tin.asset IN [{stablecoins}]\n"
        "    MATCH (wallet)-[:<<owns>>]->(:<<party>>)-[:<<ubo>>*0..3]->(ubo:<<party>>)\n"
        "    MATCH <<fiat_node>>-[tout:<<transfer>>]->(dst:<<account>>)\n"
        "    MATCH (fiat)-[:<<owns>>]->(:<<party>>)-[:<<ubo>>*0..3]->(ubo)\n"
        f"    WHERE tout.<<ts>> - tin.<<ts>> >= 0 AND tout.<<ts>> - tin.<<ts>> < {_fmt(p['CROSS_RAIL_WINDOW_S'])}\n"
        "    RETURN ubo.id AS entity_id, collect(DISTINCT tin.<<ref>>) + collect(DISTINCT tout.<<ref>>) AS tx_hashes\n"
        "$$) as (entity_id agtype, tx_hashes agtype);\n"
    )


#: The canonical registry (execution order).
SCENARIOS: list[Scenario] = [
    Scenario(
        code="SCN_CIRCULAR_01", name="CIRCULAR_FLOW", category=Category.CIRCULAR_FLOW,
        rail=Rail.BOTH, mode=Mode.BATCH, severity=Severity.CRITICAL,
        description="Funds cycling back to origin within 2-5 hops (round-tripping).",
        build_query=_q_circular,
    ),
    Scenario(
        code="SCN_STRUCT_01", name="STRUCTURING", category=Category.STRUCTURING,
        rail=Rail.BOTH, mode=Mode.BATCH, severity=Severity.HIGH,
        description="Many sub-threshold transfers from one account aggregating past the threshold.",
        build_query=_q_structuring,
    ),
    Scenario(
        code="SCN_PEEL_01", name="PEELING_CHAIN", category=Category.LAYERING,
        rail=Rail.BOTH, mode=Mode.BATCH, severity=Severity.HIGH,
        description="Chain of transfers peeling 5-20% off at each hop to obscure origin.",
        build_query=_q_peeling,
    ),
    Scenario(
        code="SCN_LAYER_FAN_01", name="HIGH_VELOCITY_LAYERING", category=Category.LAYERING,
        rail=Rail.BOTH, mode=Mode.REALTIME, severity=Severity.CRITICAL,
        description="Rapid fan-out through mules then fan-in consolidation.",
        build_query=_q_high_velocity_layering,
    ),
    Scenario(
        code="SCN_RAPID_MVMT_01", name="RAPID_MOVEMENT", category=Category.RAPID_MOVEMENT,
        rail=Rail.BOTH, mode=Mode.REALTIME, severity=Severity.HIGH,
        description="Mule forwarding >= 90% of received funds within a window.",
        build_query=_q_rapid_movement,
    ),
    Scenario(
        code="SCN_LAYER_RAPID_01", name="RAPID_LAYERING", category=Category.LAYERING,
        rail=Rail.BOTH, mode=Mode.REALTIME, severity=Severity.CRITICAL,
        description="3+ hop chain of rapid-succession transfers.",
        build_query=_q_rapid_layering,
    ),
    Scenario(
        code="SCN_CROSS_RAIL_LAYER_01", name="CROSS_RAIL_LAYERING", category=Category.LAYERING,
        rail=Rail.BOTH, mode=Mode.BATCH, severity=Severity.CRITICAL,
        description="Stablecoin inflow -> fiat outflow under the same UBO within 48h.",
        requires_capabilities=(Capability.PARTY_DIMENSION,),
        build_query=_q_cross_rail_layering,
    ),
]

#: Lookup by stable code.
BY_CODE: dict[str, Scenario] = {s.code: s for s in SCENARIOS}
