"""Capability gating (plan U2.3).

Decides whether a scenario applies to a profile by comparing the scenario's
declared ``requires_capabilities`` against the profile's ``Capabilities``.
Generalises the aml_network-only label gate (§6.1) to any optional graph
dimension (party/UBO now; baselines, wallet-analytics, etc. later).
"""

from __future__ import annotations

from .contract import GraphProfile, Scenario


def missing_capabilities(scenario: Scenario, profile: GraphProfile) -> list:
    """Capabilities the scenario needs but the profile does not expose."""
    return [c for c in scenario.requires_capabilities
            if not profile.capabilities.supports(c)]


def is_applicable(scenario: Scenario, profile: GraphProfile) -> bool:
    """True iff the profile satisfies every capability the scenario requires."""
    return not missing_capabilities(scenario, profile)
