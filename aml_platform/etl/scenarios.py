"""
Scenario registry for the AML Cypher rule engine.

Each entry is a v5-style detection scenario (see
docs/new_v5_spec/Project-Overwatch-Full-Requirements-Specification.md §15).
Thresholds live in DEFAULT_PARAMS so tuning does not require code edits;
rule_engine.render_query(scenario, params) injects them into the Cypher
string at load time.

GRAPH CONTRACT (see etl/graph_loader.py + init-scripts/03-graph-schema.sql):
  Vertex labels : Entity, SuperNode          properties: {id, system}
  Edge label    : Transfer                   properties: {amount_usd, timestamp, ref_id[, asset]}
  ``system`` is 'FIAT' for fiat rails, or the chain name (e.g. 'ETHEREUM')
  for crypto. There is currently NO beneficial-owner / party dimension on
  nodes, so cross-rail-same-UBO scenarios are not yet expressible.

VERIFICATION CAVEAT: Cypher correctness against a live Apache AGE instance
could not be executed in this environment (no Docker/Postgres+AGE). The
four migrated rules (CIRCULAR, SMURFING, PEELING, HIGH_VELOCITY_LAYERING)
are preserved VERBATIM from the prior build and were assumed working. The
two new rules (RAPID_MOVEMENT, RAPID_LAYERING) follow the same Cypher
patterns (incl. the timestamp-subtraction idiom already used by the
HIGH_VELOCITY_LAYERING rule) but MUST be live-verified before production
use — see test_scenarios.py and the manual verification procedure in
Implementation_Plan/20260710_typology_gap_plan.md.

The 4 migrated rules keep their original ``name`` values so existing
alerts ('CIRCULAR_TRANSACTION', 'SMURFING_STRUCTURING', 'PEELING_CHAIN',
'HIGH_VELOCITY_LAYERING') remain backward-compatible; the new ``code``
field is the stable v5 scenario identifier.
"""

# Bumped whenever the registry shape or a query changes. Stored on every alert.
RULE_VERSION = "2026.07-scenario-registry"

# v5 converged-model enumerations (subset relevant to implemented scenarios).
CATEGORIES = (
    "CIRCULAR_FLOW", "STRUCTURING", "LAYERING", "RAPID_MOVEMENT",
    "PLACEMENT", "TRAVEL_RULE_BREACH", "BLOCKCHAIN_RISK",
    "UNHOSTED_WALLET", "VELOCITY", "PEP_MONITORING",
)
RAILS = ("FIAT", "STABLECOIN", "BOTH")
MODES = ("REALTIME", "BATCH")
SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")

# Tunable thresholds. Overridable from the environment in rule_engine.py so
# operators can tune without code edits (e.g. via a future scenario_config table).
DEFAULT_PARAMS = {
    # Circular flow (2-5 hop cycles back to origin)
    "CIRCULAR_MIN_HOPS": 2,
    "CIRCULAR_MAX_HOPS": 5,
    # Structuring / smurfing
    "SMURFING_TX_MAX_USD": 10000,   # each individual transfer below this
    "SMURFING_TX_COUNT": 3,         # ...occurring at least this many times
    "SMURFING_TOTAL_USD": 10000,    # ...summing to at least this
    # Peeling chain (gradual 5-20% peels across a chain)
    "PEEL_MIN_HOPS": 3,
    "PEEL_MAX_HOPS": 6,
    "PEEL_DECREASE_MAX_PCT": 0.95,  # next hop amount <= prev * 0.95
    "PEEL_DECREASE_MIN_PCT": 0.80,  # next hop amount >  prev * 0.80
    # High-velocity layering (fan-out -> fan-in through mules)
    "LAYER_MULE_COUNT": 3,
    "LAYER_WINDOW_SECONDS": 3600,   # 1h
    "LAYER_PASS_PCT": 0.98,
    # Rapid movement (mule forwards most incoming funds)
    "RAPID_MVMT_PASS_PCT": 0.90,    # forwards >= 90% of incoming
    # Rapid layering (3+ hop rapid-succession chain)
    "RAPID_LAYER_MIN_HOPS": 3,
    "RAPID_LAYER_MAX_HOPS": 6,
    "RAPID_LAYER_GAP_SECONDS": 3600,  # <= 1h between consecutive hops
    # Cross-rail layering (stablecoin inflow -> fiat outflow, same UBO, within window)
    "CROSS_RAIL_WINDOW_SECONDS": 172800,  # 48h (v5 spec SCN_CROSS_RAIL_LAYER_01)
    "CROSS_RAIL_STABLECOINS": ("USDT", "USDC", "DAI", "BUSD", "USDS"),
}


def _fmt(value):
    """Render a parameter value for Cypher: ints bare, floats without trailing noise."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    # float: strip insignificant trailing zeros but keep e.g. 0.95 as 0.95
    return repr(float(value))


# ---------------------------------------------------------------------------
# Cypher query builders. Each takes the resolved params dict and returns the
# full ``SELECT * FROM cypher('aml_network', $$ ... $$) as (...)`` statement.
# The four _migrated_* builders reproduce the original typologies.py queries
# exactly, only substituting the (formerly hardcoded) thresholds from params.
# ---------------------------------------------------------------------------

def _q_circular(cfg):
    return (
        "SELECT * FROM cypher('aml_network', $$\n"
        "    MATCH p = (a:Entity)-[t:Transfer*"
        + _fmt(cfg["CIRCULAR_MIN_HOPS"]) + ".." + _fmt(cfg["CIRCULAR_MAX_HOPS"])
        + "]->(a:Entity)\n"
        "    RETURN a.id AS entity_id, relationships(p)\n"
        "$$) as (entity_id agtype, tx_hashes agtype);\n"
    )


def _q_smurfing(cfg):
    return (
        "SELECT * FROM cypher('aml_network', $$\n"
        "    MATCH (a:Entity)-[t:Transfer]->(b:Entity)\n"
        "    WHERE t.amount_usd < " + _fmt(cfg["SMURFING_TX_MAX_USD"]) + " \n"
        "    WITH a, b, count(t) as tx_count, sum(t.amount_usd) as total_usd, collect(t.ref_id) as tx_hashes\n"
        "    WHERE tx_count >= " + _fmt(cfg["SMURFING_TX_COUNT"])
        + " AND total_usd >= " + _fmt(cfg["SMURFING_TOTAL_USD"]) + "\n"
        "    RETURN a.id AS entity_id, tx_hashes\n"
        "$$) as (entity_id agtype, tx_hashes agtype);\n"
    )


def _q_peeling(cfg):
    return (
        "SELECT * FROM cypher('aml_network', $$\n"
        "    MATCH p = (a:Entity)-[t:Transfer*"
        + _fmt(cfg["PEEL_MIN_HOPS"]) + ".." + _fmt(cfg["PEEL_MAX_HOPS"]) + "]->(n:Entity)\n"
        "    WHERE ALL(idx IN range(0, size(relationships(p))-2) \n"
        "          WHERE (relationships(p)[idx+1]).amount_usd < (relationships(p)[idx]).amount_usd * "
        + _fmt(cfg["PEEL_DECREASE_MAX_PCT"]) + "\n"
        "          AND (relationships(p)[idx+1]).amount_usd > (relationships(p)[idx]).amount_usd * "
        + _fmt(cfg["PEEL_DECREASE_MIN_PCT"]) + ")\n"
        "    RETURN a.id AS entity_id, relationships(p)\n"
        "$$) as (entity_id agtype, tx_hashes agtype);\n"
    )


def _q_high_velocity_layering(cfg):
    return (
        "SELECT * FROM cypher('aml_network', $$\n"
        "    MATCH (source:Entity)-[t1:Transfer]->(mule:Entity)-[t2:Transfer]->(sink:Entity)\n"
        "    WHERE t2.timestamp - t1.timestamp < " + _fmt(cfg["LAYER_WINDOW_SECONDS"]) + "\n"
        "      AND t2.amount_usd >= (t1.amount_usd * " + _fmt(cfg["LAYER_PASS_PCT"]) + ")\n"
        "    WITH source, sink, count(mule) as mule_count, collect(t1.ref_id) + collect(t2.ref_id) as tx_hashes\n"
        "    WHERE mule_count >= " + _fmt(cfg["LAYER_MULE_COUNT"]) + "\n"
        "    RETURN source.id AS entity_id, tx_hashes\n"
        "$$) as (entity_id agtype, tx_hashes agtype);\n"
    )


def _q_rapid_movement(cfg):
    # Money mule forwarding >= RAPID_MVMT_PASS_PCT of incoming funds.
    # Pure amount-ratio (no timestamp arithmetic) so it cannot regress on
    # AGE's string-typed timestamp handling. A strict receive->forward time
    # window can be layered on once timestamp casting is validated in AGE.
    return (
        "SELECT * FROM cypher('aml_network', $$\n"
        "    MATCH (src:Entity)-[tin:Transfer]->(mule:Entity)\n"
        "    WITH mule, sum(tin.amount_usd) AS in_total, collect(tin.ref_id) AS in_refs\n"
        "    MATCH (mule)-[tout:Transfer]->(dst:Entity)\n"
        "    WITH mule, in_total, in_refs, sum(tout.amount_usd) AS out_total, collect(tout.ref_id) AS out_refs\n"
        "    WHERE in_total > 0 AND out_total >= in_total * " + _fmt(cfg["RAPID_MVMT_PASS_PCT"]) + "\n"
        "    RETURN mule.id AS entity_id, in_refs + out_refs AS tx_hashes\n"
        "$$) as (entity_id agtype, tx_hashes agtype);\n"
    )


def _q_rapid_layering(cfg):
    # Rapid-succession layering chain: 3+ hops where each consecutive hop
    # follows the previous within RAPID_LAYER_GAP_SECONDS. Uses the same
    # ``timestamp - timestamp < N`` idiom the HIGH_VELOCITY_LAYERING rule
    # already relies on, so both stand or fall together against AGE.
    return (
        "SELECT * FROM cypher('aml_network', $$\n"
        "    MATCH p = (a:Entity)-[t:Transfer*"
        + _fmt(cfg["RAPID_LAYER_MIN_HOPS"]) + ".." + _fmt(cfg["RAPID_LAYER_MAX_HOPS"]) + "]->(b:Entity)\n"
        "    WHERE ALL(idx IN range(0, size(relationships(p))-2)\n"
        "          WHERE (relationships(p)[idx+1]).timestamp - (relationships(p)[idx]).timestamp < "
        + _fmt(cfg["RAPID_LAYER_GAP_SECONDS"]) + ")\n"
        "    RETURN a.id AS entity_id, relationships(p)\n"
        "$$) as (entity_id agtype, tx_hashes agtype);\n"
    )


def _q_cross_rail_layering(cfg):
    # Cross-rail layering: stablecoin inflow to a wallet followed by fiat
    # outflow from a fiat account controlled by the SAME beneficial owner,
    # within the window. REQUIRES the party/UBO graph dimension
    # (init-scripts/06-party-ubo-model.sql + etl/party_loader.py); rule_engine
    # skips this scenario with guidance until the 'Party' label is present.
    # Plain string concatenation (no f-strings) so Cypher's {system:'FIAT'}
    # property map and the [:UBO_OF*0..3] braces stay literal.
    stablecoins = ", ".join("'" + s + "'" for s in cfg["CROSS_RAIL_STABLECOINS"])
    return (
        "SELECT * FROM cypher('aml_network', $$\n"
        "    MATCH (wallet:Entity)<-[tin:Transfer]-(src:Entity)\n"
        "    WHERE tin.asset IN [" + stablecoins + "]\n"
        "    MATCH (wallet)-[:OWNED_BY]->(:Party)-[:UBO_OF*0..3]->(ubo:Party)\n"
        "    MATCH (fiat:Entity {system: 'FIAT'})-[tout:Transfer]->(dst:Entity)\n"
        "    MATCH (fiat)-[:OWNED_BY]->(:Party)-[:UBO_OF*0..3]->(ubo)\n"
        "    WHERE tout.timestamp - tin.timestamp >= 0\n"
        "      AND tout.timestamp - tin.timestamp < " + _fmt(cfg["CROSS_RAIL_WINDOW_SECONDS"]) + "\n"
        "      AND wallet.id <> fiat.id\n"
        "    RETURN ubo.id AS entity_id, collect(DISTINCT tin.ref_id) + collect(DISTINCT tout.ref_id) AS tx_hashes\n"
        "$$) as (entity_id agtype, tx_hashes agtype);\n"
    )


# ---------------------------------------------------------------------------
# The registry. Order = execution order. ``name`` is the historical alert_type
# (kept stable for back-compat); ``code`` is the stable v5 scenario identifier.
# ---------------------------------------------------------------------------

SCENARIOS = [
    {
        "code": "SCN_CIRCULAR_01",
        "name": "CIRCULAR_TRANSACTION",
        "category": "CIRCULAR_FLOW",
        "rail": "BOTH",
        "mode": "BATCH",
        "severity": "CRITICAL",
        "description": "Funds cycling back to origin within 2-5 hops (round-tripping).",
        "build_query": _q_circular,
    },
    {
        "code": "SCN_STRUCT_01",
        "name": "SMURFING_STRUCTURING",
        "category": "STRUCTURING",
        "rail": "BOTH",
        "mode": "BATCH",
        "severity": "HIGH",
        "description": "Many sub-threshold transfers between the same pair aggregating past the threshold.",
        "build_query": _q_smurfing,
    },
    {
        "code": "SCN_PEEL_01",
        "name": "PEELING_CHAIN",
        "category": "LAYERING",
        "rail": "BOTH",
        "mode": "BATCH",
        "severity": "HIGH",
        "description": "Chain of transfers peeling 5-20% off at each hop to obscure origin.",
        "build_query": _q_peeling,
    },
    {
        "code": "SCN_LAYER_FAN_01",
        "name": "HIGH_VELOCITY_LAYERING",
        "category": "LAYERING",
        "rail": "BOTH",
        "mode": "REALTIME",
        "severity": "CRITICAL",
        "description": "Rapid fan-out through mules then fan-in consolidation (coordinated network).",
        "build_query": _q_high_velocity_layering,
    },
    {
        "code": "SCN_RAPID_MVMT_01",
        "name": "RAPID_MOVEMENT",
        "category": "RAPID_MOVEMENT",
        "rail": "BOTH",
        "mode": "REALTIME",
        "severity": "HIGH",
        "description": "Mule forwarding >= 90% of received funds (rapid pass-through). Restores the "
                       "typology mandated by AML_spec.md that had been dropped from typologies.py.",
        "build_query": _q_rapid_movement,
    },
    {
        "code": "SCN_LAYER_RAPID_01",
        "name": "RAPID_LAYERING",
        "category": "LAYERING",
        "rail": "BOTH",
        "mode": "REALTIME",
        "severity": "CRITICAL",
        "description": "3+ hop chain of rapid-succession transfers (long chain of intermediaries).",
        "build_query": _q_rapid_layering,
    },
    {
        "code": "SCN_CROSS_RAIL_LAYER_01",
        "name": "CROSS_RAIL_LAYERING",
        "category": "LAYERING",
        "rail": "BOTH",
        "mode": "BATCH",
        "severity": "CRITICAL",
        "description": "Stablecoin inflow to a wallet followed by fiat outflow from a fiat account "
                       "under the same beneficial owner within 48h. The v5 platform's headline "
                       "differentiator. REQUIRES the party/UBO dimension (init 06 + party_loader).",
        "build_query": _q_cross_rail_layering,
        # rule_engine.py skips scenarios whose required graph labels are absent,
        # logging guidance instead of erroring, so this degrades gracefully until
        # the party dimension is projected.
        "requires_labels": ("Party",),
    },
]


def render_query(scenario, params):
    """Inject ``params`` into a scenario's Cypher builder and return the SQL string."""
    return scenario["build_query"](params)
