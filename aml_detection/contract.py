"""Canonical types for the unified detection engine (plan U1.2 / ADR 0001).

This module defines the *abstract* contract every scenario is authored
against and every :class:`GraphProfile` maps onto a concrete graph. It has no
runtime dependencies (no dagster / psycopg2) so it is safe to import and unit
test anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# Enumerations (union of the values used by aml_network scenarios.py and
# tap_and_go detection.py, aligned to the v5 converged-model vocabulary).
# ---------------------------------------------------------------------------

class Category(str, Enum):
    CIRCULAR_FLOW = "CIRCULAR_FLOW"
    STRUCTURING = "STRUCTURING"
    LAYERING = "LAYERING"
    RAPID_MOVEMENT = "RAPID_MOVEMENT"
    VELOCITY = "VELOCITY"
    PLACEMENT = "PLACEMENT"
    TRAVEL_RULE_BREACH = "TRAVEL_RULE_BREACH"
    BLOCKCHAIN_RISK = "BLOCKCHAIN_RISK"
    UNHOSTED_WALLET = "UNHOSTED_WALLET"
    PEP_MONITORING = "PEP_MONITORING"


class Rail(str, Enum):
    FIAT = "FIAT"
    STABLECOIN = "STABLECOIN"
    BOTH = "BOTH"


class Mode(str, Enum):
    REALTIME = "REALTIME"
    BATCH = "BATCH"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Currency(str, Enum):
    HKD = "HKD"
    USD = "USD"

    @property
    def is_base(self) -> bool:
        """HKD is the regulatory base currency (ADR 0001)."""
        return self is Currency.HKD


class Capability(str, Enum):
    """Optional graph dimensions a profile may or may not expose."""
    PARTY_DIMENSION = "PARTY_DIMENSION"


# ---------------------------------------------------------------------------
# Resolved-threshold map: flat dict of tunable parameters (currency-resolved
# by aml_detection.currency.CurrencyResolver). Type alias only.
# ---------------------------------------------------------------------------

Params = dict[str, Any]


# ---------------------------------------------------------------------------
# Capabilities — what a profile's graph actually has. Scenario requirements
# (Capability) are checked against these by the engine (capability gating,
# plan U2.3).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PartyDimension:
    """Concrete labels for the party/UBO graph dimension, when present."""
    party_label: str   # vertex label for Party/UBO nodes, e.g. 'Party'
    owns_label: str    # Entity -> Party edge label, e.g. 'OWNED_BY'
    ubo_label: str     # Party -> Party edge label, e.g. 'UBO_OF'


@dataclass(frozen=True)
class Capabilities:
    party_dimension: Optional[PartyDimension] = None

    def supports(self, capability: "Capability") -> bool:
        if capability is Capability.PARTY_DIMENSION:
            return self.party_dimension is not None
        return False


# ---------------------------------------------------------------------------
# Scenario — one abstract detection rule. ``build_query`` renders the abstract
# Cypher body from resolved Params; the renderer (plan U2.2) maps abstract
# labels/props onto the target profile. ``build_query`` is populated by
# registry.py (U2.1) and is optional here so the contract can be tested in
# isolation.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Scenario:
    code: str                                              # stable SCN_* id
    name: str                                              # historical alert_type / display
    category: Category
    rail: Rail
    mode: Mode
    severity: Severity
    description: str
    requires_capabilities: tuple[Capability, ...] = ()
    build_query: Optional[Callable[[Params], str]] = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.startswith("SCN_"):
            raise ValueError(f"Scenario.code must start with 'SCN_': {self.code!r}")
        if not self.name:
            raise ValueError("Scenario.name is required")
        if not isinstance(self.category, Category):
            raise ValueError(f"Scenario.category must be a Category enum, got {self.category!r}")
        if not isinstance(self.rail, Rail):
            raise ValueError(f"Scenario.rail must be a Rail enum, got {self.rail!r}")
        if not isinstance(self.mode, Mode):
            raise ValueError(f"Scenario.mode must be a Mode enum, got {self.mode!r}")
        if not isinstance(self.severity, Severity):
            raise ValueError(f"Scenario.severity must be a Severity enum, got {self.severity!r}")

    def needs(self, capability: "Capability") -> bool:
        return capability in self.requires_capabilities


# ---------------------------------------------------------------------------
# GraphProfile — maps the abstract contract onto one physical graph. The DB
# connection is NOT part of the profile; it is passed into engine.detect().
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GraphProfile:
    name: str                                # 'aml_network' | 'tap_and_go'
    graph_name: str                          # the Apache AGE graph namespace
    account_label: str                       # abstract Account -> label(s); may be a union 'A|B|C'
    transfer_label: str                      # abstract Transfer -> label(s); may be a union 'A|B'
    prop_value: str                          # amount property name, e.g. 'amount_usd' | 'amount'
    base_ccy: Currency                        # currency of prop_value
    prop_ts: str                             # epoch-seconds property name (canonical: epoch)
    ts_is_epoch: bool = True
    prop_ref: str = "ref_id"                 # transaction-reference property name
    prop_rail: Optional[str] = "system"      # node rail property name, or None
    rail_constant: Optional[str] = None      # constant rail when prop_rail is None (e.g. 'FIAT')
    capabilities: Capabilities = field(default_factory=Capabilities)
    alert_table: str = "alerts"              # schema-qualified alert sink table

    def __post_init__(self) -> None:
        if not isinstance(self.base_ccy, Currency):
            raise ValueError(f"GraphProfile.base_ccy must be a Currency enum, got {self.base_ccy!r}")
        # Exactly one rail source: either a node property OR a constant.
        if (self.prop_rail is None) == (self.rail_constant is None):
            raise ValueError(
                "GraphProfile: set exactly one of prop_rail / rail_constant "
                f"(profile={self.name!r})"
            )
        if not self.ts_is_epoch:
            # The unified engine does epoch arithmetic on ts; non-epoch is a
            # future concern (the aml_network ISO->epoch migration, plan U4,
            # makes both graphs epoch). Fail loud rather than emit wrong Cypher.
            raise ValueError(
                f"GraphProfile {self.name!r}: ts must be epoch (ts_is_epoch=True); "
                "non-epoch timestamps are not supported by the unified renderer."
            )

    @property
    def has_party(self) -> bool:
        return self.capabilities.supports(Capability.PARTY_DIMENSION)
