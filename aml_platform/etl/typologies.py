"""
DEPRECATED backward-compat shim.

The scenario registry now lives in ``scenarios.py`` (v5-style entries with
stable ``code`` identifiers and tunable params). ``rule_engine.py`` consumes
the registry directly. This module is kept only so any external code still
doing ``from typologies import TYPOLOGIES`` (or referencing a ``CYPHER_*``
constant) keeps working; it derives everything from the registry so there is
a single source of truth.

New detection scenarios MUST be added to ``scenarios.SCENARIOS`` — do not
edit this file.
"""

import warnings

from scenarios import SCENARIOS, DEFAULT_PARAMS, render_query

warnings.warn(
    "typologies.py is deprecated; use scenarios.SCENARIOS instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Legacy CYPHER_* constants (rendered with default params), preserved names.
CYPHER_CIRCULAR_FLOW = render_query(
    next(s for s in SCENARIOS if s["name"] == "CIRCULAR_TRANSACTION"), DEFAULT_PARAMS
)
CYPHER_SMURFING = render_query(
    next(s for s in SCENARIOS if s["name"] == "SMURFING_STRUCTURING"), DEFAULT_PARAMS
)
CYPHER_PEELING_CHAIN = render_query(
    next(s for s in SCENARIOS if s["name"] == "PEELING_CHAIN"), DEFAULT_PARAMS
)
CYPHER_HIGH_VELOCITY_LAYERING = render_query(
    next(s for s in SCENARIOS if s["name"] == "HIGH_VELOCITY_LAYERING"), DEFAULT_PARAMS
)

# Legacy list shape: [{"name", "query", "severity"}] for every registered scenario.
TYPOLOGIES = [
    {
        "name": s["name"],
        "query": render_query(s, DEFAULT_PARAMS),
        "severity": s["severity"],
    }
    for s in SCENARIOS
]
