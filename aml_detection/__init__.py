"""
aml_detection — unified rail/currency-aware detection core.

One scenario registry + one execution engine that serves BOTH physical graphs
(`aml_network` and `tap_and_go_network`) via per-graph profiles. See
``docs/adr/0001-unified-detection-engine.md`` and §7 of
``Implementation_Plan/20260710_typology_gap_plan.md``.

IMPORT BOUNDARY (enforced by convention — review it):
    This package MUST NOT import ``dagster`` or ``psycopg2`` at module import
    time. Database connections and execution hosts are passed in by the caller,
    so the package is unit-testable and importable from BOTH the aml_platform
    venv AND the Dagster container.

Planned layout (filled by later plan phases):
    contract.py   — enums + dataclasses (this phase: U1.2)        [#18, done]
    currency.py   — CurrencyResolver                              [U1.3]
    profiles/     — aml_network + tap_and_go GraphProfiles        [U1.4]
    alerts.py     — AlertSink (schema-qualified insert adapter)   [U1.5]
    registry.py   — canonical abstract scenario registry          [U2.1]
    render.py     — per-profile Cypher renderer                   [U2.2]
    engine.py     — detect(profile, conn) execution               [U3]
"""

from .contract import (
    Capabilities,
    Capability,
    Category,
    Currency,
    GraphProfile,
    Mode,
    PartyDimension,
    Rail,
    Scenario,
    Severity,
)

__version__ = "0.1.0"

__all__ = [
    "Capabilities",
    "Capability",
    "Category",
    "Currency",
    "GraphProfile",
    "Mode",
    "PartyDimension",
    "Rail",
    "Scenario",
    "Severity",
    "__version__",
]
