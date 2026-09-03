"""GraphProfile for the Dagster ``tap_and_go_network`` graph (ADR 0001 §7.4).

Graph contract (etl/assets/graph_projection.py + etl/daily_pipeline.py):
  nodes   Customer, Counterparty, Merchant (all {id})
  edges   PAID, TRANSFERRED {txn_hash, amount, ts}
  rails   none (single fiat rail) — exposed as the constant 'FIAT'
  party   none (Cross-Rail Layering not applicable to this graph)

HKD-denominated. ``ts`` is epoch seconds (added in plan U6.5-precedent /
commit 6edb981). The DB connection is NOT part of the profile — passed to
engine.detect().
"""

from ..contract import Capabilities, Currency, GraphProfile

TAP_AND_GO = GraphProfile(
    name="tap_and_go",
    graph_name="tap_and_go_network",
    account_label="Customer|Counterparty|Merchant",
    transfer_label="PAID|TRANSFERRED",
    prop_value="amount",
    base_ccy=Currency.HKD,
    prop_ts="ts",
    ts_is_epoch=True,
    prop_ref="txn_hash",
    prop_rail=None,
    rail_constant="FIAT",
    capabilities=Capabilities(),
    alert_table="core.alerts",
)
