"""Unified detection engine (plan U3 / ADR 0001).

``detect(profile, conn)`` runs the canonical scenario registry against ONE
graph described by ``profile``, using the passed-in DB-API ``conn``. It:
  * resolves per-currency thresholds (CurrencyResolver),
  * gates scenarios on the profile's capabilities (skips with a guidance log),
  * renders concrete Cypher per profile,
  * sinks hits via the AlertSink (adapting to each table's columns),
  * isolates per-rule failures (rollback + log + continue) and commits each
    rule's alerts independently so a later failure cannot drop earlier hits.

Import boundary: this module imports ONLY other aml_detection modules (no
dagster / psycopg2). The connection is supplied by the caller — aml_platform's
rule_engine or the Dagster op — so the engine is unit-testable with a fake conn.
"""

from __future__ import annotations

import logging

from .alerts import AlertSink
from .contract import GraphProfile
from .currency import DEFAULT as DEFAULT_RESOLVER, CurrencyResolver
from .gating import missing_capabilities
from .registry import SCENARIOS, resolve_params
from .render import render

log = logging.getLogger("aml-detection")

#: Bumped whenever the registry shape, a query, or the engine changes.
RULE_VERSION = "2026.07-aml-detection-engine"


def detect(
    profile: GraphProfile,
    conn,
    *,
    resolver: CurrencyResolver = DEFAULT_RESOLVER,
    sink_class=AlertSink,
    logger=log,
) -> dict:
    """Run every applicable scenario against ``profile``'s graph.

    Returns a summary dict: {profile, evaluated, skipped, fired, errors}.
    """
    cur = conn.cursor()
    summary = {"profile": profile.name, "evaluated": 0, "skipped": 0, "fired": 0, "errors": []}
    try:
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, public;")
        sink = sink_class(profile, cur)
        params = resolve_params(profile, resolver)

        for scenario in SCENARIOS:
            missing = missing_capabilities(scenario, profile)
            if missing:
                logger.info(
                    "Skip %s [%s] on %s — missing capabilities %s",
                    scenario.name, scenario.code, profile.name, [m.value for m in missing],
                )
                summary["skipped"] += 1
                continue

            summary["evaluated"] += 1
            try:
                query = render(profile, scenario.build_query(params))
                cur.execute(query)
                hits = cur.fetchall()
                fired = 0
                for entity_id, tx_hashes in hits:
                    sink.sink(
                        scenario=scenario, entity_id=entity_id,
                        tx_hashes=tx_hashes, rule_version=RULE_VERSION,
                    )
                    fired += 1
                conn.commit()  # persist this rule's alerts independently
                if fired:
                    logger.warning("%s fired %d alert(s) on %s", scenario.name, fired, profile.name)
                summary["fired"] += fired
            except Exception as e:  # one bad rule never halts the batch
                conn.rollback()
                logger.error("Rule %s failed on %s: %s", scenario.name, profile.name, e)
                summary["errors"].append(scenario.code)
                continue

        return summary
    finally:
        cur.close()
