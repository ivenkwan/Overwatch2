"""Alert sink adapter (plan U1.5).

Writes detection alerts to the profile's schema-qualified alert table,
adapting to the column-superset difference between the two sinks:
  * ``ag_catalog.alerts`` (aml_network) — also has ``alert_type``, ``ml_typology``,
    ``window_start``/``window_end`` (from init-scripts/05-alert-schema-v5.sql).
  * ``core.alerts`` (tap_and_go) — the v5-shaped subset (etl/sql/alerts_schema.sql).

The engine authors a superset row; the sink introspects the target table's
actual columns (information_schema) and inserts only those present, so schema
drift never breaks the insert. For unit tests, columns can be injected to
avoid a DB round-trip.
"""

from __future__ import annotations

import json
from typing import Optional

from .contract import GraphProfile


def resolve_columns(cur, alert_table: str) -> set[str]:
    """Introspect the target table's column names from information_schema."""
    schema, _, name = alert_table.rpartition(".")
    schema = schema or "public"
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s",
        (schema, name),
    )
    return {row[0] for row in cur.fetchall()}


class AlertSink:
    def __init__(self, profile: GraphProfile, cur, columns: Optional[set[str]] = None):
        self.profile = profile
        self.cur = cur
        self._columns = columns  # None => introspect lazily on first sink()

    @property
    def columns(self) -> set[str]:
        if self._columns is None:
            self._columns = resolve_columns(self.cur, self.profile.alert_table)
        return self._columns

    def sink(self, *, scenario, entity_id, tx_hashes, rule_version) -> None:
        # Superset of columns the engine may populate. window_* are omitted
        # (the engine does not compute them; they default NULL in the table).
        row = {
            "alert_type": scenario.name,                 # aml_network only
            "scenario_code": scenario.code,
            "scenario_category": scenario.category.value,
            "rail": scenario.rail.value,
            "ml_typology": None,                         # aml_network only
            "severity": scenario.severity.value,
            "trigger_entity": str(entity_id),
            "related_transactions": json.dumps(tx_hashes),
            "rule_version": rule_version,
            "status": "OPEN",
        }
        present = {k: v for k, v in row.items() if k in self.columns}
        cols = ", ".join(present)
        placeholders = ", ".join(["%s"] * len(present))
        self.cur.execute(
            f"INSERT INTO {self.profile.alert_table} ({cols}) VALUES ({placeholders})",
            tuple(present.values()),
        )
