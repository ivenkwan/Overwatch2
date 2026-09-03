"""GraphProfile for the aml_platform ``aml_network`` graph (ADR 0001 §7.4).

Graph contract (aml_platform/etl/graph_loader.py + init-scripts):
  nodes   Entity {id, system}, SuperNode, Party
  edges   Transfer {amount_usd, timestamp, ts, ref_id[, asset]}
  rails   node property ``system`` ('FIAT' or chain name e.g. 'ETHEREUM')
  party   Party + OWNED_BY (Entity->Party) + UBO_OF (Party->Party)

USD-denominated. ``ts`` is epoch seconds (added in plan U4 / migration
a23ccb9). The DB connection is NOT part of the profile — passed to
engine.detect().
"""

from ..contract import Capabilities, Currency, GraphProfile, PartyDimension

AML_NETWORK = GraphProfile(
    name="aml_network",
    graph_name="aml_network",
    account_label="Entity|SuperNode",
    transfer_label="Transfer",
    prop_value="amount_usd",
    base_ccy=Currency.USD,
    prop_ts="ts",
    ts_is_epoch=True,
    prop_ref="ref_id",
    prop_rail="system",
    rail_constant=None,
    capabilities=Capabilities(
        party_dimension=PartyDimension(
            party_label="Party",
            owns_label="OWNED_BY",
            ubo_label="UBO_OF",
        ),
    ),
    alert_table="ag_catalog.alerts",
)
