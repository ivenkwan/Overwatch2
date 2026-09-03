"""Per-profile Cypher renderer (plan U2.2 / ADR 0001 §7.3-7.4).

Substitutes ``<<token>>`` placeholders in an abstract query (produced by
``registry``) with a :class:`GraphProfile`'s concrete labels, property names,
graph name, and (for party-capable profiles) the party/UBO dimension labels.

Token catalogue:
    <<graph>>      -> profile.graph_name
    <<account>>    -> profile.account_label (may be a label-union 'A|B|C')
    <<transfer>>   -> profile.transfer_label (may be a union 'PAID|TRANSFERRED')
    <<value>>      -> profile.prop_value
    <<ts>>         -> profile.prop_ts
    <<ref>>        -> profile.prop_ref
    <<party>>      -> party label            (requires party capability)
    <<owns>>       -> Entity->Party edge     (requires party capability)
    <<ubo>>        -> Party->Party edge      (requires party capability)
    <<fiat_node>>  -> rail-specific fiat account node pattern
                     (requires a rail property, i.e. aml_network-style profiles)

This module depends only on ``contract`` (no registry, no DB) — it is a pure
string transform, fully unit-testable.
"""

from __future__ import annotations

from .contract import GraphProfile

_UNRESOLVED = "<<"  # sentinel used to detect leftover tokens


def _expand_fiat_node(profile: GraphProfile) -> str:
    if profile.prop_rail is None:
        raise ValueError(
            f"<<fiat_node>> requires a rail property (system), but profile "
            f"{profile.name!r} uses a constant rail ({profile.rail_constant!r}); "
            "cross-rail is not meaningful on single-rail graphs."
        )
    # f-string doubles braces to emit a Cypher property map literally.
    return f"(fiat:{profile.account_label} {{{profile.prop_rail}: 'FIAT'}})"


def render(profile: GraphProfile, abstract_query: str) -> str:
    """Substitute every ``<<token>>`` in ``abstract_query`` for ``profile``."""
    pd = profile.capabilities.party_dimension
    out = abstract_query
    out = out.replace("<<graph>>", profile.graph_name)
    out = out.replace("<<account>>", profile.account_label)
    out = out.replace("<<transfer>>", profile.transfer_label)
    out = out.replace("<<value>>", profile.prop_value)
    out = out.replace("<<ts>>", profile.prop_ts)
    out = out.replace("<<ref>>", profile.prop_ref)

    if "<<party>>" in out or "<<owns>>" in out or "<<ubo>>" in out:
        if pd is None:
            raise ValueError(
                f"query uses the party/UBO dimension but profile "
                f"{profile.name!r} has none (scenario should be capability-gated)"
            )
        out = out.replace("<<party>>", pd.party_label)
        out = out.replace("<<owns>>", pd.owns_label)
        out = out.replace("<<ubo>>", pd.ubo_label)

    if "<<fiat_node>>" in out:
        out = out.replace("<<fiat_node>>", _expand_fiat_node(profile))

    if _UNRESOLVED in out:
        # Surface any token the renderer doesn't know about — a typo'd token
        # would otherwise silently ship a malformed query.
        leftovers = sorted({seg.split(">>", 1)[0] for seg in out.split("<<")[1:] if ">>" in seg})
        raise ValueError(f"unresolved <<tokens>> in rendered query for {profile.name!r}: {leftovers}")
    return out
