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
    <<auth_prop>>  -> current-authorization boolean property (requires the
                     authorization capability)
    <<ever_auth>>  -> ever-authorized boolean property (never cleared after
                     first approval; drift detection)
    <<fiat_node>>  -> rail-specific fiat account node pattern
                     (requires a rail property, i.e. aml_network-style profiles)

LABEL-UNION EXPANSION (live-verified on AGE, 2026-09-03): Apache AGE rejects
multi-label patterns such as ``(a:Entity|SuperNode)`` and
``[t:PAID|TRANSFERRED*2..5]``. render_statements() therefore expands the
abstract query into one Cypher statement PER combination of account/transfer
labels (e.g. tap_and_go 3 account × 2 transfer labels -> 6 statements); the
engine executes each and concatenates the hits. When a profile has no union
labels the result is a single statement, identical to the pre-expansion
behaviour.

This module depends only on ``contract`` (no registry, no DB) — it is a pure
string transform, fully unit-testable.
"""

from __future__ import annotations

from itertools import product

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


def _substitute(profile: GraphProfile, abstract_query: str) -> str:
    """Single-token substitution pass. Account/transfer labels are taken
    verbatim (callers pre-expand unions into one label per statement)."""
    pd = profile.capabilities.party_dimension
    ad = profile.capabilities.authorization_dimension
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

    if "<<auth_prop>>" in out or "<<ever_auth>>" in out:
        if ad is None:
            raise ValueError(
                f"query uses the authorization dimension but profile "
                f"{profile.name!r} has none (scenario should be capability-gated)"
            )
        out = out.replace("<<auth_prop>>", ad.auth_prop)
        out = out.replace("<<ever_auth>>", ad.ever_auth_prop)

    if "<<fiat_node>>" in out:
        out = out.replace("<<fiat_node>>", _expand_fiat_node(profile))

    if _UNRESOLVED in out:
        # Surface any token the renderer doesn't know about — a typo'd token
        # would otherwise silently ship a malformed query.
        leftovers = sorted({seg.split(">>", 1)[0] for seg in out.split("<<")[1:] if ">>" in seg})
        raise ValueError(f"unresolved <<tokens>> in rendered query for {profile.name!r}: {leftovers}")
    return out


def _variant(profile: GraphProfile, abstract_query: str, account: str, transfer: str) -> str:
    """Render one statement with a single account/transfer label pair."""
    from dataclasses import replace

    single = replace(profile, account_label=account, transfer_label=transfer)
    return _substitute(single, abstract_query)


def render_statements(profile: GraphProfile, abstract_query: str) -> list[str]:
    """Render the abstract query into one Cypher statement per label
    combination (label-union expansion for AGE)."""
    account_labels = profile.account_label.split("|")
    transfer_labels = profile.transfer_label.split("|")
    statements = [
        _variant(profile, abstract_query, account, transfer)
        for account, transfer in product(account_labels, transfer_labels)
    ]
    return statements


def render(profile: GraphProfile, abstract_query: str) -> str:
    """Back-compat: the FIRST label combination (pre-expansion semantics).

    Engine callers should use render_statements() so every label
    combination is executed.
    """
    return render_statements(profile, abstract_query)[0]
