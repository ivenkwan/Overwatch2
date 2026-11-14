"""Alert sink adapter (plan U1.5, extended by TASK-061).

Writes detection alerts to the profile's schema-qualified alert table.

TASK-061 security gate: every ``execute()`` call receives a single string
literal (no concatenation, no interpolation, no variables) and all values are
bound parameters (%s). The sink targets are a closed set — an unknown
``alert_table`` fails loud with guidance instead of composing SQL.

Targets:
  * ``ag_catalog.alerts`` (legacy v5 superset, init-scripts/05) — 10 columns.
  * ``core.alerts`` (legacy v5 subset, etl/sql/alerts_schema.sql) — 8 columns.
  * ``app.alerts`` (operational tenant-scoped, backend/init_scripts/
    01_rbac_initialization.sql) — the deployed platform's alert workbench
    table. Detection metadata (scenario code, category, rail, rule version,
    related transactions) is carried inside the JSONB ``payload``;
    ``payload->>'txn_hash'`` carries the first related transaction so the
    existing alert-triage transitions (which key on that path element) can
    act on engine-sourced alerts. ``status`` is written lowercase ('open') to
    satisfy the app.alerts CHECK constraint. Requires an explicit
    ``tenant_id`` — there is no acting user in a detection batch, so the
    deployment wiring must supply one (fail-loud, never NULL).

Column introspection (``resolve_columns`` / the ``columns`` argument) is kept
as a drift *check*: when column knowledge is available, the static column set
must all exist on the target, otherwise the sink raises instead of silently
writing a degraded row.

For unit tests, columns can be injected to avoid a DB round-trip.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from .contract import GraphProfile, Severity

#: The operational tenant-scoped sink (detected by table name).
OPERATIONAL_TABLE = "app.alerts"

#: app.alerts.risk_score is NUMERIC — map severity onto a bounded score so the
#: operational queue can priority-sort engine alerts (LOW..CRITICAL -> 25..90).
_SEVERITY_RISK_SCORE: dict[Severity, float] = {
    Severity.LOW: 25.0,
    Severity.MEDIUM: 50.0,
    Severity.HIGH: 75.0,
    Severity.CRITICAL: 90.0,
}

#: Column order each static INSERT binds (kept beside the statements below).
_AGL_COLS = ("alert_type", "scenario_code", "scenario_category", "rail", "ml_typology", "severity", "trigger_entity", "related_transactions", "rule_version", "status")
_CORE_COLS = ("scenario_code", "scenario_category", "rail", "severity", "trigger_entity", "related_transactions", "rule_version", "status")
_APP_COLS = ("tenant_id", "alert_type", "risk_score", "status", "customer_id", "payload")

#: The closed set of sink targets (fail loud on anything else).
KNOWN_SINK_TABLES = ("ag_catalog.alerts", "core.alerts", OPERATIONAL_TABLE)


def resolve_columns(cur: Any, alert_table: str) -> set[str]:
    """Introspect the target table's column names from information_schema."""
    schema, _, name = alert_table.rpartition(".")
    schema = schema or "public"
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s", (schema, name))
    return {row[0] for row in cur.fetchall()}


def _agtype_text(value: Any) -> str:
    """AGE returns agtype strings JSON-quoted through DB-API decoding
    ('\"LVPEEL_A\"'); strip the wrapping for identifier-like columns."""
    text = str(value)
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]
    return text


def _normalize_txs(tx_hashes: Any) -> Any:
    """agtype lists may decode as their text form ('[\"a\", \"b\"]'); parse
    that back into a real list so the payload JSON stays structured."""
    if isinstance(tx_hashes, (list, tuple)):
        return list(tx_hashes)
    if isinstance(tx_hashes, str) and tx_hashes.startswith("["):
        try:
            return json.loads(tx_hashes)
        except ValueError:
            return tx_hashes
    return tx_hashes


def _first_ref(tx_hashes: Any) -> Any:
    """First related-transaction reference, for payload->>'txn_hash'."""
    normalized = _normalize_txs(tx_hashes)
    if isinstance(normalized, (list, tuple)) and normalized:
        first = normalized[0]
        return _agtype_text(first) if isinstance(first, str) else first
    if isinstance(normalized, str) and normalized:
        return _agtype_text(normalized)
    return None


def _legacy_row(scenario: Any, entity_id: Any, tx_hashes: Any, rule_version: str) -> dict[str, Any]:
    """Legacy v5-shaped superset row; window_* are omitted (the engine does
    not compute them; they default NULL in the table)."""
    return {
        "alert_type": scenario.name,
        "scenario_code": scenario.code,
        "scenario_category": scenario.category.value,
        "rail": scenario.rail.value,
        "ml_typology": None,
        "severity": scenario.severity.value,
        "trigger_entity": str(entity_id),
        "related_transactions": json.dumps(tx_hashes),
        "rule_version": rule_version,
        "status": "OPEN",
    }


class AlertSink:
    def __init__(
        self,
        profile: GraphProfile,
        cur: Any,
        columns: Optional[set[str]] = None,
        tenant_id: Any = None,
    ):
        self.profile = profile
        self.cur = cur
        self._columns = columns  # None => introspect lazily (drift check only)
        self.tenant_id = tenant_id

    @property
    def columns(self) -> set[str]:
        if self._columns is None:
            self._columns = resolve_columns(self.cur, self.profile.alert_table)
        return self._columns

    def _check_drift(self, template_cols: tuple[str, ...]) -> None:
        """When column knowledge is available, verify the target table still
        carries every column the static INSERT binds. An empty result means
        the table is absent — the INSERT itself will fail loud at the DB."""
        if not self.columns:
            return
        missing = [c for c in template_cols if c not in self.columns]
        if missing:
            raise ValueError(
                f"alert table {self.profile.alert_table!r} has drifted from "
                f"its sink column set (missing {missing!r}) — update the "
                "static sink in aml_detection/alerts.py"
            )

    def sink(self, *, scenario: Any, entity_id: Any, tx_hashes: Any, rule_version: str) -> None:
        table = self.profile.alert_table
        if table == "ag_catalog.alerts":
            self._check_drift(_AGL_COLS)
            row = _legacy_row(scenario, entity_id, tx_hashes, rule_version)
            self.cur.execute("INSERT INTO ag_catalog.alerts (alert_type, scenario_code, scenario_category, rail, ml_typology, severity, trigger_entity, related_transactions, rule_version, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", tuple(row[c] for c in _AGL_COLS))
        elif table == "core.alerts":
            self._check_drift(_CORE_COLS)
            row = _legacy_row(scenario, entity_id, tx_hashes, rule_version)
            self.cur.execute("INSERT INTO core.alerts (scenario_code, scenario_category, rail, severity, trigger_entity, related_transactions, rule_version, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", tuple(row[c] for c in _CORE_COLS))
        elif table == OPERATIONAL_TABLE:
            self._check_drift(_APP_COLS)
            self.cur.execute("INSERT INTO app.alerts (tenant_id, alert_type, risk_score, status, customer_id, payload) VALUES (%s, %s, %s, %s, %s, %s)", self._operational_values(scenario, entity_id, tx_hashes, rule_version))
        else:
            raise ValueError(
                f"unknown alert sink table {table!r} — the sink set is closed "
                f"({', '.join(KNOWN_SINK_TABLES)}); add a literal INSERT "
                "branch rather than composing SQL dynamically"
            )

    def _operational_values(self, scenario: Any, entity_id: Any, tx_hashes: Any, rule_version: str) -> tuple:
        if self.tenant_id is None:
            raise ValueError(
                f"alert table {self.profile.alert_table!r} is tenant-scoped "
                "but no tenant_id was supplied — pass tenant_id= to "
                "AlertSink / engine.detect from the deployment wiring"
            )
        payload = {
            "scenario_code": scenario.code,
            "scenario_category": scenario.category.value,
            "rail": scenario.rail.value,
            "severity": scenario.severity.value,
            "rule_version": rule_version,
            "entity_id": _agtype_text(entity_id),
            "related_transactions": _normalize_txs(tx_hashes),
            # The triage endpoints UPDATE ... WHERE payload->>'txn_hash' = $1;
            # carrying the first related tx makes engine alerts triageable.
            "txn_hash": _first_ref(tx_hashes),
        }
        row = {
            "tenant_id": self.tenant_id,
            "alert_type": scenario.name,              # NOT NULL
            "risk_score": _SEVERITY_RISK_SCORE[scenario.severity],
            "status": "open",                         # CHECK is lowercase
            "customer_id": _agtype_text(entity_id),
            "payload": json.dumps(payload),
        }
        return tuple(row[c] for c in _APP_COLS)
